# -*- coding: utf-8 -*-
r"""tools/cjk_latin_spacing_test.py —— 中西文混排间距一致性判据（纯静态，CI 可跑）。

## 为什么需要它（轮55 首查）
字阶、行长、中文避头尾都查过，但没查过**中文与数字/Latin 之间是否统一加空格**
（俗称「盘古之白」）。这是排版一致性的硬指标：
同一页里「2014 年」与「2014年」混排，评委一眼能看出没有统一规范。
Awwwards 级站点对这类细节是零容忍的。

## 轮55 实测结论：完全一致，无缺陷
  · 中文+数字/Latin 无空格：**0 处**
  · 中文+数字/Latin 有空格：**61 处**

## 关键：这个 0 不能是「正则恒为 0」的假绿
本判据自带自检用例（SELFTEST），证明正则能抓到违例：
  '2014年第四批名录' / '国家级非遗2014' / 'AR展陈'  → 必须被抓到
  '2014 年第四批名录' / 'AR 展陈' / '扫描凤凰图腾' → 必须放过
7 个用例任一不符即判 FAIL —— 先证明尺子有效，再读它的读数。
（这是本项目第 12 次处理「测量本身不可靠」，见 U-148/U-133 等）

## 判据
1. 自检用例必须全部符合预期（尺子有效性）
2. 部署面文本里不得出现「中文紧贴数字/Latin」的无空格写法
3. 必须至少抓到 1 处正确写法，否则说明扫描面为空（假绿）

零样本判 SKIP 不判 PASS。
"""
import html as H
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(BASE, "site")

CJK = r"[\u4e00-\u9fff]"
DIG = r"[0-9]"
LAT = r"[A-Za-z]"
# 中文在左、数字/Latin 在右（无空格）
TIGHT_A = re.compile(r"(%s)(%s|%s)" % (CJK, DIG, LAT))
# 数字/Latin 在左、中文在右（无空格）
TIGHT_B = re.compile(r"(%s|%s)(%s)" % (DIG, LAT, CJK))

SELFTEST = [
    ("2014年第四批名录", True, "数字紧贴中文"),
    ("国家级非遗2014", True, "中文紧贴数字"),
    ("AR展陈", True, "Latin 紧贴中文"),
    ("2014 年第四批名录", False, "正确写法"),
    ("AR 展陈", False, "正确写法"),
    ("扫描凤凰图腾", False, "纯中文"),
    ("Lightweight AR", False, "纯 Latin"),
    # 转义序列：源码上是 反斜杠+n，运行时是换行，不该判成「中文紧贴 Latin」
    ("一只凤凰。" + chr(92) + "n扫描它", False, "中文 + JS 转义 \\n + 中文（轮56 误报点）"),
]


# JS 字符串字面量里的转义序列：源码上是 反斜杠+字母 两个字符，运行时是控制符。
# 不剥掉就会把 \n 里的字母 n 当成 Latin，误报「中文紧贴 Latin」。
# 轮56 实测：culture.js 的「一枚图腾，一只凤凰。\n扫描它」被误判成违例。
ESCAPES = re.compile(r"\\[nrtbfv0\\]|\\x[0-9a-fA-F]{2}|\\u[0-9a-fA-F]{4}")


def unescape_js(s):
    """把转义序列换成空格，只留真正会渲染的字符。"""
    return ESCAPES.sub(" ", s)


def visible_text():
    """部署面会渲染的文本：HTML 正文 + 数据层字符串。"""
    chunks = []
    hp = os.path.join(SITE, "index.html")
    if os.path.exists(hp):
        s = open(hp, encoding="utf-8", errors="ignore").read()
        s = re.sub(r"<!--.*?-->", " ", s, flags=re.S)
        s = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", s, flags=re.S | re.I)
        chunks.append(H.unescape(re.sub(r"<[^>]+>", " ", s)))
    for sub in ("assets/data", "assets/js"):
        d = os.path.join(SITE, sub.replace("/", os.sep))
        if os.path.isdir(d):
            for f in sorted(os.listdir(d)):
                if not f.endswith(".js"):
                    continue
                t = open(os.path.join(d, f), encoding="utf-8", errors="ignore").read()
                t = re.sub(r"/\*.*?\*/", " ", t, flags=re.S)
                t = re.sub(r"//[^\n]*", " ", t)
                for m in re.finditer(r"['\"\x60]([^'\"\x60]{1,500})['\"\x60]", t):
                    seg = m.group(1)
                    if re.search(CJK, seg):
                        chunks.append(unescape_js(seg))
    return " ".join(chunks)


def main():
    # 1) 先证明尺子有效
    bad = 0
    for txt, should_hit, _desc in SELFTEST:
        # 必须走判据的真实链路：先剥转义再判，否则自检与实判口径不一致
        probe = unescape_js(txt)
        hit = bool(TIGHT_A.search(probe) or TIGHT_B.search(probe))
        if hit != should_hit:
            bad += 1
    if bad:
        print("RESULT: FAIL")
        print("  - 判据自检不通过（%d/%d 用例不符），读数不可信" % (bad, len(SELFTEST)))
        return 1
    print("[PASS] 自检 %d 个用例符合预期（正则能抓到违例）" % len(SELFTEST))

    body = visible_text()
    if not re.search(CJK, body):
        print("RESULT: SKIP  扫描面里没有中文，判据未真正生效")
        return 0

    tight = []
    for m in TIGHT_A.finditer(body):
        tight.append(body[max(0, m.start() - 4):m.end() + 4])
    for m in TIGHT_B.finditer(body):
        tight.append(body[max(0, m.start() - 4):m.end() + 4])
    spaced = len(re.findall(r"%s\s+%s|%s\s+%s" % (CJK, DIG, CJK, LAT), body))

    print("混排写法：有空格 %d 处 / 无空格 %d 处" % (spaced, len(tight)))
    if tight:
        for t in tight[:8]:
            print("   -", t.replace(" ", "·")[:40])

    fails = []
    if len(tight) > 0:
        fails.append("%d 处中西文混排缺空格，与其余 %d 处不一致" % (len(tight), spaced))
    if spaced == 0:
        fails.append("一处正确写法都没抓到 —— 扫描面可能取空（假绿）")

    print()
    if fails:
        print("RESULT: FAIL")
        for f in fails:
            print("  -", f)
        return 1
    print("RESULT: PASS  中西文混排间距完全一致（%d 处全部加空格，0 违例）" % spaced)
    return 0


if __name__ == "__main__":
    sys.exit(main())
