# Boss直聘自动化 Skill

这是一个面向 Codex 的 Skill，用于处理 Boss直聘 Android 自动化项目中的代码开发、控件定位、页面操作和问题排查。

它的重点不是介绍 Auto.js 或某个自动化框架的 API，而是为 Agent 提供项目上下文和行为约束，使 Agent 能够区分已经验证的事实、根据代码作出的推断，以及尚未验证的假设。

## 主要能力

- 记录 Boss直聘 Android 自动化项目中已经验证的 UI 控件和操作。
- 约束 Agent 优先复用已有代码和已验证控件。
- 规范未知控件、控件定位失败和 UI 结构变化时的处理方式。
- 避免 Agent 编造控件 ID、默认依赖固定坐标或进行不必要的重构。
- 要求 Agent 在缺少页面证据时说明信息缺口，并请求必要的 UI 树或截图。

目标应用信息：

- 应用名称：Boss直聘
- Package：`com.hpbr.bosszhipin`

已验证控件和操作的完整说明见 [SKILL.md](SKILL.md)。

## 目录结构

```text
boss-zhipin-automation/
|-- SKILL.md
|-- README.md
`-- agents/
    `-- openai.yaml
```

- `SKILL.md`：Agent 实际加载的上下文、事实和操作规范。
- `agents/openai.yaml`：Skill 在界面中的显示信息和默认调用提示词。
- `README.md`：项目面向使用者的说明。

## 使用方式

Codex 会从仓库、用户、管理员和系统位置加载本地 Skill。本项目的本地安装目标是 `.agents/skills` 下的 Skill 目录。

安装后的目录必须直接包含 `SKILL.md`、`README.md` 和可选的 `agents/`：

```text
.agents/
`-- skills/
    `-- boss-zhipin-automation/
        |-- SKILL.md
        |-- README.md
        `-- agents/
            `-- openai.yaml
```

### 安装为用户级 Skill

用户级 Skill 对所有仓库可用。

Windows 默认位置：

```text
%USERPROFILE%\.agents\skills\boss-zhipin-automation\
```

在 PowerShell 中，进入本项目根目录后执行：

```powershell
$target = Join-Path $HOME ".agents\skills\boss-zhipin-automation"
New-Item -ItemType Directory -Force -Path $target | Out-Null
Copy-Item -Recurse -Force .\SKILL.md, .\README.md, .\agents $target
```

macOS 和 Linux 默认位置：

```text
~/.agents/skills/boss-zhipin-automation/
```

在终端中，进入本项目根目录后执行：

```bash
target="$HOME/.agents/skills/boss-zhipin-automation"
mkdir -p "$target"
cp -R SKILL.md README.md agents "$target/"
```

### 安装为仓库级 Skill

仓库级 Skill 只对对应仓库可用，适合团队一起维护。Codex 会从当前工作目录逐级向上扫描 `.agents/skills`，直到仓库根目录。

目标位置：

```text
<repo>/.agents/skills/boss-zhipin-automation/
```

Windows PowerShell 示例：

```powershell
$source = "C:\path\to\boss-zhipin-automation"
$target = Join-Path (Get-Location) ".agents\skills\boss-zhipin-automation"
New-Item -ItemType Directory -Force -Path $target | Out-Null
Copy-Item -Recurse -Force "$source\SKILL.md", "$source\README.md", "$source\agents" $target
```

macOS 和 Linux 示例：

```bash
source_dir="/path/to/boss-zhipin-automation"
target=".agents/skills/boss-zhipin-automation"
mkdir -p "$target"
cp -R "$source_dir/SKILL.md" "$source_dir/README.md" "$source_dir/agents" "$target/"
```

Codex 也支持符号链接的 Skill 目录。开发期间可以让安装位置链接到本项目，这样修改 `SKILL.md` 后不需要重复安装。

### 安装为管理员级 Skill

管理员级 Skill 适合共享机器或容器环境。Codex 在 Linux 和 macOS 上读取的管理员级位置是：

```text
/etc/codex/skills/boss-zhipin-automation/
```

在本项目根目录执行：

```bash
sudo mkdir -p /etc/codex/skills/boss-zhipin-automation
sudo cp -R SKILL.md README.md agents /etc/codex/skills/boss-zhipin-automation/
```

管理员级安装需要相应的系统权限。Windows 的管理员级 Skill 路径未在这份 Codex 文档中列出，因此不要自行假定安装位置。

### 调用与刷新

安装后可以：

- 使用 `/skills` 查看当前可用的 Skill。
- 使用 `$boss-zhipin-automation` 显式调用。
- 让 Codex 根据 `description` 在相关任务中隐式调用。

Codex 会自动检测 Skill 变更。如果新安装或修改后的 Skill 没有出现，重启 Codex。

### 启用或禁用

可以在 `~/.codex/config.toml` 中禁用某个本地 Skill，而无需删除文件：

```toml
[[skills.config]]
path = "/absolute/path/to/boss-zhipin-automation/SKILL.md"
enabled = false
```

修改 `config.toml` 后需要重启 Codex。

### 关于 skill-installer

`$skill-installer` 用于安装 OpenAI 精选 Skill 或其他仓库中的 Skill。本项目是本地 Skill，应通过 `.agents/skills` 安装，不建议执行：

```text
$skill-installer boss-zhipin-automation
```

如果需要把本项目分发给其他用户，后续可以将它打包为 plugin。

## 使用边界

本 Skill 只把 `SKILL.md` 中明确列出的控件和操作视为已验证事实。其他页面结构、控件 ID 和交互行为仍然需要通过当前项目的代码、运行结果或 UI 树进行确认。

如果需求涉及未知控件或无法定位的控件，应优先获取当前页面的控件树、Accessibility 信息、Poco UI 树或页面截图，不要把固定坐标作为默认替代方案。
