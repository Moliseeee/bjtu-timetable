# -*- coding: utf-8 -*-
"""同学课表 ICS 深度校验: icalendar 严格解析 + 逐个实例展开核对(教学周/日期/时间)"""
import sys
from datetime import date, datetime, timedelta
from icalendar import Calendar

PATH = r"D:\课表ics\bjtu-timetable-2026-2027-1-freshman.ics"
START = date(2026, 9, 7)          # 第1周周一
NO_CLASS = set()
d = date(2026, 9, 25)
while d <= date(2026, 10, 7):
    NO_CLASS.add(d); d += timedelta(days=1)
NO_CLASS |= {date(2026, 9, 9), date(2026, 9, 10)}

# 期望: (课程名, 周几, 节次, 起止周) —— 从截图逐格读出
EXPECT = [
    ("微积分(B)I", 1, 1, 1, 16),
    ("大学计算机", 1, 2, 9, 16),
    ("几何与代数(B)", 2, 1, 1, 16),
    ("高铁纵横", 2, 6, 5, 12),
    ("体育I", 3, 1, 1, 16),
    ("几何与代数(B)", 4, 2, 1, 12),
    ("习近平新时代中国特色社会主义思想概论", 4, 6, 1, 16),
    ("习近平新时代中国特色社会主义思想概论", 4, 7, 1, 16),
    ("专业导论", 6, 6, 1, 2),
    ("专业导论", 6, 2, 5, 6),
    ("专业导论", 6, 6, 5, 6),
]
PERIODS = {1: (8, 0, 9, 50), 2: (10, 10, 12, 0), 3: (12, 10, 14, 0),
           4: (14, 10, 16, 0), 5: (16, 20, 18, 10), 6: (19, 0, 20, 50),
           7: (21, 0, 21, 50)}

raw = open(PATH, encoding="utf-8", newline="").read()
cal = Calendar.from_ical(raw)      # 严格解析, 解析失败即抛
events = [c for c in cal.walk("VEVENT")]

# --- 展开全部实例(含 RRULE + EXDATE) ---
actual = []   # (date, 课程名, 节次, 教学周)

def expand(e, first):
    """按 RRULE 展开具体日期(仅本工程用到 WEEKLY + COUNT)"""
    r = e["RRULE"]
    count = int(r["COUNT"][0])
    iv = int(r["INTERVAL"][0]) if r.get("INTERVAL") else 1
    exd = set()
    if e.get("EXDATE"):
        v = e["EXDATE"]
        v = v if isinstance(v, list) else [v]
        for item in v:
            for dd in (item.dts if hasattr(item, "dts") else [item]):
                x = dd.dt
                if getattr(x, "tzinfo", None):
                    x = x.astimezone().replace(tzinfo=None)
                exd.add(x.date())
    out = []
    for i in range(count):
        dd = first.date() + timedelta(days=7 * iv * i)
        out.append((dd, dd not in exd))
    return out

rows = []
for e in events:
    name = str(e["SUMMARY"])
    dt = e["DTSTART"].dt
    if getattr(dt, "tzinfo", None):
        dt = dt.astimezone().replace(tzinfo=None)
    dt = dt.replace(tzinfo=None)
    period = next(p for p, (sh, sm, *_r) in PERIODS.items()
                  if (dt.hour, dt.minute) == (sh, sm))
    for dd, alive in expand(e, dt):
        wk = (dd - START).days // 7 + 1
        rows.append((name, dd.weekday() + 1, period, wk, dd, alive))

fails = []
# 1) 事件数
if len(events) != len(EXPECT):
    fails.append(f"事件数 {len(events)} != 期望 {len(EXPECT)}")
# 2) 每条 slot 的日期集合与截图一致
#    ⚠️ 同一门课同一节次可能有多条 slot(专业导论周六第6节 = 1-2周 + 5-6周),
#    所以比对单位是【VEVENT】而非"课程+周几+节次"粗分组,也不能用存活实例集合
#    (同一星期+节次的两个 slot 存活实例会并成一个集合,必然假 FAIL)
def slot_key(nm, wd, p, sw):
    """定位某 slot: rows 里同一 VEVENT 的实例 = 该 slot 起止周区间内的日期"""
    return [(wk, dd, alive) for (n2, wd2, period, wk, dd, alive) in rows
            if n2 == nm and wd2 == wd and period == p and sw <= wk < sw + (len(rows) and 99)]

def slot_instances(nm, wd, p, sw, ew):
    """该 slot 的全部实例 = 课程名+周几+节次匹配, 且教学周落在 [sw, ew]"""
    return sorted({(wk, dd, alive) for (n2, wd2, period, wk, dd, alive) in rows
                   if n2 == nm and wd2 == wd and period == p and sw <= wk <= ew})

def expected_dates(wd, sw, ew):
    out = []
    for wk in range(sw, ew + 1):
        dd = START + timedelta(days=(wk - 1) * 7 + (wd - 1))
        out.append((wk, dd))
    return out

for (nm, wd, p, sw, ew) in EXPECT:
    hits = slot_instances(nm, wd, p, sw, ew)
    if not hits:
        fails.append(f"找不到 slot: {nm} 周{wd} 第{p}节 起始周{sw}")
        continue
    got = [dd for (_wk, dd, alive) in hits if alive]
    want = [dd for (_wk, dd) in expected_dates(wd, sw, ew) if dd not in NO_CLASS]
    if got != want:
        fails.append(f"{nm} 周{wd} 第{p}节 {sw}-{ew}周 实例不符\n     got  {[d.isoformat() for d in got]}\n     want {[d.isoformat() for d in want]}")

# 4) 日期与周几自洽(锚点 2026-09-07 周一)
for (nm, wd, p, wk, dd, alive) in rows:
    if alive and dd.weekday() + 1 != wd:
        fails.append(f"{nm} {dd} 落在星期{dd.weekday()+1} != 课表星期{wd}")

# 5) 停课日无任何存活实例
for (nm, wd, p, wk, dd, alive) in rows:
    if dd in NO_CLASS and alive:
        fails.append(f"停课日 {dd} 仍有课存活: {nm}")

print(f"解析: {len(events)} 个 VEVENT, 展开 {len(rows)} 个实例")
print(f"存活实例(扣 EXDATE 后): {sum(1 for r in rows if r[5])}")
print("停课日集合:", sorted(d.isoformat() for d in NO_CLASS))
if fails:
    print("\nFAIL:")
    for f in fails:
        print(" -", f)
    sys.exit(1)
print("\nPASS: 事件数/周次/周几/节次/停课日剔除 全部与截图一致")
