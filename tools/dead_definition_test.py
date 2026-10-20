# -*- coding: utf-8 -*-
"""tools/dead_definition_test.py —— 「定义了必须被调用」判据（纯静态，CI 可跑）。

## 为什么需要它（轮53 实测出的判据缺口）
engine_polish_test.py 用「tok not in phoenix」这种名字存在性检查
来验证 I-7 的关键函数（_sampleArea / _densFor / _resampleDensity）。
所以「定义还在、但调用点被删或被改名」照样 PASS。

反向验证实测（轮53）：把调用点 this._densFor( 改成 this._densOFF(，
定义处 Phoenix.prototype._densFor = function 仍在 —— 判据 23 项全 PASS。
即粒子密度自适应被完全断开，门禁看不见。

## 这不是孤例，是本项目反复踩的同一类坑
  · 轮17  revealTall() 定义了没调用 —— verify_site 后来专门加了「兜底必须真的被调用」
  · 轮52  同一课：函数存在 != 行为发生
「定义了但没调用」是静默失效里最难发现的一种：不报错、不崩、代码看着还在。

## 判据
对引擎里「必须生效」的方法：
  1) 定义存在（X.prototype.NAME = function 或 function NAME()）
  2) 且至少有一个调用点（this.NAME( / self.NAME( 等接收者）
只定义零调用 = 死代码 = FAIL。

## 为什么用正则而不是 AST
本站零构建零依赖，判据也必须零依赖可跑。正则扫接收者点调用足够覆盖本站写法，
且必须剥注释后再扫（U-22/U-24/U-126 三次教训：注释里的字面量不是行为）。
"""
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(BASE, "site")

# (文件, 定义模式类型, 类名或 None, 方法名, 为什么必须被调用)
MUST_BE_CALLED = [
    ("assets/js/phoenix.js", "proto", "Phoenix", "_sampleArea", "按画布面积取样，密度自适应的入口"),
    ("assets/js/phoenix.js", "proto", "Phoenix", "_densFor", "面积到粒子数的映射，I-7 的核心"),
    ("assets/js/phoenix.js", "proto", "Phoenix", "_resampleDensity", "resize 后按新面积重采样"),
    ("assets/js/wood-to-statue.js", "fn", None, "revealStatue", "雕刻画布成像主绘制"),
]

RECEIVERS = r"(?:this|self|_this|_self|api|inst|engine|_engine|phx|_ph|p|it|obj)"


def strip_comments(s):
    """剥注释后再扫 —— 注释里的函数名不是行为。"""
    s = re.sub(r"/\*.*?\*/", " ", s, flags=re.S)
    s = re.sub(r"//[^\n]*", " ", s)
    return s


def main():
    fails = []
    checked = 0
    skipped = 0

    for rel, kind, cls, name, why in MUST_BE_CALLED:
        p = os.path.join(SITE, rel.replace("/", os.sep))
        if not os.path.exists(p):
            print("[SKIP] 文件不存在 %s" % rel)
            skipped += 1
            continue
        s = strip_comments(open(p, encoding="utf-8", errors="replace").read())

        if kind == "proto":
            def_pat = r"%s\.prototype\.%s\s*=\s*function" % (re.escape(cls), re.escape(name))
        else:
            def_pat = r"function\s+%s\s*\(" % re.escape(name)
        has_def = re.search(def_pat, s) is not None

        if kind == "proto":
            call_pat = r"\b%s\.%s\s*\(" % (RECEIVERS, re.escape(name))
        else:
            # 普通函数：裸调用。先摘掉定义本身，避免把 function NAME( 当调用点
            body_nc = re.sub(r"function\s+%s\s*\(" % re.escape(name), "@@DEF@@", s)
            call_pat = r"\b%s\s*\(" % re.escape(name)
        calls = re.findall(call_pat, body_nc if kind != "proto" else s)

        checked += 1
        if not has_def:
            fails.append("%s 定义不存在（%s）—— %s" % (name, rel, why))
        elif not calls:
            fails.append("%s 只有定义、零调用点（%s）—— %s，功能实际未生效" % (name, rel, why))
        else:
            print("[PASS] %-20s 定义 + %d 处调用（%s）" % (name, len(calls), rel.split("/")[-1]))

    print()
    print("检查 %d 个「必须生效」的引擎方法（跳过 %d）" % (checked, skipped))
    print()
    if checked == 0:
        print("RESULT: SKIP  无可检查项")
        return 0
    if fails:
        print("RESULT: FAIL")
        for f in fails:
            print("  -", f)
        return 1
    print("RESULT: PASS  %d 个引擎方法均有定义且确有调用点" % checked)
    return 0


if __name__ == "__main__":
    sys.exit(main())