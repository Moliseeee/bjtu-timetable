# -*- coding: utf-8 -*-
"""临时脚本: 从历史会话记录里找回 GitHub classic PAT (只读, 只打掩码)"""
import re, sqlite3, json, urllib.request, os, sys

HOME = r"D:\Hermes Agent CN Desktop\data\hermes-home"
db = os.path.join(HOME, "state.db")
con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
cur = con.cursor()
cur.execute("select name from sqlite_master where type='table'")
tables = [r[0] for r in cur.fetchall()]
print("tables:", tables)

blob = []
for t in tables:
    try:
        cur.execute(f"select * from {t}")
        cols = [d[0] for d in cur.description]
        for row in cur.fetchall():
            for c, v in zip(cols, row):
                if isinstance(v, str):
                    blob.append(v)
    except Exception as e:
        print("skip", t, e)
text = "\n".join(blob)
print("scanned chars:", len(text))

pats = sorted(set(re.findall(r"ghp_[A-Za-z0-9]{36}", text)) |
              set(re.findall(r"github_pat_[A-Za-z0-9_]{60,}", text)))
print("found tokens:", len(pats))

opener = urllib.request.build_opener()  # 直连
valid = []
for t in pats:
    mask = t[:10] + "..." + t[-4:]
    try:
        req = urllib.request.Request("https://api.github.com/user",
                                     headers={"Authorization": f"Bearer {t}",
                                              "User-Agent": "hermes"})
        with opener.open(req, timeout=25) as r:
            j = json.loads(r.read().decode("utf-8"))
        print(f"{mask} -> 200 login={j.get('login')}")
        valid.append(t)
    except Exception as e:
        code = getattr(e, "code", None)
        print(f"{mask} -> {'HTTP ' + str(code) if code else 'ERR ' + str(e)[:60]}")
try:
    con.close()
except Exception:
    pass
# 结果只落掩码到 stdout, 原文不落盘
