# -*- coding: utf-8 -*-
"""run_bench.py — 10 任务浏览器基准套件 + 质量分 Q = 成功率 × 首次通过率 × 效率系数
形态：任务清单 + 评分公式 + 基线快照比对。每任务记录：pass(0/1), first_try(0/1), rounds(int)
用法: python run_bench.py --tasks tasks.json --out q_score.json [--baseline base.json]
"""
import json, sys

def q_score(results):
    n = len(results)
    if not n: return 0.0, {"error": "empty"}
    sr = sum(r["pass"] for r in results) / n
    ft = sum(r["first_try"] for r in results) / n
    eff = n / sum(max(1, r["rounds"]) for r in results)  # 1 round = 1.0, 多轮衰减
    return round(sr * ft * eff, 4), {"success": sr, "first_try": ft, "efficiency": round(eff, 4)}

def main():
    argv = sys.argv[1:]
    paths = {}
    i = 0
    while i < len(argv):
        if argv[i].startswith("--") and i + 1 < len(argv):
            paths[argv[i]] = argv[i + 1]
            i += 2
        else:
            i += 1
    res = json.load(open(paths.get("--tasks", "tasks.json"), encoding="utf-8-sig"))
    q, parts = q_score(res)
    out = {"Q": q, "parts": parts, "n": len(res)}
    if "--baseline" in paths:
        base = json.load(open(paths["--baseline"], encoding="utf-8-sig"))
        bq, _ = q_score(base)
        out["baseline_Q"] = bq
        out["lift_pct"] = round((q - bq) / bq * 100, 1) if bq else None
        out["gate_30pct"] = (out.get("lift_pct") or 0) >= 30
    op = paths.get("--out", "q_score.json")
    json.dump(out, open(op, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False))
    sys.exit(0 if out.get("gate_30pct", True) else 1)

if __name__ == "__main__":
    main()
