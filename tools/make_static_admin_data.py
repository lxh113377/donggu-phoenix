# -*- coding: utf-8 -*-
r"""tools/make_static_admin_data.py —— 生成后台与页脚的「静态演示数据」（老大 2026-10-22 指定）。

## 需求原话（2026-10-22）
「发现个 bug，这个数据突然跌下去，我改做一个静态页面吧，不实时更新，
  要不然到时候演示一更新数据，访问量成零了。访问量按周统计，
  日期为九月初到十一月初，访问量随机分配，总量为 1 万到两万」

## 三条硬约束，全部由本脚本自证（不达标就 exit 1，不写文件）
  1. 按「周」统计，窗口 2026-09-01 ~ 2026-11-09（九月初到十一月初，十个整周）
     取十个**整周**而非 09-01~11-08：后者只有 69 天，末周缺一天却分到整周的量，
     日均会比别的周高一截 —— 判据 admin_static_data_test 的「每周七个整日」正是
     在第一次实跑时抓到这件事的。
  2. 随机分配：种子固定（可复现），但每周/每日/各维度的数值由随机数决定，
     形态像真实流量（上行趋势 + 周末上扬 + 收尾冲刺 + 噪声）
  3. 总量落在 1 万 ~ 2 万 —— 而且不论按哪种口径读都落在区间内：
       浏览（pageview）总量 = 12,700 左右
       全部事件总量 = 18,500 左右
     上一版 seed_admin_data.py 为同一件事立过同样的口径，这里沿用。

## 为什么数据要生成成 JS 文件而不是 JSON
站点硬约束是「零依赖零构建 + file:// 双击可看」。fetch('x.json') 在
file:// 协议下必败（CORS），而 script src 引 JS 永远可用。
后台与页脚因此同一份数据、同一条通路，演示时不需要起任何服务。

## 幂等与防漂移
产物带 SHA256 清单（tools/admin_stats_manifest.json）。
tools/admin_static_data_test.py 每次重算并与清单比对：
手工改过一个数字、或忘了重跑生成器，都会判红。
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import random
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(BASE, "site")
# 只允许写这四处的白名单（生成器写产物是它的本职，但越界写入必须失败）
OUT_ADMIN = os.path.join(SITE, "assets", "data", "admin-stats.js")
OUT_FOOTER = os.path.join(SITE, "assets", "data", "footer-stats.js")
OUT_MANIFEST = os.path.join(BASE, "tools", "admin_stats_manifest.json")
OUT_DOC = os.path.join(BASE, "docs", "后台演示数据说明.md")
ALLOWED_OUT = (OUT_ADMIN, OUT_FOOTER, OUT_MANIFEST, OUT_DOC)

SEED = 20261108
START = dt.date(2026, 9, 1)          # 实测 weekday()==1，即周二
N_WEEKS = 10
N_DAYS = 70                           # 2026-09-01 起十个整周（至 2026-11-09）
PV_TOTAL = 12700                      # 浏览总量（口径 1）
WEEKDAY_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
# 单一权威文案：后台横幅、页脚、docs 都读这一个字段，避免三处各写一份而漂移
DEMO_NOTE = ("演示用静态样本：数值一次生成、固定不变，不随真实访问更新。"
             "统计窗口 2026-09-01 至 2026-11-09，按周聚合。")


def allocate(total, weights):
    """最大余数法：把 total 按 weights 分成整数，和恰好等于 total。

    为什么不能用 round 逐个取整：十周各自 round 之后总和会漂
    （正负 5 是常态），而「周次相加 == 累计」是后台表格与指标卡互相自洽的底线。
    """
    s = float(sum(weights))
    assert s > 0, "权重全为零，无法分配"
    raw = [total * w / s for w in weights]
    base = [int(x) for x in raw]
    rem = total - sum(base)
    order = sorted(range(len(raw)), key=lambda i: raw[i] - base[i], reverse=True)
    for k in range(rem):
        base[order[k % len(base)]] += 1
    return base


def build():
    """产出数据字典。同一种子必然同一结果（无系统时间、无网络）。"""
    rnd = random.Random(SEED)
    end = START + dt.timedelta(days=N_DAYS - 1)

    # ---- 周浏览：上行趋势 × 收尾冲刺 × 噪声 ----
    wk_w = []
    for i in range(N_WEEKS):
        trend = 0.55 + 0.45 * (i / float(N_WEEKS - 1))
        ramp = 1.0 + (0.5 * (i - 6) / 3.0 if i >= 7 else 0.0)   # 最后三周现场活动
        wk_w.append(trend * ramp * rnd.uniform(0.88, 1.12))
    week_pv = allocate(PV_TOTAL, wk_w)

    weeks = []
    week_uv = []
    week_scenes = []
    week_summon = []
    days = []
    for i in range(N_WEEKS):
        w_start = START + dt.timedelta(days=7 * i)
        w_end = w_start + dt.timedelta(days=6)
        if w_end > end:                       # 末周按窗口右界截断（本窗口恰为整周）
            w_end = end
        span = (w_end - w_start).days + 1
        pv = week_pv[i]
        uv = int(round(pv / rnd.uniform(1.17, 1.28)))
        sc = int(round(pv * rnd.uniform(0.30, 0.42)))
        sm = int(round(pv * rnd.uniform(0.10, 0.15)))
        week_uv.append(uv)
        week_scenes.append(sc)
        week_summon.append(sm)
        weeks.append({
            "idx": i + 1,
            "start": w_start.isoformat(),
            "end": w_end.isoformat(),
            "pv": pv, "uv": uv, "scenes": sc, "summon": sm,
            "events": pv + sc + sm,
        })
        # ---- 周内七日：真实星期名 + 周末上扬 + 一个随机峰值日 ----
        peak = rnd.randrange(span)
        dw = []
        for j in range(span):
            d = w_start + dt.timedelta(days=j)
            w = 1.0
            if d.weekday() >= 5:
                w *= 1.14
            if j == peak:
                w *= rnd.uniform(1.35, 1.70)
            w *= rnd.uniform(0.85, 1.15)
            dw.append(w)
        dpv = allocate(pv, dw)
        for j in range(span):
            d = w_start + dt.timedelta(days=j)
            days.append({
                "date": d.isoformat(),
                "dow": WEEKDAY_CN[d.weekday()],
                "week": i + 1,
                "pv": dpv[j],
                "uv": int(round(dpv[j] / rnd.uniform(1.17, 1.28))),
            })

    total_pv = sum(week_pv)
    total_uv = sum(week_uv)
    total_scenes = sum(week_scenes)
    total_summon = sum(week_summon)
    total_events = total_pv + total_scenes + total_summon

    # ---- 维度排行：份额表 × 最大余数，保证与总量对账 ----
    langs = [("zh-CN", 0.855), ("en-US", 0.075), ("zh-TW", 0.030),
             ("ja-JP", 0.020), ("ko-KR", 0.012), ("fr-FR", 0.008)]
    screens = [("390x844", 0.135), ("360x780", 0.125), ("430x932", 0.105),
               ("393x852", 0.095), ("1920x1080", 0.125), ("1440x900", 0.075),
               ("414x896", 0.065), ("375x667", 0.055), ("1536x864", 0.055),
               ("411x891", 0.045), ("2560x1440", 0.035), ("1024x1366", 0.025)]
    refs = [("直接访问", 0.44), ("微信图文", 0.20), ("百度搜索", 0.13),
            ("必应搜索", 0.06), ("抖音", 0.06), ("谷歌搜索", 0.05),
            ("GitHub", 0.03), ("知乎", 0.02), ("其他", 0.01)]
    scenes = [("phoenix", 0.46), ("craft", 0.33), ("red", 0.21)]
    geo = [("中国", 0.885), ("中国香港", 0.018), ("中国台湾", 0.016),
           ("日本", 0.018), ("新加坡", 0.016), ("美国", 0.018),
           ("英国", 0.010), ("德国", 0.009), ("韩国", 0.007),
           ("澳大利亚", 0.003)]

    lang_n = allocate(total_pv, [s for _, s in langs])
    screen_n = allocate(total_pv, [s for _, s in screens])
    ref_n = allocate(total_pv, [s for _, s in refs])
    scene_n = allocate(total_scenes, [s for _, s in scenes])
    geo_pv = allocate(total_pv, [s for _, s in geo])
    geo_uv = allocate(total_uv, [s for _, s in geo])

    return {
        "meta": {
            "kind": "demo-static",
            "window": {"start": START.isoformat(), "end": end.isoformat(),
                       "weeks": N_WEEKS, "days": N_DAYS},
            "seed": SEED,
            "note": DEMO_NOTE,
            "generator": "tools/make_static_admin_data.py",
        },
        "totals": {
            "pv": total_pv, "uv": total_uv,
            "scenes": total_scenes, "summon": total_summon,
            "demoNote": DEMO_NOTE,
            "events": total_events,
            "weeks": [{"idx": w["idx"], "start": w["start"], "end": w["end"],
                       "pv": w["pv"], "uv": w["uv"],
                       "scenes": w["scenes"], "summon": w["summon"],
                       "events": w["events"]} for w in weeks],
            "langs": [{"l": n, "n": c} for (n, _), c in zip(langs, lang_n)],
            "screens": [{"s": n, "n": c} for (n, _), c in zip(screens, screen_n)],
            "referrers": [{"src": n, "n": c} for (n, _), c in zip(refs, ref_n)],
            "sceneRanks": [{"scene": n, "n": c} for (n, _), c in zip(scenes, scene_n)],
            "countries": [{"c": n, "n": p, "u": u}
                          for (n, _), p, u in zip(geo, geo_pv, geo_uv)],
        },
        "weeks": weeks,
        "days": days,
    }


def check(d):
    """自证：口径、区间、对账关系全部现场核对，任一不符即列出来。"""
    bad = []
    t = d["totals"]
    wn = d["meta"]["window"]
    if wn["start"] != "2026-09-01":
        bad.append("窗口左界不是九月初：%s" % wn["start"])
    if wn["end"] != "2026-11-09":
        bad.append("窗口右界不是十一月初：%s" % wn["end"])
    if len(d["weeks"]) != N_WEEKS:
        bad.append("周数不是 %d：%d" % (N_WEEKS, len(d["weeks"])))
    if len(d["days"]) != N_DAYS:
        bad.append("天数不是 %d：%d" % (N_DAYS, len(d["days"])))
    for nm, v in (("浏览", t["pv"]), ("事件", t["events"])):
        if not 10000 <= v <= 20000:
            bad.append("%s总量 %d 不在 1 万~2 万" % (nm, v))
    if sum(w["pv"] for w in d["weeks"]) != t["pv"]:
        bad.append("周浏览相加 != 累计浏览")
    if sum(w["uv"] for w in d["weeks"]) != t["uv"]:
        bad.append("周访客相加 != 累计访客")
    if sum(w["events"] for w in d["weeks"]) != t["events"]:
        bad.append("周事件相加 != 事件总量")
    if sum(x["n"] for x in t["langs"]) != t["pv"]:
        bad.append("语言分布相加 != 浏览总量")
    if sum(x["n"] for x in t["screens"]) != t["pv"]:
        bad.append("屏幕档相加 != 浏览总量")
    if sum(x["n"] for x in t["referrers"]) != t["pv"]:
        bad.append("来源分布相加 != 浏览总量")
    if sum(x["n"] for x in t["countries"]) != t["pv"]:
        bad.append("国家分布相加 != 浏览总量")
    if sum(x["u"] for x in t["countries"]) != t["uv"]:
        bad.append("国家访客相加 != 累计访客")
    if sum(x["n"] for x in t["sceneRanks"]) != t["scenes"]:
        bad.append("场景分布相加 != 场景总量")
    for w in d["weeks"]:
        if not (0 < w["uv"] <= w["pv"]):
            bad.append("第 %d 周访客不满足 0<uv<=pv" % w["idx"])
        if not (0 <= w["scenes"] <= w["pv"] and 0 <= w["summon"] <= w["pv"]):
            bad.append("第 %d 周互动数超过浏览量" % w["idx"])
        dd = [x for x in d["days"] if x["week"] == w["idx"]]
        if sum(x["pv"] for x in dd) != w["pv"]:
            bad.append("第 %d 周逐日相加 != 该周浏览" % w["idx"])
    for x in d["days"]:
        if not (0 < x["uv"] <= x["pv"]):
            bad.append("%s 逐日访客不满足 0<uv<=pv" % x["date"])
    pvs = [x["pv"] for x in d["days"]]
    if min(pvs) < 30:
        bad.append("有单日浏览低于 30（实得 %d），看着像断档" % min(pvs))
    if d["weeks"][-1]["pv"] < d["weeks"][0]["pv"]:
        bad.append("末周低于首周：形态不像「展期临近收尾时走高」")
    return bad


def js_blob(var_name, obj):
    body = json.dumps(obj, ensure_ascii=False, indent=2)
    return ("/* %s —— 由 tools/make_static_admin_data.py 生成，请勿手工编辑。\n"
            " * 生成命令：python tools/make_static_admin_data.py\n"
            " * 防漂移判据：tools/admin_static_data_test.py（重算并比对 SHA256）\n"
            " * 数据性质：演示用静态样本，固定不实时更新（老大 2026-10-22 指定）\n"
            " */\nvar %s = %s;\n" % (var_name, var_name, body))


def sha256_text(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def write_out(path, text):
    assert path in ALLOWED_OUT, "生成器越界写入：%s" % path
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def doc_of(d):
    t = d["totals"]
    w = d["meta"]["window"]
    rows = "\n".join("| 第 %d 周 | %s ~ %s | %s | %s | %s | %s |" % (
        x["idx"], x["start"], x["end"], format(x["pv"], ","), format(x["uv"], ","),
        format(x["scenes"], ","), format(x["summon"], ",")) for x in d["weeks"])
    return "\n".join([
        "# 后台演示数据说明",
        "",
        "> 这份说明讲清三件事：后台与主站页脚用的静态演示数据从哪来、口径是什么、",
        "> 怎么重新生成。**这些数据不是真实访问量。**",
        "",
        "## 为什么改成静态",
        "",
        "后台原先直读 Cloudflare D1。演示现场一旦数据库被清空或读不到，",
        "刷新一次页面，「累计浏览」就会从一万多直接掉到个位数 ——",
        "在评委面前把最关键的数字归零。老大 2026-10-22 定的处置是：",
        "后台改为静态页面、不实时更新，数据一次生成后固定下来。",
        "",
        "## 口径",
        "",
        "| 项 | 值 |",
        "|---|---|",
        "| 统计窗口 | %s 至 %s（十个整周，共 %d 天） |" % (w["start"], w["end"], w["days"]),
        "| 聚合粒度 | 按周（逐日为周内明细） |",
        "| 累计浏览 | %s |" % format(t["pv"], ","),
        "| 累计访客 | %s |" % format(t["uv"], ","),
        "| AR 场景打开 | %s |" % format(t["scenes"], ","),
        "| 唤凤互动 | %s |" % format(t["summon"], ","),
        "| 全部事件 | %s |" % format(t["events"], ","),
        "| 随机种子 | %d（同种子可复现） |" % d["meta"]["seed"],
        "",
        "两种读法（只看浏览 / 看全部事件）都落在 1 万~2 万区间内，",
        "所以不论按哪种口径读，都符合「总量 1 万到两万」的要求。",
        "",
        "## 周次明细",
        "",
        "| 周次 | 起讫 | 浏览 | 访客 | AR 场景 | 唤凤 |",
        "|---|---|---|---|---|---|",
        rows,
        "",
        "## 重新生成",
        "",
        "    python tools/make_static_admin_data.py",
        "    python tools/admin_static_data_test.py   # 必须 PASS",
        "",
        "产物四个文件：",
        "",
        "- site/assets/data/admin-stats.js —— 后台整页数据",
        "- site/assets/data/footer-stats.js —— 主站页脚计数（与后台同源同数）",
        "- tools/admin_stats_manifest.json —— SHA256 清单，供防漂移判据比对",
        "- docs/后台演示数据说明.md —— 本文件",
        "",
        "手工改过其中任何一个数字，admin_static_data_test.py 会判红并指出是哪个",
        "文件。要改数据就改生成器再重跑，不要改产物。",
        "",
        "## 真实统计还在不在",
        "",
        "在。functions/api/ 与 D1 一行没动，只是演示面不再读它：",
        "",
        "- 想看真实数据：起本地后端 npx wrangler pages dev site，",
        "  或按 memory/07-deploy.md 用 wrangler d1 execute donggu-analytics 查询",
        "- 页脚计数与后台读的是同一份静态样本，两边永远一致",
        "- 演示结束后若要恢复实时：把 site/assets/js/analytics.js 的 renderStats",
        "  改回读 /api/stats，后台改回读 /api/admin/overview；回滚方式记录在",
        "  memory/04-decisions.md",
        "",
    ])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="只重算并比对，不写文件（防漂移判据用）")
    a = ap.parse_args()

    d = build()
    bad = check(d)
    if bad:
        print("RESULT: FAIL  数据自证不通过：")
        for b in bad:
            print("  -", b)
        return 1

    t = d["totals"]
    admin_js = js_blob("DG_STATIC_STATS", d)
    footer_js = js_blob("DG_FOOTER_STATS", {
        "window": d["meta"]["window"],
        "uniques": t["uv"],
        "pv": t["pv"],
        "label": "演示样本",
    })
    doc = doc_of(d)
    files = {
        "site/assets/data/admin-stats.js": admin_js,
        "site/assets/data/footer-stats.js": footer_js,
        "docs/后台演示数据说明.md": doc,
    }
    manifest = {
        "generator": "tools/make_static_admin_data.py",
        "seed": d["meta"]["seed"],
        "window": d["meta"]["window"],
        "totals": {"pv": t["pv"], "uv": t["uv"], "events": t["events"],
                   "scenes": t["scenes"], "summon": t["summon"]},
        "sha256": {k: sha256_text(v) for k, v in sorted(files.items())},
    }
    man_text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"

    if a.check:
        drift = []
        for rel, text in files.items():
            p = os.path.join(BASE, *rel.split("/"))
            if not os.path.exists(p):
                drift.append("%s 缺失" % rel)
                continue
            cur = open(p, encoding="utf-8").read().replace("\r\n", "\n")
            if sha256_text(cur) != manifest["sha256"][rel]:
                drift.append("%s 内容与生成器不一致（产物被手工改过或忘了重跑）" % rel)
        mp = os.path.join(BASE, "tools", "admin_stats_manifest.json")
        if not os.path.exists(mp):
            drift.append("清单缺失：tools/admin_stats_manifest.json")
        else:
            try:
                cur_man = json.loads(open(mp, encoding="utf-8").read())
            except Exception as e:
                drift.append("清单无法解析：%s" % e)
                cur_man = {}
            if cur_man.get("sha256") != manifest["sha256"]:
                drift.append("清单 SHA256 与当前产物不一致")
        print()
        if drift:
            print("RESULT: FAIL  静态演示数据漂移：")
            for x in drift:
                print("  -", x)
            return 1
        print("RESULT: PASS  三个产物与生成器逐字节一致（SHA256 对账）")
        return 0

    for rel, text in files.items():
        write_out(os.path.join(BASE, *rel.split("/")), text)
    write_out(OUT_MANIFEST, man_text)

    wn = d["meta"]["window"]
    print("生成静态演示数据：")
    print("  窗口 %s ~ %s（%d 周 / %d 天）" % (wn["start"], wn["end"], N_WEEKS, N_DAYS))
    print("  累计浏览 %d / 累计访客 %d / 全部事件 %d" % (t["pv"], t["uv"], t["events"]))
    print("  AR 场景 %d / 唤凤 %d" % (t["scenes"], t["summon"]))
    print("  周浏览序列:", " ".join(str(x["pv"]) for x in d["weeks"]))
    print("  自证对账全部成立（周次/逐日/六个维度共 12 条求和关系）")
    for rel in sorted(files):
        print("  写出 %s（%.1f KB）" % (rel, len(files[rel]) / 1024.0))
    print("  写出 tools/admin_stats_manifest.json")
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
