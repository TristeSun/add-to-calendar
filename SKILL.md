---
name: add-to-calendar
description: 把课表、校历、选课系统截图、会议通知、机票/火车行程单等文件或聊天截图里的日程批量写入 macOS 日历（Calendar.app），并检查与已有课程/行程的时间冲突。Use whenever the user wants to 把…加到日历/添加日程/记一下行程/排个日程, sends 课表、校历、会议通知、座谈会通知、机票行程单、航班信息 screenshots or files and expects calendar events, asks 日历里有什么/查一下某天的安排, or wants conflicts checked — even if they don't say "日历" explicitly but paste a schedule.
---

# add-to-calendar：日程解析 + macOS 日历批量写入

把用户提供的课表、校历、通知和行程整理成 Calendar.app 事件。流程是：**提取 → 换算日期 → 预览并确认 → 写入 → 回读核对与冲突提醒**。

本 skill 使用通用的 Markdown、Python 和 AppleScript，可由 Codex 与 ZCode 共用。使用当前 agent 提供的文件、PDF、图片和终端工具：在 ZCode 中可用 document-skills 插件或 ZCode 文件引用时可以照常使用；在 Codex 中使用 Codex 当前可用的工具和引用方式。不要假设两边的工具名称或安装路径相同。

## 适用环境

- 日历写入依赖 macOS 的 Calendar.app 和 `osascript`。写入时，agent 必须能在这台 Mac 上运行本地命令，并且终端或 agent 应用已获得 macOS「自动化」权限。
- 如果当前 agent 在云端或其他机器上运行，可以解析材料、换算日期并生成预览，但不能声称已写入用户 Mac 的 Calendar.app。
- 正式写入前先展示事件清单和假设，等用户确认后再执行。

## 1. 提取日程信息

| 输入 | 处理方式 | 注意事项 |
|---|---|---|
| `.xlsx` 课表 | 用 `openpyxl` 读取 | 课表可能使用合并单元格；读取 `merged_cells` 并将合并区域内容归回对应日期与节次 |
| PDF 校历、通知、行程单 | 使用当前 agent 可用的 PDF 阅读工具；ZCode 中若已安装 document-skills 插件，可优先使用；否则用本机已安装的 `pdfplumber` 或 `pypdf` 提取文字 | 扫描件没有文字层时，使用可用的 OCR 或图片阅读能力；Codex 与 ZCode 都按当前环境选工具，不要写死插件路径 |
| 截图或照片 | 使用当前 agent 的图片阅读能力 | 微信截图可能用「周次:(节次)」缩写，按 §2 解码 |
| 聊天消息 | 直接提取日程信息 | 「下午 3 点左右」按 15:00 处理；时长未知时默认 1 小时，并在预览中说明假设 |

如果源文件在会自动清理的临时目录中、后续还要重复读取，先复制到工作目录。

## 2. 换算日期和时间

**周次 → 日期**：`日期 = 第 1 周周一 + (周次 - 1) × 7 + (星期几 - 1) 天`。第 1 周周一必须来自用户提供的校历或明确说明，不要猜。

**节次 → 时间**：先查 `references/timetables.md`。该文件含特定学校、学期的默认信息；若与用户材料不符，以用户当次提供的材料为准。同一门课在不同周次可能有不同节次，按课表逐行处理。

**节假日与调休**，依次核对：

1. 先看课表是否已经列出补课日（例如周六按周三节次上课）；已有安排不要再推算一遍。
2. 假期当天且课表未安排课程时，跳过原本会落在该日的课。
3. 校历注明某日补星期 Y 的课、课表又没有该补课日时，仅当该课程周次覆盖原日期且星期 Y 有这门课，才按星期 Y 的节次补一条。
4. 校历写「另行通知」的假期，暂按课表排课，并在汇报中提醒用户留意后续通知。

## 3. 确定日历和事件字段

- 使用用户指定的日历名称。`references/timetables.md` 中的日历映射是作者本机默认值，只有适用于当前用户时才沿用。
- 如果目标日历不存在，先确认用户希望使用的名称；只有当前环境支持创建日历且用户已确认时才创建。`scripts/cal.py` 本身不提供创建日历的命令。
- `title` 写清楚课程名或事由；`location` 写教室、机场或会议室；`notes` 保留周次、节次、航班号、票号等之后可能要查的信息。重复课程的每个事件都写明周次。
- 航班按起飞至落地建一条事件；航站楼、订单号等放进 `notes`。

## 4. 预览并写入（`scripts/cal.py`）

使用当前 skill 实际安装目录下的 `scripts/cal.py`。不要假定固定的 ZCode、Codex 或 Claude Code 路径。常见个人目录是 ZCode 的 `~/.zcode/skills/add-to-calendar` 和 Codex 的 `~/.agents/skills/add-to-calendar`；其他安装位置请按当前加载的 `SKILL.md` 路径解析。

先预览：

```bash
python3 /ABSOLUTE/PATH/TO/add-to-calendar/scripts/cal.py add \
  --calendar 生活 --file events.json --dry-run
```

向用户展示待写入事件、日期来源和所有估算，再等待确认。用户确认后才去掉 `--dry-run` 执行写入：

```bash
python3 /ABSOLUTE/PATH/TO/add-to-calendar/scripts/cal.py add \
  --calendar 生活 --file events.json
```

脚本按标题和开始时间跳过重复事件。若写入中途失败，先用 `list` 查看已写入部分，再补写剩余事件。

## 5. 回读核对和冲突提醒

写入后必须用 `list` 回读核对事件数量、日期和首末场次，并用 `conflicts` 检查与相关日历的时间冲突：

```bash
python3 /ABSOLUTE/PATH/TO/add-to-calendar/scripts/cal.py list \
  --calendar 生活 --from 2026-09-07 --to 2026-09-15
python3 /ABSOLUTE/PATH/TO/add-to-calendar/scripts/cal.py conflicts \
  --file events.json --calendars 专业课,公共课
```

冲突只报告，不自动删除或修改已有事件。回复中用日期、日程、时间、地点列出结果，说明日期来源和不确定假设；在 ZCode 中可用 `::zcode-file-citation` 标注来源，在 Codex 中使用当前可用的文件引用方式；如没有引用能力，写出文件名和页码。

## 已知限制

- 本项目目标环境中的 Calendar.app AppleScript 全天事件标记不可用；跨天活动用带明确起止时间的计时事件表示。
- 日期由 AppleScript 逐组件构造，以兼容不同系统语言；不要拼接本地化日期字面量。
- AppleScript `whose` 查询需使用脚本中的写法。批量写入可能部分成功，重试前先回读现场。
- 自动化权限由 macOS 控制，agent 不能通过本 skill 绕过系统权限。
