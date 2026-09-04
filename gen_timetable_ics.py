# -*- coding: utf-8 -*-
"""
北交大 2026-2027-1 学期课表 → ICS 生成器
用法: python gen_timetable_ics.py [--start 2026-09-07] [--weeks 16]
默认: 第1周周一 = 2026-08-31, 共16周 (实际学期用 --start 指定)
生成: 脚本同目录 bjtu-timetable-2026-2027-1.ics
"""
import argparse
import hashlib
from datetime import date, datetime, timedelta
from pathlib import Path

# ---------------- 参数 ----------------
DEFAULT_START = date(2026, 8, 31)   # 第1周周一(如校历不同改这里或 --start)
TOTAL_WEEKS = 16

# 节次时间表: 节次 -> (开始时分, 结束时分)
PERIODS = {
    1: (8, 0, 9, 50),      # 第1节 08:00-09:50
    2: (10, 10, 12, 0),    # 第2节 10:10-12:00
    3: (12, 10, 14, 0),    # 第3节 12:10-14:00
    4: (14, 10, 16, 0),    # 第4节 14:10-16:00
    5: (16, 20, 18, 10),   # 第5节 16:20-18:10
    6: (19, 0, 20, 50),    # 第6节 19:00-20:50
    7: (21, 0, 21, 50),    # 第7节 21:00-21:50
}

# ---------------- 课程数据 ----------------
# slot = (weekday 1=周一..7=周日, period, start_week, end_week, interval)
COURSES = [
    {"code": "M304085B", "name": "铁路货运组织与技术", "teacher": "韩梅",
     "slots": [(1, 1, 1, 16, 1), (3, 4, 1, 16, 1)]},
    {"code": "M304260B", "name": "列车牵引计算", "teacher": "唐金金",
     "slots": [(1, 2, 1, 12, 1), (4, 1, 1, 12, 1)]},
    {"code": "M308007B", "name": "数理统计", "teacher": "薛晓峰",
     "slots": [(1, 4, 1, 16, 1), (3, 1, 1, 16, 1)]},
    {"code": "M408003B", "name": "图像处理基础", "teacher": "王晓静",
     "slots": [(1, 5, 1, 8, 1), (5, 5, 1, 8, 1)]},
    {"code": "A121083B", "name": "射箭", "teacher": "鲁大兴",
     "slots": [(2, 1, 1, 16, 1)]},
    {"code": "M304095B", "name": "运输组织学", "teacher": "魏玉光",
     "slots": [(2, 2, 1, 16, 1), (4, 2, 1, 15, 2)]},   # 周四仅奇数周1,3..15
    {"code": "M404131B", "name": "集装箱运输与多式联运B", "teacher": "王力",
     "slots": [(2, 4, 1, 8, 1), (5, 2, 1, 8, 1)]},
    {"code": "M304343B", "name": "铁路客运组织", "teacher": "张琦",
     "slots": [(2, 5, 1, 12, 1), (5, 1, 1, 12, 1)]},
    {"code": "C104297B", "name": "人工智能基础及应用（B）", "teacher": "董宏辉",
     "slots": [(3, 2, 9, 16, 1), (5, 4, 9, 16, 1)]},   # 仅9-16周
    {"code": "A011009B", "name": "大学美育实践", "teacher": "杨梦婉",
     "slots": [(6, 1, 2, 9, 1), (6, 2, 2, 9, 1)]},     # 周六1、2节连上
    {"code": "P404190B", "name": "交通运输专业复杂工程问题研究系列讲座", "teacher": "黎浩东",
     "slots": [(6, 3, 1, 16, 1)]},
]
# 地点(静态映射, 按课程+节次)
LOCATIONS = {
    ("铁路货运组织与技术", 1): "海淀西校区 逸夫教学楼 YF106",
    ("铁路货运组织与技术", 4): "海淀西校区 逸夫教学楼 YF106",
    ("列车牵引计算", 1): "海淀西校区 逸夫教学楼 YF205",
    ("列车牵引计算", 2): "海淀西校区 逸夫教学楼 YF205",
    ("数理统计", 1): "海淀西校区 思源楼 SY106",
    ("数理统计", 4): "海淀西校区 思源楼 SY106",
    ("图像处理基础", 5): "海淀西校区 思源楼 SY201",
    ("射箭", 1): "海淀西校区 综合体育馆 体育教室1",
    ("运输组织学", 2): "海淀西校区 思源东楼 SD103",
    ("集装箱运输与多式联运B", 2): "海淀西校区 第八教学楼 8207",
    ("集装箱运输与多式联运B", 4): "海淀西校区 第八教学楼 8207",
    ("铁路客运组织", 1): "海淀西校区 思源楼 SY203",
    ("铁路客运组织", 5): "海淀西校区 思源楼 SY203",
    ("人工智能基础及应用（B）", 2): "海淀西校区 逸夫教学楼 YF611",
    ("人工智能基础及应用（B）", 4): "海淀西校区 逸夫教学楼 YF611",
    ("大学美育实践", 1): "海淀西校区 地点见本科生院网站或学院通知",
    ("大学美育实践", 2): "海淀西校区 地点见本科生院网站或学院通知",
    ("交通运输专业复杂工程问题研究系列讲座", 3): "海淀西校区 地点见本科生院网站或学院通知",
}

# ---------------- ICS 工具 ----------------
def esc(s):
    """ICS 文本转义"""
    return (s.replace("\\", "\\\\").replace(";", "\\;")
             .replace(",", "\\,").replace("\n", "\\n"))

def to_utc(dt_local):
    """北京(UTC+8) -> UTC 的 naive datetime"""
    return dt_local - timedelta(hours=8)

def fmt_utc(dt):
    return dt.strftime("%Y%m%dT%H%M%SZ")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=str, default=DEFAULT_START.isoformat(), help="第1周周一日期 YYYY-MM-DD")
    ap.add_argument("--weeks", type=int, default=TOTAL_WEEKS)
    args = ap.parse_args()
    start_monday = date.fromisoformat(args.start)
    if start_monday.weekday() != 0:
        raise SystemExit(f"起始日必须是周一: {args.start} 是星期{start_monday.isoformat()}")

    events = []
    uid_seed = 1
    for c in COURSES:
        for (wd, period, sw, ew, iv) in c["slots"]:
            sh, sm, eh, em = PERIODS[period]
            count = (ew - sw) // iv + 1
            # 第一次上课的本地时间
            first_day = start_monday + timedelta(days=(sw - 1) * 7 + (wd - 1))
            start_dt = datetime(first_day.year, first_day.month, first_day.day, sh, sm)
            end_dt = datetime(first_day.year, first_day.month, first_day.day, eh, em)
            # 间隔处理: RRULE INTERVAL
            interval_txt = ""
            if iv == 2:
                interval_txt = ";INTERVAL=2"
            week_note = f"第{sw}-{ew}周" + ("(隔周)" if iv == 2 else "")
            desc = f"课程号:{c['code']} 教师:{c['teacher']} 周次:{week_note}"
            loc = LOCATIONS.get((c["name"], period), "海淀西校区")
            uid = f"bjtu-2026-2027-1-{uid_seed:03d}"
            uid_seed += 1
            summary = c["name"]
            lines = [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{datetime.now().strftime('%Y%m%dT%H%M%SZ')}",
                f"DTSTART:{fmt_utc(to_utc(start_dt))}",
                f"DTEND:{fmt_utc(to_utc(end_dt))}",
                f"SUMMARY:{esc(summary)}",
                f"DESCRIPTION:{esc(desc)}",
                f"LOCATION:{esc(loc)}",
                f"RRULE:FREQ=WEEKLY;COUNT={count}{interval_txt}",
                "END:VEVENT",
            ]
            events.append("\r\n".join(lines))

    ics_body = (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//Molise//BJTU Timetable 2026-2027-1//CN\r\n"
        "CALSCALE:GREGORIAN\r\n"
        "METHOD:PUBLISH\r\n"
        "X-WR-CALNAME:北交大课表 2026-2027-1\r\n"
        "X-WR-TIMEZONE:Asia/Shanghai\r\n"
        + "\r\n".join(events) + "\r\n"
        "END:VCALENDAR\r\n"
    )

    out = Path(__file__).resolve().parent / "bjtu-timetable-2026-2027-1.ics"
    with open(out, "w", encoding="utf-8", newline="") as f:
        f.write(ics_body)
    print(f"OK 生成 {out}")
    print(f"事件数: {ics_body.count('BEGIN:VEVENT')} 个 (规则展开前的模板事件)")
    print(f"首个DTSTART: {events[0].splitlines()[3]}")
    # 抽查最后一个事件的起始
    print(f"学期跨度: {start_monday} ~ {start_monday + timedelta(days=args.weeks * 7 - 1)}")

if __name__ == "__main__":
    main()
