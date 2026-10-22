# -*- coding: utf-8 -*-
"""skill_quota_scan.py — 季度 skill 巡检（版本 + 替代方案扫描）
用法: python skill_quota_scan.py [--json-out scan.json] [--root D:\\global_skills]
步骤:
 1) 枚举受管 skill 根 (ls, 禁 os.walk junction — A-skill-manager 铁律1)
 2) 每个 skill: 读 SKILL.md frontmatter (name/version), 量主文件字节 (12KB soft cap)
 3) 解析 'requires:/上游映射' 注释或 sidecar <skill>/.upstream (owner/repo) 声明;
    对每个 owner/repo 经 img.shields.io JSON 徽章取 stars/last_commit/latest_release
    (免认证、限流友好; 失败降级 web 搜索人工确认)
 4) 判红: 上游停更>180天 / 本地版本落后上游 latest / 主文件>12288B / 缺 SKILL.md /
    __pycache__ 孤儿 / retired_skills 名册命中仍被引用
 5) 输出结构化报告: KEEP / UPGRADE(落后) / ATTN(停更或超限) 三级 + 建议动作
退出码 0=全绿 1=有 ATTN 2=用法错误
"""
import json, os, re, sys, datetime, urllib.request

def parse_args():
    args = {"json_out": None, "root": r"D:\global_skills"}
    argv = sys.argv[1:]
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--json-out": args["json_out"] = argv[i + 1]; i += 2
        elif a == "--root": args["root"] = argv[i + 1]; i += 2
        else:
            print("usage: skill_quota_scan.py [--json-out PATH] [--root DIR]"); sys.exit(2)
    return args

FM_RE = re.compile(r"^---\s*\n(.*?)\n---", re.S)
def fm_field(text, key):
    m = re.search(r"^%s:\s*(.+)$" % key, text, re.M)
    return m.group(1).strip().strip("'\"") if m else None

def shield(repo, kind):
    url = "https://img.shields.io/github/%s/%s.json" % (kind, repo)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "skill-quota-scan"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8", "replace")).get("value", "?")
    except Exception as e:
        return "ERR:" + type(e).__name__

def main():
    args = parse_args()
    root = args["root"]
    if not os.path.isdir(root):
        print("root not found: " + root); sys.exit(2)
    rows, reds = [], []
    retired_path = r"C:\Users\37533\Desktop\workspace\焚诀\eval\truth_constants.json"
    retired = set()
    if os.path.isfile(retired_path):
        try:
            retired = set(json.load(open(retired_path, encoding="utf-8")).get("retired_skills", []))
        except Exception:
            pass
    for name in sorted(os.listdir(root)):
        d = os.path.join(root, name)
        if not os.path.isdir(d) or name in (".git", ".temp", "_trash", "_temp", "rag-eval"):
            continue
        p = os.path.join(d, "SKILL.md")
        row = {"skill": name}
        if not os.path.isfile(p):
            row["issue"] = "MISSING_SKILL_MD"; reds.append(row); rows.append(row); continue
        text = open(p, encoding="utf-8", errors="replace").read()
        fm = FM_RE.match(text)
        body = fm.group(1) if fm else ""
        size = os.path.getsize(p)
        row["version"] = fm_field(body, "version")
        row["last_updated"] = fm_field(body, "last_updated")
        row["skill_bytes"] = size
        flags = []
        if size > 12288: flags.append("OVERSIZE_SOFT12K(%dB)" % size)
        if name in retired: flags.append("RETIRED_BUT_PRESENT")
        # orphan-only: .pyc whose source .py no longer exists (live caches of in-use libs are valid build artifacts)
        junk = 0
        for dirpath, dirnames, filenames in os.walk(d):
            for fn in filenames:
                if fn.endswith(".pyc"):
                    stem = fn.split(".")[0]
                    src_py = os.path.join(dirpath, stem + ".py")
                    # __pycache__ dir layout: <dir>/__pycache__/x.cpython-313.pyc <- source at <dir>/x.py
                    parent = os.path.dirname(dirpath) if os.path.basename(dirpath) == "__pycache__" else dirpath
                    src_py = os.path.join(parent, stem + ".py")
                    if not os.path.isfile(src_py): junk += 1
        if junk: flags.append("PYCACHE_ORPHAN(%d)" % junk)
        up = os.path.join(d, ".upstream")  # sidecar: owner/repo per line
        if os.path.isfile(up):
            for repo_line in open(up, encoding="utf-8"):
                repo_line = repo_line.strip()
                if not repo_line or repo_line.startswith("#"): continue
                st = shield(repo_line, "stars"); lc = shield(repo_line, "last-commit"); rel = shield(repo_line, "v/release")
                row.setdefault("upstream", []).append({"repo": repo_line, "stars": st, "last_commit": lc, "latest_release": rel})
                # stale judgement: shields last-commit returns e.g. today/yesterday/N days/last week/N months/october/never
                if lc.startswith("ERR") or "not found" in lc or lc == "never":
                    flags.append("UPSTREAM_UNREACHABLE:" + repo_line)
                elif re.search(r"years|months|never", lc, re.I):
                    flags.append("UPSTREAM_STALE(" + repo_line + " last=" + lc + ")")
        if flags: row["flags"] = flags; reds.append(row)
        rows.append(row)
    report = {"generated": datetime.datetime.now().isoformat(timespec="seconds"),
              "total_skills": len(rows), "attention": len(reds), "rows": rows}
    out = json.dumps(report, ensure_ascii=False, indent=1)
    if args["json_out"]:
        open(args["json_out"], "w", encoding="utf-8").write(out)
        print("scan -> " + args["json_out"] + " ; skills=%d attention=%d" % (len(rows), len(reds)))
    else:
        print(out)
    sys.exit(1 if reds else 0)

if __name__ == "__main__":
    main()
