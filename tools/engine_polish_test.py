# -*- coding: utf-8 -*-
"""tools/engine_polish_test.py —— 引擎打磨判据（I-7 密度/节流 + I-8 注册表，纯静态 CI 可跑）。

对标来源（docs/对标分析报告.md §4）：
  I-7 粒子密度按面积自适应 + HUD 写入 leading/trailing 节流
      参照 VincentGarreau/particles.js 的 number.density.value_area
      与 aframevr/aframe 的 throttleLeadingAndTrailing
  I-8 场景注册表：消除「加一场景要改 3 处 + verify 白名单」的隐式耦合
      参照 aframe registerSystem：重复注册抛错 + 排查型错误文案

判据盯的是**退化**，不是"做没做过"：
  · 旧 phoenix.js 是 isMobile ? 1500 : 2600；这种硬档位若复活即判红；
  · 旧 paintHud 逐帧无条件写 style.width（224fps ⇒ 224 次/秒布局写入）；
    节流是否有效看三件事：周期常量、trailing 补写、force 旁路；
  · 旧 create() 是 if 链；注册表存在但没有 ar.js 侧的 try/catch 接错，
    等于把「静默失败」换成「抛错后仍然静默」。

注：本文件刻意不用含引号的正则字符类（如 ["']）—— 那种写法在多层管道里
反复被转义咬到，改用纯字符串扫描（registered_ids / if 链子串判断），
可读且不脆弱。
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gate_guard import verdict, emit

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(BASE, "site")

QUOTES = ("\"", "'")


def rd(p):
    return open(p, encoding="utf-8", errors="replace").read()


def strip_comments(s):
    """剥注释后再查「反模式是否复活」。
    一手教训（本轮实测）：phoenix.js 的 I-7 注释里原话写了「旧口径 isMobile ? 1500 : 2600」，
    不剥注释就扫源码，判据把这段历史说明当成了代码，误报「硬档位复活」。
    与 verify 第 20 项字体判据同一课：**扫代码必须先剥注释**（U-22/U-24 已两次记录）。
    """
    s = re.sub(r"/\\*.*?\\*/", " ", s, flags=re.S)
    s = re.sub(r"//[^\\n]*", " ", s)
    return s


def registered_ids(s):
    """扫 register(<引号>id<引号> ...，取注册的场景名。"""
    out = []
    i = 0
    key = "register("
    while True:
        j = s.find(key, i)
        if j < 0:
            break
        k = j + len(key)
        while k < len(s) and s[k] in " \t\r\n":
            k += 1
        if k < len(s) and s[k] in QUOTES:
            q = s[k]
            e = s.find(q, k + 1)
            if e > k:
                out.append(s[k + 1:e])
        i = j + len(key)
    return out


def main():
    phoenix = rd(os.path.join(SITE, "assets", "js", "phoenix.js"))
    arjs = rd(os.path.join(SITE, "assets", "js", "ar.js"))
    scenes = rd(os.path.join(SITE, "assets", "js", "ar-scenes.js"))
    fails = []
    checked = 0

    # ============ I-7a 密度按面积自适应 ============
    for tok, why in (
        ("_sampleArea", "按面积取样的入口"),
        ("_densFor", "面积到粒子数的密度函数"),
        ("DENS_MAX", "密度上限（大屏不无限加钱）"),
        ("DENS_MIN", "密度下限（再稀就看不出是凤凰）"),
        ("_resampleDensity", "resize 后按新面积重采样"),
    ):
        checked += 1
        if tok not in phoenix:
            fails.append("phoenix.js 缺少 %s（%s）" % (tok, why))

    checked += 1
    pcode = strip_comments(phoenix)
    if "? 1500 : 2600" in pcode:
        fails.append("phoenix.js 的 isMobile ? 1500 : 2600 硬档位复活（自适应被改回）")

    checked += 1
    # 闭包在 Phoenix.prototype 赋值层级，收尾是 2 空格缩进的 };
    m = re.search(r"_densFor = function \(area\) \{([\s\S]{0,400}?)\n  \};", pcode)
    if not m or "area" not in m.group(1):
        fails.append("_densFor 未使用 area 入参（密度没真的按面积算）")
    elif "DENS_MAX" not in m.group(1) or "DENS_MIN" not in m.group(1):
        fails.append("_densFor 未做上下限夹取（粒子数会随面积无限增长）")

    checked += 1
    if "DENS_MAX || this.maxParticles" not in pcode:
        fails.append("_sample 未按上限采样（resize 变密时无富余目标点）")

    # ============ I-7b HUD leading/trailing 节流 ============
    for tok, why in (
        ("hud.period", "节流周期常量（HUD 每秒写入有上限）"),
        ("hud.writes", "写入次数计数（供验收读取）"),
        ("hud.force", "状态跳变绕过节流的旁路"),
    ):
        checked += 1
        if tok not in arjs:
            fails.append("ar.js HUD 节流缺少 %s（%s）" % (tok, why))

    checked += 1
    if "hud.pending = setTimeout" not in arjs:
        fails.append("HUD 节流缺 trailing 补写（段尾进度条会停在 99.6% 不到 100%）")

    checked += 1
    if "function paintHud(now)" not in arjs:
        fails.append("paintHud 签名未接收 now（节流没有时基）")
    else:
        m2 = re.search(r"function paintHud\(now\) \{([\s\S]{0,900}?)\n    \}", arjs)
        body = m2.group(1) if m2 else ""
        if "hud.period" not in body or "return;" not in body:
            fails.append("paintHud 未做周期判据与提前返回（节流没生效）")

    checked += 1
    # 定义行也含 "paintHud(now)"，所以要查带分号的**调用**形态（反向验证时发现的判据漏洞）
    if "paintHud(now);" not in arjs:
        fails.append("frame() 未把 now 传给 paintHud（节流依赖兜底时钟）")

    checked += 1
    if "el.play.textContent !== label" not in arjs:
        fails.append("播放按钮文案未做值比较（逐帧写 DOM 反模式复活）")

    # ============ I-8 场景注册表 ============
    for tok, why in (
        ("SCENE_REGISTRY", "注册表本体"),
        ("function register(", "register() 入口"),
        ("sceneNames", "只读快照（供门禁数据驱动对账）"),
    ):
        checked += 1
        if tok not in scenes:
            fails.append("ar-scenes.js 注册表缺少 %s（%s）" % (tok, why))

    checked += 1
    if "if (id === " in scenes:
        fails.append("create() 仍是 if 链硬编码（应查 SCENE_REGISTRY）")

    checked += 1
    if "SCENE_REGISTRY[id]" not in scenes:
        fails.append("create() 未改为查表")

    checked += 1
    if "已注册" not in scenes or "排查方向" not in scenes:
        fails.append("register/create 未抛「往哪查」的排查型错误（只说失败没用）")

    ids = registered_ids(scenes)
    checked += 1
    if len(ids) < 3:
        fails.append("注册表场景数 %d < 3（交付口径三段）" % len(ids))

    checked += 1
    if not ("AR_SCENES.create(id, data)" in arjs and "try {" in arjs and "未接入播放层" in arjs):
        fails.append("ar.js 未用 try/catch 接住 create() 抛错（未知场景仍会静默失败）")

    print("I-7/I-8 引擎判据：phoenix/ar.js/ar-scenes 三侧共 %d 项" % checked)
    print("注册表已登记场景: " + ", ".join(ids))
    for f in fails:
        print("  -", f)
    code, msg = verdict(checked=checked, fails=fails, what="引擎打磨判据")
    return emit(code, msg)


if __name__ == "__main__":
    sys.exit(main())
