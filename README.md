# add-to-calendar

把课表、校历、会议通知和行程单整理成 macOS「日历」里的事件。Agent 会先读取材料、按校历换算日期，再给你一份待写入清单；确认后才写入，并回读核对、提示时间冲突。

适合每学期要录入一批课程，或想把 PDF、表格、截图和聊天里的安排集中进日历的人。

## 能做什么

- 从 xlsx、PDF、图片和文字中提取课程、会议与出行安排；读取合并单元格课表。
- 按第 1 周周一、周次、星期和节次换算实际日期与时间，并结合校历处理放假、补课和停课。
- 写入前预览；写入时按标题和开始时间跳过重复事件；写入后回读核对并报告日程冲突。

冲突只会报告给你，不会自动删除或改动已有事件。

## 适用范围与 Agent 兼容性

本项目使用 `SKILL.md`、`scripts/` 和 `references/` 组织内容，符合开放的 [Agent Skills 格式](https://agentskills.io/specification)。同一份 skill 可供 ZCode、Codex 和 Claude Code 使用；Codex 与 Claude Code 的安装目录按各自文档为准：[Codex Skills](https://developers.openai.com/api/docs/guides/tools-skills) · [Claude Code Skills](https://code.claude.com/docs/en/skills)。

同一份 `SKILL.md` 同时面向 Codex 和 ZCode：在 ZCode 中可继续使用已安装的 document-skills 和原生文件引用；在 Codex 中使用 Codex 当前提供的文件、PDF、图片和终端工具。skill 本身不要求其中任何一方，也不假设两边的工具名称和安装目录相同。若自动发现没有触发，可在对话中明确要求使用 `add-to-calendar`。运行写入仍有两个条件：

- `references/timetables.md` 含作者所在学校的课时、校历和日历名称。使用前请替换成自己的信息，或以当次提供的材料为准。
- 写入由 `scripts/cal.py` 通过 AppleScript 控制 Calendar.app。Agent 必须能在装有 Calendar.app 的 Mac 上运行本地命令；仅能访问云端容器的 agent 无法替你操作这台 Mac 的日历。

安装位置示例：

| Agent | 常见个人 skill 目录 |
|---|---|
| ZCode | `~/.zcode/skills/add-to-calendar` |
| Codex | `~/.agents/skills/add-to-calendar` |
| Claude Code | `~/.claude/skills/add-to-calendar` |

其他 agent 请使用其文档指定的 skills 目录。安装后若 agent 没有自动发现 skill，可在对话中明确要求它使用 `add-to-calendar`。

## 安装与运行

把整个仓库复制到对应目录。例如 Codex：

```bash
mkdir -p ~/.agents/skills
cp -R /path/to/add-to-calendar ~/.agents/skills/
```

Claude Code 用户把目标目录改为 `~/.claude/skills`；ZCode 用户可使用 `~/.zcode/skills`。然后按 agent 的说明重新加载或启动会话。

运行前准备好两项信息：

1. 校历上的「第 1 周周一」日期。Agent 不应靠猜测补出这一天。
2. 目标日历名称，例如「专业课」或「生活」。脚本不会创建日历；如果目标日历还不存在，请先在 Calendar.app 中创建。

把材料和这两项信息发给 agent。先检查它列出的事件、日期换算和假设，再让它写入。

例如：「这是我的课表截图和校历。第 1 周周一是 8 月 31 日，课程放进『专业课』。请先列出安排，我确认后再写入。」

## 环境要求

- macOS 和 Calendar.app；Calendar 自动化权限需授予运行 agent 命令的终端或应用。
- Python 3；`cal.py` 本身只用标准库。读取 xlsx 需要 `openpyxl`。
- Agent 能读取所给文件和图片，并能在本机运行 Python 与 `osascript`。

首次写入时，macOS 可能会询问是否允许终端或 agent 应用控制「日历」。也可以在「系统设置 → 隐私与安全性 → 自动化」中启用权限。

## 命令示例

以下示例中的 `/path/to/add-to-calendar` 请替换成 skill 实际安装位置。

```bash
# 查看日历
python3 /path/to/add-to-calendar/scripts/cal.py calendars

# 预览 JSON 里的事件，不写入
python3 /path/to/add-to-calendar/scripts/cal.py add \
  --calendar 生活 --file events.json --dry-run

# 确认预览无误后写入
python3 /path/to/add-to-calendar/scripts/cal.py add \
  --calendar 生活 --file events.json

# 回读并检查时间冲突
python3 /path/to/add-to-calendar/scripts/cal.py list \
  --calendar 生活 --from 2026-09-01 --to 2026-09-30
python3 /path/to/add-to-calendar/scripts/cal.py conflicts \
  --file events.json --calendars 专业课,公共课
```

事件文件是 JSON 数组，例如：

```json
[
  {
    "title": "天文写作",
    "start": "2026-09-09 13:30",
    "end": "2026-09-09 16:10",
    "location": "B201",
    "notes": "第 2 周，周三第 5–7 节",
    "calendar": "专业课"
  }
]
```

## 注意事项

- `references/timetables.md` 里的节次表和校历是特定学校、特定学期的信息；每学期都要重新核对。
- AppleScript 的全天事件标记在本项目目标环境中不可用。跨天活动会写成带起止时间的计时事件。
- 批量写入中途可能有个别事件失败。脚本会跳过已存在的标题和开始时间；重跑前先用 `list` 查看日历。
- 模糊时间会按整点处理；没有时长时默认 1 小时。Agent 应在写入前把这些假设告诉你。

## English

Turn timetables, academic calendars, notices, and itineraries into events in Apple Calendar. The agent extracts the details, converts weeks and class periods into dates, shows you a preview, and writes events only after you confirm. It then reads them back and reports conflicts. Existing events are never changed automatically.

### Compatibility

The folder follows the open [Agent Skills format](https://agentskills.io/specification). The same skill is intended for ZCode, [Codex](https://developers.openai.com/api/docs/guides/tools-skills), and [Claude Code](https://code.claude.com/docs/en/skills). In ZCode, it can use the document-skills plugin and native file citations when available; in Codex, it uses the file, PDF, image, and terminal tools available there. Neither agent is excluded. Other agents can use it if they discover and read `SKILL.md`.

Calendar writes still require a local macOS session with Calendar.app, Python, `osascript`, and Automation permission; a cloud-only agent cannot control the Calendar app on your Mac. The timetable reference also contains the author's school-specific data and should be updated before use.

### Requirements and setup

- macOS with Calendar.app and permission for the agent's terminal to control it.
- Python 3. Install `openpyxl` to read xlsx files.
- Install the whole folder in your agent's skill directory. Common locations are `~/.zcode/skills`, `~/.agents/skills` (Codex), and `~/.claude/skills` (Claude Code).
- Before scheduling, provide the date of Week 1 Monday and the destination calendar name. Create the calendar in Calendar.app first if it does not exist, then check the preview before asking the agent to write events.

See the Chinese sections above for command examples, event JSON fields, and known limitations.

## License

[MIT](LICENSE)
