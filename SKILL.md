---
name: add-to-calendar
description: 把课表、校历、选课系统截图、会议通知、机票/火车行程单等文件或聊天截图里的日程批量写入 macOS 日历（Calendar.app），并检查与已有课程/行程的时间冲突。Use whenever the user wants to 把…加到日历/添加日程/记一下行程/排个日程, sends 课表、校历、会议通知、座谈会通知、机票行程单、航班信息 screenshots or files and expects calendar events, asks 日历里有什么/查一下某天的安排, or wants conflicts checked — even if they don't say "日历" explicitly but paste a schedule.
---

# add-to-calendar：日程解析 + macOS 日历批量写入

把用户发来的课表/通知/行程变成日历事件。核心循环：**提取 → 换算日期 → 确认计划 → 写入 → 核对与冲突提醒**。配套脚本 `scripts/cal.py` 已封装全部 AppleScript 细节，优先用它，不要手写 osascript。

本 skill 对任何学校/单位通用：**第1周周一、节次→时刻表、目标日历名**一律以用户当次提供的校历/课表/指示为准；`references/timetables.md` 只是本机（南京学院/中国科大）的默认事实，其他用户请替换成自己的材料，或直接在对话里告诉 agent。

## 1. 提取内容

按输入类型路由：

| 输入 | 方法 | 坑 |
|---|---|---|
| .xlsx 课表 | openpyxl（缺就 `pip install openpyxl`） | 课表靠合并单元格布局，**必须同时读 merged_cells**，空值要按合并区域归位 |
| PDF（校历/行程单/会议手册） | document-skills 插件：`P=$(ls -d ~/.zcode/cli/plugins/cache/zcode-plugins-official/document-skills/*/skills/pdf 2>/dev/null | tail -1); python3 "$P/scripts/pdf.py" extract.text 文件.pdf`；插件未安装就直接用 pdfplumber/pypdf 提取 | **stderr 必须丢弃**（`2>/dev/null`）：字体警告会刷屏并污染 JSON 管道；若提取不到文字层，把页面渲染成 PNG 后用视觉读 |
| 截图/图片 | 直接用 Read 工具看 | 微信截图常含"周次:(节次)"缩写，按 §2 解码 |
| 微信聊天消息 | 直接读 | "下午3点左右"这类模糊时间按整点记，时长未知默认 1 小时，**必须向用户说明假设** |

微信临时目录（`.../WeChat/temp/...`）里的文件会被自动清理，如需复用先拷到工作区。

## 2. 换算成具体日期

**周次 → 日期**：`日期 = 第1周周一 + (周次-1)×7 + (星期几-1) 天`。第1周周一**只能从校历上拿**，不要猜。

**节次 → 时间**：两所学校的节次表在 `references/timetables.md`。⚠️ 每学期可能调整，校历/通知里附了上课时间表时以附件为准；同一门课**不同周次的节次可能不同**（课表会分多行写，逐行处理）。

**节假日与调休**（依次做）：
1. 先看课表自己有没有处理调休（比如"第6周 周六(5-7)"就是补进假期的课）——课表已有的行不要重复推算。
2. 假日（中秋/国庆/元旦等）当天且课表未安排的课 → 跳过。
3. 校历注明"X日（周几）补周Y的课"且课表**没有**对应行时：若课程周次范围覆盖被顶掉的那个原日期、且课程有周Y的课，才在 X 日按周Y节次补一条。
4. "另行通知"的假期（如元旦）：照常排课，在总结里提醒用户留意通知。

## 3. 确定日历与事件字段

- 用户日历名先看 `references/timetables.md` 的默认映射：课程按属性进 **专业课/公共课**，会议、航班、出差进 **生活**。用户指定了就用用户的；日历不存在时先问一句或建新日历。
- 字段：`title` 干净课名/事由；`location` 教室/机场/会议室；`notes` 写周次、节次、航班号、票号、主讲、用餐等一切用户以后要查的信息；冲突多发的重复课**每条都带周次**，方便日后单条改。
- 航班：按起飞–落地建一条，notes 里写航站楼、订单号。

## 4. 写入（scripts/cal.py）

```bash
# 先预览
python3 ~/.agents/skills/add-to-calendar/scripts/cal.py add --calendar 生活 --file events.json --dry-run
# 正式写入（自动按标题+时间去重；单条失败不影响其余）
python3 ~/.agents/skills/add-to-calendar/scripts/cal.py add --calendar 生活 --file events.json
```

写入前**必须**先去重确认（脚本内置按标题+开始时间去重，重复跑安全）；如果上次跑到一半失败，先 `list` 看现场再补跑。

## 5. 核对 + 冲突提醒

```bash
python3 ~/.agents/skills/add-to-calendar/scripts/cal.py list --calendar 生活 --from 2026-09-07 --to 2026-09-15
python3 ~/.agents/skills/add-to-calendar/scripts/cal.py conflicts --file events.json --calendars 专业课,公共课
```

- 写完必须回读核对条数和首末场次。
- 发现课程与出差/会议时间冲突时：**只报告，不删不改**，给出哪天哪节与哪个行程撞、建议用户请假或调整。
- 汇报格式：一张日期/日程/时间/地点表 + 假设说明（估算的时长、模糊的时间）+ 冲突警告。来源文件用 `::zcode-file-citation` 引用。

## 已知坑（都已封装/规避，但别"优化"掉）

- **allday 属性在本机 macOS 的 Calendar AppleScript 里是坏的**（with-properties 和事后 set 都报 -1700），EventKit 权限对终端不可用 → 跨天活动用"首尾带具体时间的计时日程"替代全天横幅。
- AppleScript 日期字面量随系统语言变化 → 只能用 `mkdate` 逐组件构造（脚本内已实现），永远不要拼 `date "2026-09-09 13:30"`。
- `whose` 查询结果需要变量中转，直接 `count of (events of ...)` 嵌套过深会报错；批量脚本可能**部分成功后中止**，重试前先看现场。
- osascript 的 Apple Events 权限已授予；EventKit 未授予。
