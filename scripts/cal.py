#!/usr/bin/env python3
"""cal.py — macOS 日历(Calendar.app)批量读写工具（add-to-calendar skill 配套）

所有 AppleScript 细节都已处理：本地化安全的日期构造、去重、单事件容错、
allday 属性损坏的规避。事件文件为 JSON 数组：

  [
    {"title": "天文写作", "start": "2026-09-09 13:30", "end": "2026-09-09 16:10",
     "location": "B201", "notes": "第2周 周三(5-7节)", "calendar": "专业课"}
  ]

start/end 支持 "YYYY-MM-DD HH:MM" 或 "YYYY-MM-DD"（后者按 00:00/23:59 处理，
多天跨度会生成连续的计时日程——不要试图用 allday，见 SKILL.md 已知坑）。
calendar 可写在事件里，或统一用 --calendar 指定。
"""
import argparse
import datetime as dt
import json
import subprocess
import sys

AS_HELP = """on mkdate(y, mo, dd, h, mi)
\tset d to current date
\tset day of d to 1
\tset year of d to y
\tset month of d to mo
\tset day of d to dd
\tset hours of d to h
\tset minutes of d to mi
\tset seconds of d to 0
\treturn d
end mkdate

on iso(d)
\tset out to (year of d as text) & "-"
\tset m to (month of d as integer)
\tif m < 10 then set out to out & "0"
\tset out to out & (m as text) & "-"
\tset dd to day of d
\tif dd < 10 then set out to out & "0"
\tset out to out & (dd as text) & " "
\tset h to hours of d
\tif h < 10 then set out to out & "0"
\tset out to out & (h as text) & ":"
\tset mi to minutes of d
\tif mi < 10 then set out to out & "0"
\tset out to out & (mi as text)
\treturn out
end iso"""


def osascript(src, timeout=600):
    p = subprocess.run(["osascript", "-"], input=src, capture_output=True,
                       text=True, encoding="utf-8", timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or "osascript failed")
    return p.stdout.strip()


def esc(s):
    return (s or "").replace("\\", "\\\\").replace('"', '\\"').replace("\n", "；")


def parse_event(e, default_cal):
    cal = e.get("calendar") or default_cal
    if not cal:
        raise ValueError(f"事件缺少 calendar 且未给 --calendar: {e.get('title')}")
    start = dt.datetime.strptime(e["start"], "%Y-%m-%d %H:%M") if len(e["start"]) > 10 \
        else dt.datetime.strptime(e["start"], "%Y-%m-%d")
    if len(e["end"]) > 10:
        end = dt.datetime.strptime(e["end"], "%Y-%m-%d %H:%M")
    else:
        end = dt.datetime.strptime(e["end"], "%Y-%m-%d").replace(hour=23, minute=59)
    return {"title": e["title"], "start": start, "end": end,
            "location": e.get("location", ""), "notes": e.get("notes", ""),
            "calendar": cal}


def mkdate_expr(t):
    t = t.replace(microsecond=0)
    return f"my mkdate({t.year}, {t.month}, {t.day}, {t.hour}, {t.minute})"


def cmd_calendars(a):
    out = osascript(f'{AS_HELP}\ntell application "Calendar" to return name of calendars')
    print(out)
    return 0


def cmd_list(a):
    lo = dt.datetime.strptime(a.from_date, "%Y-%m-%d")
    hi = dt.datetime.strptime(a.to_date, "%Y-%m-%d").replace(hour=23, minute=59)
    title_filter = f' and summary contains "{esc(a.title)}"' if a.title else ""
    src = f"""{AS_HELP}
tell application "Calendar"
\tset out to ""
\tset evs to (every event of calendar "{esc(a.calendar)}" whose start date ≥ {mkdate_expr(lo)} and start date ≤ {mkdate_expr(hi)}{title_filter})
\trepeat with e in evs
\t\tset out to out & my iso(start date of e) & "|" & my iso(end date of e) & "|" & summary of e & "|" & (location of e) & linefeed
\tend repeat
\treturn out
end tell"""
    for line in sorted(osascript(src).splitlines()):
        if not line.strip():
            continue
        s, e, title, loc = line.split("|", 3)
        sd = dt.datetime.strptime(s, "%Y-%m-%d %H:%M")
        ed = dt.datetime.strptime(e, "%Y-%m-%d %H:%M")
        print(f"{sd:%Y-%m-%d %H:%M} ~ {ed:%m-%d %H:%M}  {title}  @{loc}")
    return 0


def cmd_add(a):
    events = [parse_event(e, a.calendar) for e in json.load(open(a.file))]
    if a.dry_run:
        for e in events:
            print(f"[dry] {e['calendar']} | {e['start']:%Y-%m-%d %H:%M}-{e['end']:%H:%M} | {e['title']} | @{e['location']}")
        print(f"共 {len(events)} 条，未执行。去掉 --dry-run 正式写入。")
        return 0

    blocks = []
    for e in events:
        lo = e["start"] - dt.timedelta(minutes=1)
        hi = e["start"] + dt.timedelta(minutes=1)
        props = (f'{{summary:"{esc(e["title"])}", start date:{mkdate_expr(e["start"])}, '
                 f'end date:{mkdate_expr(e["end"])}')
        props += f', location:"{esc(e["location"])}"' if e["location"] else ""
        props += f', description:"{esc(e["notes"])}"' if e["notes"] else ""
        props += "}"
        blocks.append(f"""
\tset dup to count of (events whose summary is "{esc(e['title'])}" and start date ≥ {mkdate_expr(lo)} and start date ≤ {mkdate_expr(hi)})
\tif dup > 0 then
\t\tset res to res & "SKIP|{esc(e['title'])}|" & linefeed
\telse
\t\ttry
\t\t\tmake new event at end of events with properties {props}
\t\t\tset res to res & "OK|{esc(e['title'])}|" & linefeed
\t\ton error errMsg
\t\t\tset res to res & "ERR|{esc(e['title'])}|" & errMsg & linefeed
\t\tend try
\tend if""")
    src = f"""{AS_HELP}
tell application "Calendar"
\tset res to ""
\ttell calendar "{esc(a.calendar)}"{"".join(blocks)}
\tend tell
\treturn res
end tell"""
    out = osascript(src, timeout=900)
    ok = skip = err = 0
    for line in out.splitlines():
        if line.startswith("OK"):
            ok += 1
        elif line.startswith("SKIP"):
            skip += 1
            print(f"跳过(已存在): {line.split('|')[1]}")
        elif line.startswith("ERR"):
            err += 1
            print(f"失败: {line}")
    print(f"\nRESULT: created={ok} skipped={skip} failed={err} total={len(events)}")
    if err:
        print("注意：失败的事件可修正后重跑——已成功的会被 SKIP，不会重复。")
        return 1
    return 0


def cmd_conflicts(a):
    events = [parse_event(e, a.calendar) for e in json.load(open(a.file))]
    cals = [c.strip() for c in a.calendars.split(",") if c.strip()]
    found = 0
    for e in events:
        for cal in cals:
            src = f"""{AS_HELP}
tell application "Calendar"
\tset out to ""
\tset evs to (every event of calendar "{esc(cal)}" whose start date < {mkdate_expr(e['end'])} and end date > {mkdate_expr(e['start'])})
\trepeat with x in evs
\t\tset out to out & summary of x & "|" & my iso(start date of x) & "|" & my iso(end date of x) & linefeed
\tend repeat
\treturn out
end tell"""
            for line in osascript(src).splitlines():
                if not line.strip():
                    continue
                title, s, en = line.rsplit("|", 2)
                sd = dt.datetime.strptime(s, "%Y-%m-%d %H:%M")
                ed = dt.datetime.strptime(en, "%Y-%m-%d %H:%M")
                print(f"冲突: {e['start']:%m-%d %H:%M} [{e['title']}] ↔ [{title}] {sd:%H:%M}-{ed:%H:%M} @{cal}")
                found += 1
    print(f"\nRESULT: conflicts={found}")
    return 0


def cmd_delete(a):
    lo = dt.datetime.strptime(a.from_date, "%Y-%m-%d")
    hi = dt.datetime.strptime(a.to_date, "%Y-%m-%d").replace(hour=23, minute=59)
    src = f"""{AS_HELP}
tell application "Calendar"
\tset n to 0
\ttell calendar "{esc(a.calendar)}"
\t\tset victims to (every event whose summary is "{esc(a.title)}" and start date ≥ {mkdate_expr(lo)} and start date ≤ {mkdate_expr(hi)})
\t\tif {"true" if a.yes else "false"} then
\t\t\trepeat with x in victims
\t\t\t\tdelete x
\t\t\t\tset n to n + 1
\t\t\tend repeat
\t\telse
\t\t\tset n to count of victims
\t\tend if
\tend tell
\treturn n
end tell"""
    n = osascript(src)
    if a.yes:
        print(f"已删除 {n} 条「{a.title}」")
    else:
        print(f"匹配到 {n} 条「{a.title}」，未删除。确认后加 --yes 执行。")
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    cal_p = sub.add_parser("calendars", help="列出所有日历名")
    cal_p.set_defaults(func=cmd_calendars)

    q = sub.add_parser("list", help="列出某日历某时间段日程")
    q.add_argument("--calendar", required=True)
    q.add_argument("--from", dest="from_date", required=True)
    q.add_argument("--to", dest="to_date", required=True)
    q.add_argument("--title", help="按标题包含过滤")
    q.set_defaults(func=cmd_list)

    w = sub.add_parser("add", help="批量写入（自动去重，单条失败不影响其余）")
    w.add_argument("--file", required=True, help="事件 JSON 文件")
    w.add_argument("--calendar", help="默认日历名（事件里可单独覆盖）")
    w.add_argument("--dry-run", action="store_true")
    w.set_defaults(func=cmd_add)

    c = sub.add_parser("conflicts", help="检查事件与现有日程的时间冲突")
    c.add_argument("--file", required=True)
    c.add_argument("--calendar", help="事件文件未写 calendar 时的默认值")
    c.add_argument("--calendars", default="专业课,公共课",
                   help="在这些日历中查冲突，逗号分隔，默认 专业课,公共课")
    c.set_defaults(func=cmd_conflicts)

    d = sub.add_parser("delete", help="按标题+时间段删除（默认只预览，加 --yes 执行）")
    d.add_argument("--calendar", required=True)
    d.add_argument("--title", required=True)
    d.add_argument("--from", dest="from_date", required=True)
    d.add_argument("--to", dest="to_date", required=True)
    d.add_argument("--yes", action="store_true")
    d.set_defaults(func=cmd_delete)

    a = p.parse_args()
    try:
        sys.exit(a.func(a))
    except RuntimeError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
