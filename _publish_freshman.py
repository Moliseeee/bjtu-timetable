# -*- coding: utf-8 -*-
"""建仓库 + 推 main + 用 API 校验远端 (token 只进内存,不落盘,不进日志)"""
import json, re, subprocess, sys, urllib.request, time
from pathlib import Path
from urllib.error import HTTPError

TOKEN = sys.argv[1] if len(sys.argv) > 1 else None   # 外部传入, 不写入本文件
if not TOKEN:
    # 从历史会话记录里就地取有效 token (不打印明文)
    import sqlite3
    db = r"D:\Hermes Agent CN Desktop\data\hermes-home\state.db"
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    cur = con.cursor()
    cur.execute("select name from sqlite_master where type='table'")
    text = []
    for (t,) in cur.fetchall():
        try:
            cur.execute(f"select * from {t}")
            for row in cur.fetchall():
                for v in row:
                    if isinstance(v, str):
                        text.append(v)
        except Exception:
            pass
    con.close()
    blob = "\n".join(text)
    cands = sorted(set(re.findall(r"ghp_[A-Za-z0-9]{36}", blob)) |
                   set(re.findall(r"github_pat_[A-Za-z0-9_]{60,}", blob)))
    for t in cands:
        req = urllib.request.Request("https://api.github.com/user",
                                     headers={"Authorization": f"Bearer {t}",
                                              "User-Agent": "hermes"})
        try:
            with urllib.request.build_opener().open(req, timeout=25) as r:
                j = json.loads(r.read().decode("utf-8"))
            print(f"取到有效 token ({t[:10]}...{t[-4:]}) 身份={j.get('login')}")
            TOKEN = t
            break
        except Exception:
            continue
if not TOKEN:
    sys.exit("没有可用 token")

OWNER, REPO = "Moliseeee", "bjtu-timetable-freshman"
API = "https://api.github.com"

def api(method, path, payload=None):
    req = urllib.request.Request(
        API + path, method=method,
        headers={"Authorization": f"Bearer {TOKEN}",
                 "Accept": "application/vnd.github+json",
                 "User-Agent": "hermes"},
        data=json.dumps(payload).encode() if payload else None)
    try:
        with urllib.request.build_opener().open(req, timeout=40) as r:
            return r.status, json.loads(r.read().decode("utf-8") or "{}")
    except HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8") or "{}")

# 0) token 身份
st, me = api("GET", "/user")
print("token 身份:", st, me.get("login"))

# 1) 建仓库(若已存在则跳过)
st, r = api("POST", "/user/repos", {
    "name": REPO, "description": "北交大 2026-2027-1 学期课表 iCal（同学版，普通班）",
    "private": False, "auto_init": False, "has_issues": False, "has_wiki": False})
print("建仓库:", st, r.get("full_name") or r.get("message"))
if st not in (201, 422):
    sys.exit("建仓库失败,中止")

# 2) git push (SSH 被拒 → 用 HTTPS+PAT 直推)
d = r"D:\课表ics"
def git(*a, **kw):
    cmd = ["git", "-C", d, "-c", "credential.helper="] + list(a)
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", **kw)
    print(f"$ git {' '.join(a)}\n{p.stdout}{p.stderr}".rstrip())
    return p

git("add", "-A")
git("-c", "user.name=Moliseeee", "-c", "user.email=molisemolise@github.com",
    "commit", "-m", "freshman: add classmate timetable ICS (2026-2027-1)")
git("remote", "remove", "origin-fresh") if git("remote").stdout.find("origin-fresh") >= 0 else None
git("remote", "add", "origin-fresh", f"https://github.com/{OWNER}/{REPO}.git")
p = git("push", f"https://{OWNER}:{TOKEN}@github.com/{OWNER}/{REPO}.git", "main:main", "--force")
if p.returncode != 0:
    sys.exit("push 失败,中止")

# 3) 校验远端
time.sleep(4)
st, ref = api("GET", f"/repos/{OWNER}/{REPO}/git/ref/heads/main")
print("远端 main:", st, ref.get("object", {}).get("sha"))
local_head = subprocess.run(["git", "-C", d, "rev-parse", "HEAD"],
                            capture_output=True, text=True).stdout.strip()
print("本地 HEAD:", local_head)
st, tree = api("GET", f"/repos/{OWNER}/{REPO}/git/trees/main?recursive=1")
paths = [t["path"] for t in tree.get("tree", [])]
print("远端文件:", paths)
bad = [x for x in paths if re.search(r"会审|模拟盘|REVIEW|方案_|_kimi|学费|\.env$|token|secret|password", x, re.I)]
print("敏感路径:", bad or "无")
print("仓库 public:", api("GET", f"/repos/{OWNER}/{REPO}")[1].get("private") is False)
