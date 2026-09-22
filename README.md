# Boss直聘自动打招呼 Skill

一个让 Agent 用 ADB 驱动**安卓手机**、在 Boss直聘 App 上批量点“打招呼”的 Skill。

你只要把手机连上、停在某个职位的详情页，Agent 就会自动读取职位信息、点“打招呼”、返回并左滑切到下一个职位，默认连续处理 10 个。

- 目标应用：Boss直聘（`com.hpbr.bosszhipin`）
- 运行方式：手机 USB 连接 + `adb` + 手机端 `uiautomator`，Python 标准库，无需 Appium / AirTest
- 默认脚本：`scripts/auto_greet.py`（由 `scripts/run_auto_greet.cmd` 包装调用）

## 它能做什么

对当前职位详情页，逐个执行：

1. 检查 ADB 连接（只接受状态为 `device` 的已授权设备）。
2. 读取职位名称、职位描述、薪资、工作地点、招聘者姓名。
3. 点击“打招呼”。
4. 返回上一页，再左滑切换到下一个职位。
5. 汇总每个职位的处理结果和成功打招呼数量。

不会做的事：不投递简历、不发送自定义聊天内容、不在无法识别的页面上盲点。

## 前置条件

- 安卓手机开启**USB 调试**，并在手机上授权本机电脑（`adb devices` 显示 `device`）。
- 本机有 `adb`，且能从 `PATH`、`ADB` 环境变量或常见 Android SDK 目录中找到。
- 有 Python 3（脚本只依赖标准库）。
- **把手机停在 Boss直聘的职位详情页**再启动脚本——本项目没有已验证的职位列表卡片控件，无法从列表页自动进入第一个职位。

`scripts/run_auto_greet.cmd` 会自动在 `D:\Program Files (x86)\*\python-embed\python.exe` 里找解释器；如果你的 Python 装在别处，直接改用 `python scripts/auto_greet.py` 即可。

## 快速开始

```powershell
# 1. 先确认手机连接正常（不读页面、不点击）
python scripts/auto_greet.py --check

# 2. 在手机上打开某个职位的详情页，然后开始自动打招呼
python scripts/auto_greet.py
```

或用包装脚本（自带 UTF-8 输出设置）：

```powershell
scripts\run_auto_greet.cmd --count 10
```

## 常用参数

| 参数 | 说明 |
| --- | --- |
| `--check` | 只检查 ADB 连接，不读取页面、不点击 |
| `--count N` | 处理多少个职位，默认 `10` |
| `--serial SERIAL` | 指定设备序列号；同时连接多台手机时必须指定 |
| `--dry-run` | 读取并切换职位，但不点“打招呼”（仅预览用） |

连接检查不通过（无设备 / `offline` / `unauthorized` / 多设备未指定 `--serial`）时，脚本会直接报错退出，不会做任何点击或滑动。

## 已验证的控件

以下控件 ID 已在真实设备上验证可用，脚本依赖它们定位页面。

职位详情页：

| 控件 ID | 用途 |
| --- | --- |
| `com.hpbr.bosszhipin:id/tv_job_name` | 职位名称 |
| `com.hpbr.bosszhipin:id/tv_description` | 职位描述 |
| `com.hpbr.bosszhipin:id/tv_job_salary` | 职位薪资 |
| `com.hpbr.bosszhipin:id/tv_required_location` | 工作地点 |
| `com.hpbr.bosszhipin:id/tv_boss_name` | 招聘者姓名 |
| `com.hpbr.bosszhipin:id/btn_chat` | 打招呼 |

个人投递数据：

| 控件 ID | 用途 |
| --- | --- |
| `com.hpbr.bosszhipin:id/tv_geek_contacts_number` | 沟通数量 |
| `com.hpbr.bosszhipin:id/tv_geek_post_resume_number` | 投递数量 |
| `com.hpbr.bosszhipin:id/tv_interview_count` | 面试数量 |

页面缺少 `tv_job_name` 或 `btn_chat` 时，脚本会判定“当前不是职位详情页”并停止，而不是猜测页面结构。

## 目录结构

```text
boss-zhipin-automation/
|-- SKILL.md              # Agent 加载的上下文、事实与操作规范
|-- README.md             # 本文件
|-- agents/
|   `-- openai.yaml       # Skill 的显示信息和默认调用提示词
`-- scripts/
    |-- auto_greet.py       # 自动打招呼主脚本
    `-- run_auto_greet.cmd  # Windows 包装脚本
```

## 安装为本地 Skill

Codex 从 `.agents/skills` 加载本地 Skill，安装后的目录必须直接包含 `SKILL.md`：

```text
.agents/
`-- skills/
    `-- boss-zhipin-automation/
        |-- SKILL.md
        |-- README.md
        |-- agents/
        `-- scripts/
```

用户级（对所有仓库可用）——Windows：

```powershell
$target = Join-Path $HOME ".agents\skills\boss-zhipin-automation"
New-Item -ItemType Directory -Force -Path $target | Out-Null
Copy-Item -Recurse -Force .\SKILL.md, .\README.md, .\agents, .\scripts $target
```

用户级——macOS / Linux：

```bash
target="$HOME/.agents/skills/boss-zhipin-automation"
mkdir -p "$target"
cp -R SKILL.md README.md agents scripts "$target/"
```

仓库级（只对当前仓库可用）把同样的文件复制到 `<repo>/.agents/skills/boss-zhipin-automation/`。开发期间也可以把安装位置直接符号链接到本仓库，改完 `SKILL.md` 无需重复安装。

安装后可用 `/skills` 查看、用 `$boss-zhipin-automation` 显式调用，或由 Codex 根据 `description` 隐式调用；修改后若未生效，重启 Codex。

## 事实分级与使用边界

`SKILL.md` 中明确列出的控件和操作才算**已验证事实**；其余页面结构、控件 ID 和交互行为仍需用当前设备上的 UI 树、运行结果或截图确认。

因此当需求涉及未知控件时，Agent 应：

- 不编造控件 ID、不假设页面结构、不把固定坐标当作默认方案；
- 先向你索要当前页面的控件树 / Accessibility 信息 / 页面截图；
- 在信息不足时明确说明“目前无法可靠定位”，而不是静默降级成坐标点击。

修改自动化代码时优先做最小改动、复用已有实现和已验证控件，不做与需求无关的重构。
