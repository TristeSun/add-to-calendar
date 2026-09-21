# add-to-calendar

> 把课表、校历、会议通知、机票/火车行程单（文件或截图）批量解析并写入 **macOS 日历（Calendar.app）** 的 Agent Skill。
>
> An Agent Skill that batch-parses class schedules, academic calendars, meeting notices and flight/train itineraries (files or screenshots) into **Apple Calendar on macOS**.

---

## 目录 / Contents

- [中文说明](#中文说明)（默认）
- [English](#english)

---

## 中文说明

### 这是什么

把"人发来的日程材料"变成"日历里整齐的事件"。你把课表截图、选课系统导出的 xlsx、校历 PDF、会议通知或航班行程单直接发给你的 AI Agent（ZCode / Claude Code / Codex 等），它就会：

1. **提取**：读 xlsx 课表（含合并单元格）、PDF、截图、聊天消息里的日程；
2. **换算日期**：`日期 = 第1周周一 + (周次-1)×7 + (星期几-1)`，节次 → 具体时刻，并处理节假日与调休（补课/停课）；
3. **确认计划**：先给你看将要写入的事件清单和所做假设；
4. **写入日历**：通过 `scripts/cal.py` 批量写入 Calendar.app，自动按标题+时间去重；
5. **核对与冲突提醒**：写完回读核对条数，检查与已有课程/行程的时间冲突（只报告，不擅自删改）。

### 用户需要做什么（3 步）

**第 1 步：安装 skill**

把整个 `add-to-calendar` 文件夹拷贝到你所用 agent 的 skills 目录（没有就新建）：

```bash
mkdir -p ~/.agents/skills
cp -r /path/to/add-to-calendar ~/.agents/skills/
# ZCode 用户也可以放 ~/.zcode/skills/
```

重启 agent 会话后，skill 会被自动发现。你不需要背任何命令——

**第 2 步：授权（仅首次）**

macOS 会要求"终端/agent App 控制日历"的权限。首次写入时如果弹出授权窗口，点"允许"；如果没弹或误点了拒绝：

> 系统设置 → 隐私与安全性 → 自动化 → 找到你的终端 App → 勾选"日历"

**第 3 步：发材料 + 说一句话**

把课表/校历/通知发给 agent，同时告诉它两件只有你知道的事：

- 📅 **第 1 周周一是哪天**（校历上有；agent 不会猜）
- 🗂 **想写进哪个日历**（没有就让它新建，比如"专业课""生活"）

示例：

> "这是我的课表截图和校历，第 1 周周一是 9 月 1 日，课写进「专业课」，其他写进「生活」，加到日历。"

之后的所有解析、换算、写入、核对都由 agent 完成。

### 支持的输入

| 输入 | 说明 |
|---|---|
| xlsx 课表 | 选课系统/教务系统导出，含合并单元格也能读 |
| PDF 校历/通知/行程单 | 有文字层直接读；扫描件会转图片识别 |
| 截图/照片 | 课表截图、微信聊天记录、会议通知照片 |
| 一句话 | "周三下午 3 点和王老师开会"也行 |

### 给 Agent 的说明

Agent 请完整阅读 [SKILL.md](SKILL.md) 后再动手，要点：

- 一律用 `scripts/cal.py`，**不要手写 osascript**（日期本地化、allday 损坏、whose 查询等坑已封装，见 SKILL.md"已知坑"）；
- **第 1 周周一只能从用户的校历获取**，节次表以用户材料为准（本仓库 `references/timetables.md` 只是作者本机的默认值，其他用户请替换或直接在对话中提供）；
- 写入前先 `--dry-run` 预览；写完必须 `list` 回读核对；冲突**只报告不删改**；
- 模糊时间（"下午3点左右"）按整点记、时长未知默认 1 小时，并**必须向用户说明假设**。

`cal.py` 命令一览：

```bash
cal.py calendars                                   # 列出所有日历
cal.py list --calendar 生活 --from 2026-09-01 --to 2026-09-30 [--title 关键词]
cal.py add --calendar 生活 --file events.json [--dry-run]
cal.py conflicts --file events.json --calendars 专业课,公共课
cal.py delete --calendar 生活 --title "xx" --from ... --to ... [--yes]
```

事件文件为 JSON 数组：

```json
[
  {"title": "天文写作", "start": "2026-09-09 13:30", "end": "2026-09-09 16:10",
   "location": "B201", "notes": "第2周 周三(5-7节)", "calendar": "专业课"}
]
```

### 环境要求

- macOS（依赖 Calendar.app + AppleScript）
- Python 3（仅标准库；解析 xlsx 另需 `pip install openpyxl`）
- 终端对"日历"的自动化权限（见上）

### 已知限制

- **全天事件属性在 AppleScript 下损坏**（系统报 -1700），跨天活动用"首尾带具体时间的计时日程"替代；
- 走 AppleScript 而非 EventKit（后者对终端的权限模型不可用）；
- 批量写入可能"部分成功后中止"，脚本已按标题+时间去重，重跑安全，但重跑前建议先 `list` 看现场。

---

## English

### What is this

An agent skill that turns schedule material you send (class timetables, academic calendars, meeting notices, flight itineraries — as files or screenshots) into clean Apple Calendar events on macOS. Your AI agent (ZCode, Claude Code, Codex, …) will:

1. **Extract** events from xlsx (merged cells supported), PDF, screenshots, or chat messages;
2. **Convert** week numbers + class periods into real dates/times using your academic calendar (week-1 Monday), handling holidays and make-up classes;
3. **Confirm** the plan and its assumptions with you before writing;
4. **Write** events into Calendar.app via `scripts/cal.py` (dedup by title + start time);
5. **Verify** by reading back, and **report conflicts** with existing events (report only — never deletes/modifies on its own).

### What YOU need to do (3 steps)

1. **Install** — copy this folder into your agent's skills directory:

   ```bash
   mkdir -p ~/.agents/skills
   cp -r /path/to/add-to-calendar ~/.agents/skills/
   # ZCode users may also use ~/.zcode/skills/
   ```

   Restart your agent session; the skill is discovered automatically.

2. **Grant permission (first time only)** — macOS needs your terminal/agent app to control Calendar. Approve the popup on first run, or set it manually:
   *System Settings → Privacy & Security → Automation → your terminal app → Calendar*.

3. **Send your schedule + two facts** — give the agent your timetable/calendar files and tell it:
   * the date of **Week-1 Monday** (from your academic calendar — the agent will not guess), and
   * which **calendar names** to use (e.g. "Courses", "Life"; it can create them).

   Example: *"Here's my timetable screenshot and academic calendar. Week-1 Monday is Sep 1. Put courses into 'Courses' and everything else into 'Life', add to my calendar."*

   Everything else — parsing, date math, writing, verification — is the agent's job.

### For agents

Read [SKILL.md](SKILL.md) in full before acting. Key rules: always use `scripts/cal.py` (never hand-write osascript — localization, broken all-day events and `whose` pitfalls are already handled); get Week-1 Monday only from the user's academic calendar; `--dry-run` before writing, `list` to verify after; report conflicts without deleting; state assumptions for fuzzy times (default duration 1 hour).

`references/timetables.md` ships the author's local period tables (Nanjing College / USTC) as a default — replace it with your own or provide times in chat.

### Requirements

- macOS with Calendar.app; Python 3 (stdlib only; `pip install openpyxl` for xlsx); Automation permission for your terminal (see above).

### Known limitations

- The all-day flag is broken in Calendar's AppleScript bridge (error -1700): multi-day events are written as timed events spanning days instead.
- Uses AppleScript rather than EventKit.
- Batch writes can abort midway after partial success; the script dedups by title + start time, so re-running is safe — but check with `list` first.

---

## License

[MIT](LICENSE)
