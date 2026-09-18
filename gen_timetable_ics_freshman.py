# -*- coding: utf-8 -*-
"""
北交大 2026-2027-1 学期课表 → ICS 生成器
用法: python gen_timetable_ics_freshman.py [--start 2026-09-07] [--weeks 16]
生成: 脚本同目录 bjtu-timetable-2026-2027-1-freshman.ics

数据来源: 2026-09-18 用户提供的教学支撑平台「选课课表」截图(教务原文)
课表总数: 本学期课程; 含隔周课(Python基础 双周)与限定期次课
"""
import argparse
from datetime import date, datetime, timedelta
from pathlib import Path

# ---------------- 参数 ----------------
DEFAULT_START = date(2026, 9, 7)    # 第1周周一(2026-2027-1 用户确认)
TOTAL_WEEKS = 16

# 节次时间表: 节次 -> (开始时分, 结束时分)
PERIODS = {
    1: (8, 0, 9, 50),
    2: (10, 10, 12, 0),
    3: (12, 10, 14, 0),
    4: (14, 10, 16, 0),
    5: (16, 20, 18, 10),
    6: (19, 0, 20, 50),
    7: (21, 0, 21, 50),
}

def daterange(a, b):
    cur, out = a, []
    while cur <= b:
        out.append(cur)
        cur += timedelta(days=1)
    return out

NO_CLASS_DATES = set(
    daterange(date(2026, 9, 25), date(2026, 10, 7)) +   # 中秋+国庆连放 9/25-10/7
    [date(2026, 9, 9), date(2026, 9, 10)]               # 校庆 9/9-9/10
)
EXTRA_CLASSES = {}

# ---------------- 课程数据 ----------------
# 数据来源: 2026-09-18 用户提供的四张连续滚动截图 + 用户逐条确认修正
#   ★ 修正1: 原误读的"周四第5/6/7节"实为"周五第5/6/7节"(少切一列)
#   ★ 修正2: 专业导论周六 4/5/6 节各"1-2周 + 5-6周"两段合并为一条(周次区间跨度大)
# slot = (weekday 1=周一..7=周日, period, start_week, end_week, interval)
# interval=1 每周; interval=2 隔周(从 start_week 起每隔一周)
COURSES = [
    {"code": "C108001B", "name": "微积分(B)I", "teacher": "余爱梅",
     "slots": [(1, 1, 1, 16, 1), (3, 2, 1, 16, 1), (5, 1, 1, 16, 1)]},
    {"code": "C108004B", "name": "几何与代数(B)", "teacher": "王晓静",
     "slots": [(2, 1, 1, 16, 1), (4, 2, 1, 12, 1)]},
    {"code": "A121001B", "name": "体育I", "teacher": "高峻",
     "slots": [(4, 1, 1, 16, 1)]},
    {"code": "C102017B", "name": "大学计算机", "teacher": "周周,李宜芳",
     "slots": [(2, 2, 9, 16, 1)]},
    {"code": "A123005B", "name": "公民素养与全面发展", "teacher": "唐薇",
     "slots": [(5, 3, 1, 16, 1)]},
    {"code": "A019001B", "name": "国家安全教育",
     "teacher": "黎姝红,刘吉强,杜晔,闫长丽,李静,安志强,李营辉,刘娟娟",
     "slots": [(6, 3, 9, 16, 1)]},
    {"code": "M203002B", "name": "管理学原理", "teacher": "曾德麟",
     "slots": [(1, 4, 1, 12, 1), (3, 5, 1, 12, 1)]},
    {"code": "C112003B", "name": "中级综合英语", "teacher": "李淞",
     "slots": [(2, 4, 1, 12, 1), (5, 4, 1, 12, 1)]},
    {"code": "M203012B", "name": "Python基础及应用", "teacher": "陈学东",
     "slots": [(3, 4, 1, 16, 1), (5, 5, 2, 16, 2)]},   # 周五第5节 双周(2,4,...,16周)
    {"code": "M103001B", "name": "专业导论",
     "teacher": "周耀东,张姗姗,周建勤,任旭,刘颖琦,穆文歆,赵晓军,肖迪",
     # 周六 4/5/6 节, 1-2周 与 5-6周 两段合并(区间跨度大, 按用户确认合一)
     "slots": [(6, 4, 1, 6, 1), (6, 5, 1, 6, 1), (6, 6, 1, 6, 1)]},
    {"code": "A022014B", "name": "大学生心理健康", "teacher": "苗永清",
     "slots": [(1, 5, 9, 16, 1)]},
    {"code": "A103982B", "name": "商业礼仪与沟通", "teacher": "王曦若",
     "slots": [(2, 5, 1, 8, 1)]},
    {"code": "A032001B", "name": "高铁纵横", "teacher": "贺振欢",
     "slots": [(2, 6, 5, 12, 1)]},
    {"code": "A109019B", "name": "习近平新时代中国特色社会主义思想概论",
     "teacher": "王楠,尚娜娜", "slots": [(5, 6, 1, 16, 1), (5, 7, 1, 16, 1)]},
]

# 地点: (课程名, 节次) -> 教室
LOCATIONS = {
    ("微积分(B)I", 1): "海淀西校区 思源楼 SY108",
    ("微积分(B)I", 2): "海淀西校区 思源楼 SY108",
    ("几何与代数(B)", 1): "海淀东校区 东区一教 DQ203",
    ("几何与代数(B)", 2): "海淀东校区 东区一教 DQ203",
    ("体育I", 1): "海淀西校区 主校区体育场",
    ("大学计算机", 2): "海淀西校区 地点见本科生院网站或学院通知",
    ("公民素养与全面发展", 3): "海淀西校区 地点见本科生院网站或学院通知",
    ("国家安全教育", 3): "海淀西校区 网络课",
    ("管理学原理", 4): "海淀东校区 东区一教 DQ412",
    ("管理学原理", 5): "海淀东校区 东区一教 DQ412",
    ("中级综合英语", 4): "海淀东校区 东区一教 DQ206",
    ("Python基础及应用", 5): "海淀东校区 东区一教 DQ410",
    ("专业导论", 4): "海淀西校区 第九教学楼 中心报告厅",
    ("专业导论", 5): "海淀西校区 第九教学楼 中心报告厅",
    ("专业导论", 6): "海淀西校区 第九教学楼 中心报告厅",
    ("大学生心理健康", 5): "海淀东校区 东区一教 DQ313",
    ("商业礼仪与沟通", 5): "海淀东校区 东区一教 DQ105",
    ("高铁纵横", 6): "海淀西校区 逸夫教学楼 YF505",
    ("习近平新时代中国特色社会主义思想概论", 6): "海淀西校区 思源楼 SY109",
    ("习近平新时代中国特色社会主义思想概论", 7): "海淀西校区 思源楼 SY109",
}

# ---------------- ICS 工具 ----------------
def esc(s):
    return (s.replace("\\", "\\\\").replace(";", "\\;")
             .replace(",", "\\,").replace("\n", "\\n"))

def to_utc(dt_local):
    return dt_local - timedelta(hours=8)

def fmt_utc(dt):
    return dt.strftime("%Y%m%dT%H%M%SZ")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=str, default=DEFAULT_START.isoformat())
    ap.add_argument("--weeks", type=int, default=TOTAL_WEEKS)
    args = ap.parse_args()
    start_monday = date.fromisoformat(args.start)
    if start_monday.weekday() != 0:
        raise SystemExit(f"起始日必须是周一: {args.start}")

    events = []
    uid_seed = 1
    total_exdates = 0
    for c in COURSES:
        for (wd, period, sw, ew, iv) in c["slots"]:
            sh, sm, eh, em = PERIODS[period]
            count = (ew - sw) // iv + 1
            first_day = start_monday + timedelta(days=(sw - 1) * 7 + (wd - 1))
            exdates = []
            for i in range(count):
                inst = first_day + timedelta(days=i * 7 * iv)
                if inst in NO_CLASS_DATES:
                    exdates.append(fmt_utc(to_utc(datetime(inst.year, inst.month, inst.day, sh, sm))))
            interval_txt = ";INTERVAL=2" if iv == 2 else ""
            week_note = f"第{sw}-{ew}周" + ("(隔周)" if iv == 2 else "")
            desc = f"课程号:{c['code']} 教师:{c['teacher']} 周次:{week_note}"
            loc = LOCATIONS.get((c["name"], period), "海淀西校区")
            uid = f"bjtu-2026-2027-1-fresh-{uid_seed:03d}"
            uid_seed += 1
            lines = [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{datetime.now().strftime('%Y%m%dT%H%M%SZ')}",
                f"DTSTART:{fmt_utc(to_utc(datetime(first_day.year, first_day.month, first_day.day, sh, sm)))}",
                f"DTEND:{fmt_utc(to_utc(datetime(first_day.year, first_day.month, first_day.day, eh, em)))}",
                f"SUMMARY:{esc(c['name'])}",
                f"DESCRIPTION:{esc(desc)}",
                f"LOCATION:{esc(loc)}",
                f"RRULE:FREQ=WEEKLY;COUNT={count}{interval_txt}",
            ]
            if exdates:
                lines.append("EXDATE:" + ",".join(exdates))
                total_exdates += len(exdates)
            lines.append("END:VEVENT")
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
    out = Path(__file__).resolve().parent / "bjtu-timetable-2026-2027-1-freshman.ics"
    with open(out, "w", encoding="utf-8", newline="") as f:
        f.write(ics_body)
    print(f"OK 生成 {out}")
    print(f"VEVENT: {ics_body.count('BEGIN:VEVENT')} 个, EXDATE: {total_exdates} 个")
    print(f"学期跨度: {start_monday} ~ {start_monday + timedelta(days=args.weeks * 7 - 1)}")

if __name__ == "__main__":
    main()
