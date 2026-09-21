"""Boss 直聘批量打招呼脚本。

运行前会检查 ADB 设备连接。默认对当前职位详情页真实点击“打招呼”，
处理指定数量的职位；使用 --dry-run 时只读取页面信息，不执行点击。
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET


PACKAGE = "com.hpbr.bosszhipin"
RID_JOB_NAME = f"{PACKAGE}:id/tv_job_name"
RID_DESCRIPTION = f"{PACKAGE}:id/tv_description"
RID_SALARY = f"{PACKAGE}:id/tv_job_salary"
RID_LOCATION = f"{PACKAGE}:id/tv_required_location"
RID_BOSS_NAME = f"{PACKAGE}:id/tv_boss_name"
RID_CHAT_BTN = f"{PACKAGE}:id/btn_chat"

DEFAULT_COUNT = 10
SLEEP_TAP = 0.8
SLEEP_BACK = 0.3
SLEEP_SWIPE = 1.5
SLEEP_ERROR = 1.0
SWIPE_DURATION = 100

ADB = None
ADB_SERIAL = None


class AdbError(RuntimeError):
    """ADB 环境、连接或命令执行错误。"""


def resolve_adb():
    """优先使用显式配置或 PATH 中的 adb，并兼容常见 Android SDK 路径。"""
    candidates = []

    configured = os.environ.get("ADB")
    if configured:
        candidates.append(configured)

    on_path = shutil.which("adb")
    if on_path:
        candidates.append(on_path)

    adb_name = "adb.exe" if os.name == "nt" else "adb"
    for variable in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        sdk_root = os.environ.get(variable)
        if sdk_root:
            candidates.append(
                os.path.join(sdk_root, "platform-tools", adb_name)
            )

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidates.append(
            os.path.join(
                local_app_data,
                "Android",
                "Sdk",
                "platform-tools",
                adb_name,
            )
        )

    for candidate in candidates:
        if not candidate:
            continue
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
        if os.path.isfile(candidate):
            return os.path.abspath(candidate)

    return "adb"


def adb(*args, timeout=15, check=True):
    command = [ADB]
    if ADB_SERIAL:
        command.extend(["-s", ADB_SERIAL])
    command.extend(args)

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            timeout=timeout,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
    except FileNotFoundError as exc:
        raise AdbError(
            "未找到 adb。请安装 Android Platform Tools，并将 adb 加入 PATH，"
            "或设置 ADB 环境变量。"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise AdbError(f"ADB 命令超时：{' '.join(args)}") from exc

    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise AdbError(
            f"ADB 命令失败（退出码 {result.returncode}）：{' '.join(args)}"
            + (f"\n{detail}" if detail else "")
        )

    return result.stdout


def list_devices():
    output = adb("devices", "-l")
    devices = []

    for line in output.splitlines():
        line = line.strip()
        if not line or line.startswith("List of devices"):
            continue
        if line.startswith("*"):
            continue

        parts = line.split()
        if len(parts) >= 2:
            devices.append((parts[0], parts[1], line))

    return devices


def ensure_adb_connection(serial=None):
    devices = list_devices()

    if serial:
        for device_serial, state, detail in devices:
            if device_serial == serial:
                if state != "device":
                    raise AdbError(
                        f"设备 {serial} 当前状态为 {state}，不能执行自动化。\n"
                        f"{detail}"
                    )
                return serial

        available = ", ".join(item[0] for item in devices) or "无"
        raise AdbError(
            f"未找到指定的 ADB 设备：{serial}\n当前设备：{available}"
        )

    ready = [item for item in devices if item[1] == "device"]

    if not devices:
        raise AdbError(
            "未检测到 ADB 设备。请连接手机、开启 USB 调试并允许调试授权。"
        )

    if not ready:
        details = "\n".join(item[2] for item in devices)
        raise AdbError(
            "检测到 ADB 设备，但没有可用设备。请检查手机上的调试授权。\n"
            f"{details}"
        )

    if len(ready) > 1:
        serials = ", ".join(item[0] for item in ready)
        raise AdbError(
            f"检测到多个可用设备：{serials}\n"
            "请使用 --serial 指定目标设备。"
        )

    return ready[0][0]


def dump_ui():
    last_error = None

    for _ in range(2):
        xml = adb("exec-out", "uiautomator", "dump", "/dev/tty")
        start = xml.find("<hierarchy")
        end_marker = "</hierarchy>"
        end = xml.find(end_marker, start) + len(end_marker)

        if start != -1 and end >= len(end_marker):
            try:
                return ET.fromstring(xml[start:end])
            except ET.ParseError as exc:
                last_error = exc
        else:
            last_error = RuntimeError(
                f"UI 数据不完整：{xml[-200:]}"
            )

        time.sleep(0.8)

    raise RuntimeError(f"无法获取当前 UI：{last_error}")


def find(root, resource_id):
    for node in root.iter("node"):
        if node.attrib.get("resource-id") == resource_id:
            return node
    return None


def get_text(root, resource_id):
    node = find(root, resource_id)
    return node.attrib.get("text", "暂无") if node is not None else "暂无"


def parse_bounds(node):
    values = re.findall(r"\d+", node.attrib["bounds"])
    if len(values) != 4:
        raise RuntimeError(f"无法解析控件边界：{node.attrib.get('bounds')}")
    return tuple(map(int, values))


def tap(root, resource_id):
    node = find(root, resource_id)
    if node is None:
        return False

    x1, y1, x2, y2 = parse_bounds(node)
    x = (x1 + x2) // 2
    y = (y1 + y2) // 2

    adb("shell", "input", "tap", str(x), str(y))
    return True


def swipe_next(root):
    node = find(root, RID_JOB_NAME)
    if node is None:
        return False

    x1, y1, x2, y2 = parse_bounds(node)
    y = (y1 + y2) // 2

    adb(
        "shell",
        "input",
        "swipe",
        str(x2),
        str(y),
        str(x1),
        str(y),
        str(SWIPE_DURATION),
    )
    return True


def is_job_detail_page(root):
    return (
        find(root, RID_JOB_NAME) is not None
        and find(root, RID_CHAT_BTN) is not None
    )


def process_position(root, dry_run):
    job_name = get_text(root, RID_JOB_NAME)
    description = get_text(root, RID_DESCRIPTION)
    salary = get_text(root, RID_SALARY)
    location = get_text(root, RID_LOCATION)
    boss_name = get_text(root, RID_BOSS_NAME)

    print(f"职位：{job_name}")
    print(f"薪资：{salary}")
    print(f"地点：{location}")
    print(f"招聘者：{boss_name}")
    print(f"描述：{description}")

    if find(root, RID_CHAT_BTN) is None:
        print("结果：找不到打招呼按钮，跳过")
        return False

    if dry_run:
        print("结果：找到打招呼按钮（dry-run，未点击）")
        return False

    tap(root, RID_CHAT_BTN)
    print("结果：打招呼")
    return True


def run(count=DEFAULT_COUNT, dry_run=False):
    root = dump_ui()
    if not is_job_detail_page(root):
        print("当前不是 Boss直聘职位详情页，未执行任何点击或滑动。")
        return 1

    clicked = 0

    for index in range(count):
        print(f"\n========== [{index + 1}/{count}] ==========")

        try:
            root = dump_ui()
            was_clicked = process_position(root, dry_run)

            if was_clicked:
                clicked += 1
                time.sleep(SLEEP_TAP)
                adb("shell", "input", "keyevent", "4")
                time.sleep(SLEEP_BACK)
                root = dump_ui()

            if not swipe_next(root):
                print("结果：找不到职位名称控件，无法切换到下一个职位")

            time.sleep(SLEEP_SWIPE)

        except Exception as exc:
            print(f"异常：{exc}")
            time.sleep(SLEEP_ERROR)

    if dry_run:
        print(f"\n任务完成：已预览 {count} 个职位，未执行点击。")
    else:
        print(
            f"\n任务完成：共处理 {count} 个职位，"
            f"成功打招呼 {clicked} 个。"
        )
    return 0


def parse_args():
    parser = argparse.ArgumentParser(
        description="检查 ADB 连接并批量执行 Boss直聘打招呼。"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=DEFAULT_COUNT,
        help=f"处理职位数量，默认 {DEFAULT_COUNT}。",
    )
    parser.add_argument(
        "--serial",
        help="ADB 设备序列号；连接多个设备时必须指定。",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="仅检查 ADB 设备连接，不读取页面或执行点击。",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="读取职位信息并切换，但不点击打招呼按钮。",
    )
    return parser.parse_args()


def main():
    global ADB, ADB_SERIAL

    args = parse_args()
    if args.count <= 0:
        print("[错误] --count 必须大于 0。", file=sys.stderr)
        return 2

    try:
        ADB = resolve_adb()
        ADB_SERIAL = ensure_adb_connection(args.serial)
        print(f"ADB 已连接：{ADB_SERIAL}")

        if args.check:
            print("ADB 连接检查通过。")
            return 0

        return run(args.count, args.dry_run)
    except AdbError as exc:
        print(f"[ADB 错误] {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\n用户中止。", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
