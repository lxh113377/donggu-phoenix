# -*- coding: utf-8 -*-
"""backfill_last_updated.py — Phase 0.3：为缺 last_updated 的 SKILL.md 注入 git 真值日期。
只插字段不动正文；已有该键件跳过；无 git 历史/新件跳过并报告。
用法: python backfill_last_updated.py [--apply]（默认 dry-run）
"""
import os, re, subprocess, sys, json

ROOT = r"D:\global_skills"
APPLY = "--apply" in sys.argv
SKIP_DIRS = {".git", ".temp", "_trash", "_temp", "_bak", "node_modules"}
FM = re.compile(r"^(---\r?\n)(.*?)(\r?\n---)", re.S)
KEY = re.compile(r"^last_updated:\s*(.+)$", re.M)

def git_last_date(rel):
    try:
        out = subprocess.run(["git", "-C", ROOT, "log", "-1", "--format=%cd", "--date=short", "--", rel],
                             capture_output=True, text=True, timeout=30)
        d = out.stdout.strip()
        return d if re.match(r"^\d{4}-\d{2}-\d{2}$", d) else None
    except Exception:
        return None

def main():
    report = {"apply": APPLY, "inserted": [], "skipped_has_key": 0, "skipped_no_date": []}
    for name in sorted(os.listdir(ROOT)):
        d = os.path.join(ROOT, name)
        if not os.path.isdir(d) or name in SKIP_DIRS: continue
        p = os.path.join(d, "SKILL.md")
        if not os.path.isfile(p): continue
        raw = open(p, "rb").read()
        text = raw.decode("utf-8", "replace")
        m = FM.match(text)
        if not m: report["skipped_no_date"].append([name, "no-frontmatter"]); continue
        if KEY.search(m.group(2)): report["skipped_has_key"] += 1; continue
        rel = name.replace("\\", "/")
        date = git_last_date(rel)
        if not date: report["skipped_no_date"].append([name, "no-git-date"]); continue
        # insert after version: line if present, else at end of frontmatter block
        body = m.group(2)
        if re.search(r"^version:", body, re.M):
            newbody = re.sub(r"(^version:.*$)", r"\1\nlast_updated: " + date, body, count=1, flags=re.M)
        else:
            newbody = body + "\nlast_updated: " + date
        newline = "\r\n" if b"\r\n" in raw else "\n"
        newtext = text[:m.start()] + m.group(1) + newbody.replace("\n", newline) + m.group(3) + text[m.end():]
        if APPLY:
            open(p, "wb").write(newtext.encode("utf-8"))
        report["inserted"].append([name, date])
    print(json.dumps({"apply": APPLY, "inserted_n": len(report["inserted"]),
                      "skipped_has_key": report["skipped_has_key"],
                      "skipped_no_date_n": len(report["skipped_no_date"])}, ensure_ascii=False))
    if APPLY:
        json.dump(report, open(os.path.join(ROOT, "..", "_skill_audit_backfill.json").replace("global_skills..", "global_memory"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

if __name__ == "__main__":
    main()
