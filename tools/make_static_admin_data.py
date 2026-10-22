# -*- coding: utf-8 -*-
r"""tools/make_static_admin_data.py —— 生成后台与页脚的「静态演示数据」。

## 需求（老大口径，2026-10-22 两次下达，第二次是三处修正）
1. **浏览量线性增加太假了** —— 周序列必须有涨有跌、有峰有谷，
   不能是「每周都比上一周多一点」那种一眼假的直线。
2. **日期要用现实的日期，九月初到十月底，一周统计一次** ——
   窗口落在 2026-09-01 起的真实日历周里，且**一天都不能进未来**。
   上一版窗口跑到 2026-11-09（比基准日 10-22 还晚），这就是「不现实」。
3. **总量 1 万到 2 万** —— 两种读法（只看浏览 / 看全部事件）都要在区间内。

## 窗口怎么定的（这里有个必须讲清的取舍）
老大说的是「到十月底」。但「按周统计」要求周是完整的，而 2026-10-19~10-25
这一周里 10-22 才是基准日 —— 本周还没过完。三种取法各有权衡：

  a) 截到 10-31 但末周只有 6 天（10-26~10-31）
     末周天数少、量也少，图上看起来又是一次「跌下去」——
     那正是 2026-10-22 老大第一次报的 bug 的形态，绝不能自己再造一个。
  b) 截到 10-25（本周日）→ 但 10-23~10-25 是未来，违反「现实日期」。
  c) **截到 10-18（最后一个已结束的周日）** ← 采用这个

  c 的代价是右界比「十月底」早了 13 天；换来的是：**周全部完整、
  一天都不在未来、末端不会因为周没结束而塌**。
  这是「日期现实」的严格解，而不是折中。

第一个周 2026-09-01~09-06 只有 6 天：9 月 1 日是周二，9 月 1 日之前
属于 8 月（不在「九月初」窗口内），所以首周天然是残缺周 —— 这是日历决定的，
不是数据造假。周量按天数折算（见 weekly_levels 里的 /7.0），
所以首周不会被硬塞满一整周的量。

## 随机性怎么做的（对着第 1 条要求）
周量 = 随机游走的基线水平 × 两处小高峰 × 一处回落 × 天数折算。
  · 随机游走：每周乘一个 0.80~1.24 的随机因子 —— 有涨有跌，不是等差数列
  · 两处小高峰：模拟展期活动/图文推送带来的脉冲（×1.22~1.45）
  · 一处回落：模拟热度退潮（×0.70~0.84）
  · 天数折算：让 6 天的首周按 6/7 缩量，不虚高
逐日 = 周量再按「周末上扬 ×1.12 / 周一略低 ×0.93 / 随机 0.76~1.32」二次分配。
所以两层都不是直线：周序有 4 次上涨 2 次下跌，日序有 25+ 次方向反转。

**种子固定**（SEED 常量），同一种子必然复现同一组数。
种子的挑法不是随便取：见 tools/pick_seed_notes.md 的筛选标准
（非单调 + 反转次数 + 峰谷比 + 环比上限 + 末周不塌）。

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

# ---- 时间基准：显式常量，不读系统时间（否则换一天跑结果就变，判据会漂）----
DEMO_DAY = dt.date(2026, 10, 22)
START = dt.date(2026, 9, 1)          # 九月初（周二）
# 右界 = 基准日之前"最后一个已结束的周日"。这样周是完整的、且不进未来。
END = DEMO_DAY - dt.timedelta(days=DEMO_DAY.weekday() + 1)   # 2026-10-18
N_DAYS_BASE = (END - START).days + 1

SEED = 20261144                       # 筛选标准见 tools/pick_seed_notes.md
PV_TOTAL = 13000                      # 浏览总量（口径 1；全部事件另算）
WEEKDAY_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
# 单一权威文案：后台横幅、页脚、docs 都读这一个字段，避免三处各写一份而漂移
DEMO_NOTE = ("演示用静态样本：数值一次生成、固定不变，不随真实访问更新。"
             "统计窗口 %s 至 %s，按周聚合。" % (START.isoformat(), END.isoformat()))


def week_spans():
    """把 [START, END] 切成「日历周」：首周可能不完整，其后每个整周。

    返回 [(start_date, end_date, days), ...]。
    为什么首周可能不完整：START 是 9-01（周二），9-01 之前属于 8 月，
    不在「九月初」窗口内，所以首周从周二开始 —— 这是日历事实，不是造假。
    """
    out = []
    first_end = START + dt.timedelta(days=6 - START.weekday())
    if first_end > END:
        first_end = END
    out.append((START, first_end, (first_end - START).days + 1))
    cur = first_end + dt.timedelta(days=1)
    while cur + dt.timedelta(days=6) <= END:
        out.append((cur, cur + dt.timedelta(days=6), 7))
        cur += dt.timedelta(days=7)
    if cur <= END:                    # 理论上不会走到（END 是周日），但兜住
        out.append((cur, END, (END - cur).days + 1))
    return out


def allocate(total, weights):
    """最大余数法：把 total 按 weights 分成整数，和恰好等于 total。

    为什么不能逐个 round：每周各自 round 之后总和会漂（正负 5 是常态），
    而「周次相加 == 累计」是后台表格与指标卡互相自洽的底线。
    """
    s = float(sum(weights))
    assert s > 0, "权重全为零，无法分配"
    raw = [total * w / s for w in weights]
    b = [int(x) for x in raw]
    rem = total - sum(b)
    order = sorted(range(len(raw)), key=lambda i: raw[i] - b[i], reverse=True)
    for k in range(rem):
        b[order[k % len(b)]] += 1
    return b


def weekly_levels(rnd, spans):
    """周量水平：随机游走 + 两处小高峰 + 一处回落（对着「线性太假」写的）。

    返回与 spans 等长的权重列表（还乘了天数折算，首周不会被灌满整周的量）。
    """
    n = len(spans)
    lvl = 1.0
    raw = []
    for _ in range(n):
        lvl *= rnd.uniform(0.80, 1.24)          # 随机游走：有涨有跌
        lvl = max(0.62, min(lvl, 2.15))         # 夹住，避免走到极端
        raw.append(lvl)

    # 两处小高峰（展期活动 / 图文推送的真实形态），但必须落在有足够空间的位
    for k in rnd.sample(range(1, n), min(2, n - 1)):
        raw[k] *= rnd.uniform(1.22, 1.45)

    # 一处回落（热度退潮）：位置随机但避开首末周，否则看起来像崩了
    dip = rnd.randrange(2, n - 1) if n >= 4 else rnd.randrange(1, n)
    raw[dip] *= rnd.uniform(0.70, 0.84)

    # 天数折算：6 天的首周按 6/7 缩量
    return [raw[i] * spans[i][2] / 7.0 for i in range(n)]


def build():
    """产出数据字典。同一种子必然同一结果（无系统时间、无网络）。"""
    rnd = random.Random(SEED)
    spans = week_spans()
    week_pv = allocate(PV_TOTAL, weekly_levels(rnd, spans))

    weeks = []
    days = []
    tot_uv = tot_sc = tot_sm = 0
    for i, (w_start, w_end, span) in enumerate(spans):
        pv = week_pv[i]
        # 访客/场景/唤凤：在周量上带随机比例（不是固定倍数，否则维度也变直线）
        uv = int(round(pv / rnd.uniform(1.17, 1.28)))
        sc = int(round(pv * rnd.uniform(0.30, 0.42)))
        sm = int(round(pv * rnd.uniform(0.10, 0.15)))
        tot_uv += uv
        tot_sc += sc
        tot_sm += sm
        weeks.append({
            "idx": i + 1,
            "start": w_start.isoformat(),
            "end": w_end.isoformat(),
            "days": span,
            "pv": pv, "uv": uv, "scenes": sc, "summon": sm,
            "events": pv + sc + sm,
        })

        # ---- 周内逐日：周末上扬 + 周一略低 + 随机，二次分配（不是等分）----
        dw = []
        for j in range(span):
            d = w_start + dt.timedelta(days=j)
            x = 1.0
            if d.weekday() >= 5:
                x *= 1.12
            if d.weekday() == 0:
                x *= 0.93
            x *= rnd.uniform(0.76, 1.32)
            dw.append(x)
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
    total_events = total_pv + tot_sc + tot_sm

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
    scene_n = allocate(tot_sc, [s for _, s in scenes])
    geo_pv = allocate(total_pv, [s for _, s in geo])
    geo_uv = allocate(tot_uv, [s for _, s in geo])

    return {
        "meta": {
            "kind": "demo-static",
            "window": {"start": START.isoformat(), "end": END.isoformat(),
                       "weeks": len(spans), "days": sum(s[2] for s in spans),
                       "demoDay": DEMO_DAY.isoformat()},
            "seed": SEED,
            "note": DEMO_NOTE,
            "generator": "tools/make_static_admin_data.py",
        },
        "totals": {
            "pv": total_pv, "uv": tot_uv,
            "scenes": tot_sc, "summon": tot_sm,
            "demoNote": DEMO_NOTE,
            "events": total_events,
            "weeks": [{"idx": w["idx"], "start": w["start"], "end": w["end"],
                       "days": w["days"],
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
    """自证：口径、区间、对账、随机形态全部现场核对，任一不符即列出来。"""
    bad = []
    t = d["totals"]
    wn = d["meta"]["window"]
    if wn["start"] != "2026-09-01":
        bad.append("窗口左界不是九月初：%s" % wn["start"])
    if wn["end"] != "2026-10-18":
        bad.append("窗口右界不是 2026-10-18（最后一个已结束的周日）：%s" % wn["end"])
    end_d = dt.date.fromisoformat(wn["end"])
    if end_d > DEMO_DAY:
        bad.append("窗口右界 %s 超过基准日 %s（出现未来日期）" % (end_d, DEMO_DAY))
    if end_d.weekday() != 6:
        bad.append("窗口右界 %s 不是周日（末周会残缺，图上又要塌一次）" % end_d)
    if len(d["weeks"]) < 4:
        bad.append("周数太少（%d），不像「按周统计」" % len(d["weeks"]))
    if len(d["days"]) != wn["days"]:
        bad.append("日数 %d != 窗口天数 %d" % (len(d["days"]), wn["days"]))

    for nm, v in (("浏览", t["pv"]), ("事件", t["events"])):
        if not 10000 <= v <= 20000:
            bad.append("%s总量 %d 不在 1 万~2 万" % (nm, v))

    # ---- 对账：所有求和关系必须恰好相等 ----
    if sum(w["pv"] for w in d["weeks"]) != t["pv"]:
        bad.append("周浏览相加 != 累计浏览")
    if sum(w["uv"] for w in d["weeks"]) != t["uv"]:
        bad.append("周访客相加 != 累计访客")
    if sum(w["events"] for w in d["weeks"]) != t["events"]:
        bad.append("周事件相加 != 事件总量")
    for x in d["days"]:
        pass
    if sum(x["pv"] for x in d["days"]) != t["pv"]:
        bad.append("逐日浏览相加 != 累计浏览")
    for key in ("langs", "screens", "referrers"):
        if sum(x["n"] for x in t[key]) != t["pv"]:
            bad.append("%s 分布相加 != 累计浏览" % key)
    if sum(x["n"] for x in t["countries"]) != t["pv"]:
        bad.append("国家浏览相加 != 累计浏览")
    if sum(x["u"] for x in t["countries"]) != t["uv"]:
        bad.append("国家访客相加 != 累计访客")
    if sum(x["n"] for x in t["sceneRanks"]) != t["scenes"]:
        bad.append("场景分布相加 != AR 场景总量")

    # ---- 逐周：七天整日 + 逐日对账 + 访客不超浏览 ----
    for w in d["weeks"]:
        dd = [x for x in d["days"] if x["week"] == w["idx"]]
        if len(dd) != w["days"]:
            bad.append("第 %d 周天数 %d != 声明 %d" % (w["idx"], len(dd), w["days"]))
        if sum(x["pv"] for x in dd) != w["pv"]:
            bad.append("第 %d 周逐日相加 != 该周浏览" % w["idx"])
        if not (0 < w["uv"] <= w["pv"]):
            bad.append("第 %d 周访客不满足 0<uv<=pv" % w["idx"])
        if not (0 <= w["scenes"] <= w["pv"] and 0 <= w["summon"] <= w["pv"]):
            bad.append("第 %d 周互动数超过浏览量" % w["idx"])
    for x in d["days"]:
        if not (0 < x["uv"] <= x["pv"]):
            bad.append("%s 逐日访客不满足 0<uv<=pv" % x["date"])

    # ---- 第 1 条要求：不许是「线性增加」那种假 ----
    v = [w["pv"] for w in d["weeks"]]
    n = len(v)
    if all(v[i] > v[i - 1] for i in range(1, n)):
        bad.append("周序列严格单调递增 —— 这就是老大说的「线性增加太假」")
    if all(v[i] < v[i - 1] for i in range(1, n)):
        bad.append("周序列严格单调递减 —— 看着像热度在崩塌")
    ups = sum(1 for i in range(1, n) if v[i] > v[i - 1])
    downs = n - 1 - ups
    if downs < 1:
        bad.append("周序列只有上涨没有回落（涨 %d 次 / 跌 %d 次）" % (ups, downs))
    if ups < 1:
        bad.append("周序列只有下跌没有回升")
    reversals = sum(1 for i in range(2, n)
                    if (v[i] - v[i - 1]) * (v[i - 1] - v[i - 2]) < 0)
    if reversals < 2:
        bad.append("周序列方向反转只有 %d 次，走势仍像一条斜线" % reversals)
    ratio = max(v) / float(min(v))
    if ratio < 1.45:
        bad.append("周峰谷比只有 %.2f，起伏不明显（<1.45 接近平线）" % ratio)
    if ratio > 3.2:
        bad.append("周峰谷比 %.2f 过大，像发生过事故而不是自然波动" % ratio)
    mx_jump = max(abs(v[i] / float(v[i - 1]) - 1) for i in range(1, n))
    if mx_jump > 0.55:
        bad.append("最大单周环比 %.0f%% 太夸张（>55%% 像数据断裂）" % (mx_jump * 100))

    # 逐日也要有起伏，不能周内等分
    dpv = [x["pv"] for x in d["days"]]
    if len(set(dpv)) < max(5, len(dpv) // 6):
        bad.append("逐日浏览量取值过于集中（%d 种），像等分或常数" % len(set(dpv)))
    if min(dpv) < 60:
        bad.append("有单日浏览低于 60（实得 %d），看着像断档" % min(dpv))
    drev = sum(1 for i in range(2, len(dpv))
               if (dpv[i] - dpv[i - 1]) * (dpv[i - 1] - dpv[i - 2]) < 0)
    if drev < len(dpv) // 3:
        bad.append("逐日方向反转仅 %d 次，日曲线太平" % drev)
    return bad


def js_blob(var_name, obj):
    body = json.dumps(obj, ensure_ascii=False, indent=2)
    return ("/* %s —— 由 tools/make_static_admin_data.py 生成，请勿手工编辑。\n"
            " * 生成命令：python tools/make_static_admin_data.py\n"
            " * 防漂移判据：tools/admin_static_data_test.py（重算并比对 SHA256）\n"
            " * 数据性质：演示用静态样本，固定不实时更新（老大 2026-10-22 指定）\n"
            " * 形态：按周聚合、周与日都有随机起伏（非线性）；窗口不进未来\n"
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
    rows = "\n".join("| 第 %d 周 | %s ~ %s | %d | %s | %s | %s | %s |" % (
        x["idx"], x["start"][5:], x["end"][5:], x["days"],
        format(x["pv"], ","), format(x["uv"], ","),
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
        "| 统计窗口 | %s 至 %s（%d 个日历周，共 %d 天） |" % (
            w["start"], w["end"], w["weeks"], w["days"]),
        "| 聚合粒度 | 按周（逐日为周内明细） |",
        "| 累计浏览 | %s |" % format(t["pv"], ","),
        "| 累计访客 | %s |" % format(t["uv"], ","),
        "| AR 场景打开 | %s |" % format(t["scenes"], ","),
        "| 唤凤互动 | %s |" % format(t["summon"], ","),
        "| 全部事件 | %s |" % format(t["events"], ","),
        "| 生成基准日 | %s（窗口不进未来） |" % w["demoDay"],
        "| 随机种子 | %d（同种子可复现） |" % d["meta"]["seed"],
        "",
        "两种读法（只看浏览 / 看全部事件）都落在 1 万~2 万区间内。",
        "",
        "## 为什么右界是 10-18 而不是 10-31",
        "",
        "「按周统计」要求周完整，而 10-19~10-25 这一周在基准日 10-22 还没过完。",
        "三个选项各自的代价：",
        "",
        "- 截到 10-31：末周只剩 6 天，量也少，图上又是一次「跌下去」",
        "  —— 正是最初要修的那个 bug 的形态，不能自己再造一个",
        "- 截到 10-25：10-23~10-25 是未来，违反「现实日期」",
        "- **截到 10-18（最后一个已结束的周日）** ← 采用",
        "",
        "代价是右界比「十月底」早 13 天；换来周全完整、一天不在未来、末端不塌。",
        "首周 09-01~09-06 只有 6 天同理：9-01 是周二，之前属于 8 月。",
        "首周的量按 6/7 折算，不虚高。",
        "",
        "## 周次明细",
        "",
        "| 周次 | 起讫（月-日） | 天数 | 浏览 | 访客 | AR 场景 | 唤凤 |",
        "|---|---|---|---|---|---|---|",
        rows,
        "",
        "## 随机形态（对着「线性太假」）",
        "",
        "周量 = 随机游走基线 × 两处小高峰 × 一处回落 × 天数折算；",
        "逐日 = 周量再按周末上扬 / 周一略低 / 随机二次分配。",
        "所以周序与日序都不是直线：",
        "",
        "- 周序上涨 %d 次 / 下跌 %d 次，峰谷比 %.2f，最大单周环比 %.0f%%" % (
            sum(1 for i in range(1, len(d["weeks"]))
                if d["weeks"][i]["pv"] > d["weeks"][i - 1]["pv"]),
            sum(1 for i in range(1, len(d["weeks"]))
                if d["weeks"][i]["pv"] < d["weeks"][i - 1]["pv"]),
            max(x["pv"] for x in d["weeks"]) / float(min(x["pv"] for x in d["weeks"])),
            max(abs(d["weeks"][i]["pv"] / float(d["weeks"][i - 1]["pv"]) - 1)
                for i in range(1, len(d["weeks"]))) * 100),
        "- 逐日峰谷比 %.2f（单日最低 %d / 最高 %d）" % (
            max(x["pv"] for x in d["days"]) / float(min(x["pv"] for x in d["days"])),
            min(x["pv"] for x in d["days"]), max(x["pv"] for x in d["days"])),
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
    v = [x["pv"] for x in d["weeks"]]
    print("生成静态演示数据：")
    print("  窗口 %s ~ %s（%d 个日历周 / %d 天，右界为最后一个已结束的周日）" % (
        wn["start"], wn["end"], wn["weeks"], wn["days"]))
    print("  累计浏览 %d / 累计访客 %d / 全部事件 %d" % (t["pv"], t["uv"], t["events"]))
    print("  AR 场景 %d / 唤凤 %d" % (t["scenes"], t["summon"]))
    print("  周浏览序列:", " ".join(str(x) for x in v))
    print("  周上涨 %d 次 / 下跌 %d 次 / 峰谷比 %.2f" % (
        sum(1 for i in range(1, len(v)) if v[i] > v[i - 1]),
        sum(1 for i in range(1, len(v)) if v[i] < v[i - 1]),
        max(v) / float(min(v))))
    print("  自证：口径 / 对账 / 非线性形态 全部成立")
    for rel in sorted(files):
        print("  写出 %s（%.1f KB）" % (rel, len(files[rel]) / 1024.0))
    print("  写出 tools/admin_stats_manifest.json")
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
