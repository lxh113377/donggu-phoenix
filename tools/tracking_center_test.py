# -*- coding: utf-8 -*-
r"""tools/tracking_center_test.py —— 居中宽字距必须补偿（纯静态，CI 可跑）。

## 原理
letter-spacing 加在每个字符「之后」，**包括最后一个**。
所以居中排布的宽字距文本，盒子右侧比墨迹多出一个字距：
  几何中心 = 容器中心，但墨迹视觉中心 = 中心 - ls/2 → 看起来偏左
偏移量 = letter-spacing / 2，与字数无关。

## 轮60 的缺陷与修法
.hero h1 / .hero h1 em / .hero-tag 在移动端随 .hero-inner 居中，
偏移 2.16px / 5.96px / 2.52px（em 那处 0.31 个字符宽，肉眼明显）。
修法：margin-right: -<letter-spacing>，让盒子宽度 = 墨迹宽度。
左对齐时右边界收缩不影响视觉，故无条件加是安全的。

## 为什么必须用 HTML DOM 树判断「居中」（轮62 自检抓到的缺陷）
第一版只看 CSS 选择器字符串的祖先前缀，于是漏掉真正重要的情形：
  .hero-inner{text-align:center} 让其后代 h1、h1 em 都居中，
  但选择器 ".hero h1 em" 的字符串前缀里**没有 .hero-inner**。
若不用 DOM 树，判据恰好守不住轮60 那 3 个元素 —— 最该管的没管住。
现改为：解析 index.html 的 DOM 树，对每个宽字距规则做真实选择器匹配，
再看该元素自身或任一**祖先元素**是否命中居中规则。

## 判据口径（有意保守，防过度修正）
只有「居中 + 偏移 >= 1.5px」才要求补偿。
轮61 实测另有 4 个居中宽字距元素（#cam .hint / .ar-hint / .nav a / .toast）
偏移 0.60~1.04px，低于阈值故不要求 —— 每条补偿都是维护成本，
为 1px 以内加规则属于噪音。1.5px ≈ 1/3 个 12px 字符宽，是肉眼可辨下限。

## 自检（第 13 次处理「测量本身不可靠」）
先用自己的样本证明尺子有效，任一不符即判 FAIL：
  · 居中+0.30em+无补偿 → 必须报
  · 居中+0.30em+有补偿 → 必须放过
  · 居中+0.05em → 放过（窄字距）
  · 居中+0.12em 但偏移仅 0.6px → 放过（低于阈值）
  · 左对齐+0.30em → 放过（不居中就不偏）
  · 祖先居中+子级宽字距 → 必须报（就是第一版漏掉的那种）
"""
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS = os.path.join(BASE, 'site', 'assets', 'css', 'main.css')
HTML = os.path.join(BASE, 'site', 'index.html')

MIN_OFFSET_PX = 1.5
MIN_TRACKING_EM = 0.10

VOID_TAGS = {'br', 'img', 'input', 'meta', 'link', 'hr', 'source', 'path', 'circle',
             'rect', 'use', 'stop', 'polygon', 'line', 'ellipse'}


def strip_comments(s):
    return re.sub(r'/\*.*?\*/', ' ', s, flags=re.S)


def parse_dom(html_text):
    """极简 DOM：返回 [{'tag','classes','id','parent'}]，parent 为索引或 None。"""
    s = re.sub(r'<!--.*?-->', ' ', html_text, flags=re.S)
    s = re.sub(r'<(script|style)\b[^>]*>.*?</\1>', ' ', s, flags=re.S | re.I)
    nodes = []
    stack = []
    for m in re.finditer(r'<(/?)([a-zA-Z][\w-]*)((?:"[^"]*"|\'[^\']*\'|[^>"\'])*)>', s):
        closing, tag, attrs = m.group(1), m.group(2).lower(), m.group(3)
        if closing:
            for i in range(len(stack) - 1, -1, -1):
                if stack[i][0] == tag:
                    del stack[i:]
                    break
            continue
        classes = []
        cm = re.search(r'class\s*=\s*"([^"]*)"', attrs) or re.search(r"class\s*=\s*'([^']*)'", attrs)
        if cm:
            classes = [c for c in cm.group(1).split() if c]
        nid = None
        im = re.search(r'\bid\s*=\s*"([^"]*)"', attrs) or re.search(r"id\s*=\s*'([^']*)'", attrs)
        if im:
            nid = im.group(1)
        idx = len(nodes)
        parent = stack[-1][1] if stack else None
        nodes.append({'tag': tag, 'classes': set(classes), 'id': nid, 'parent': parent})
        if tag not in VOID_TAGS and not attrs.rstrip().endswith('/'):
            stack.append((tag, idx))
    return nodes


def comp_parts(comp):
    """把复合选择器拆成 tag / classes / id，剥掉伪类伪元素与组合符。"""
    base = re.split(r'[:\[]', comp)[0]
    base = re.sub(r'[>+~]', ' ', base).strip()
    classes = re.findall(r'\.([\w-]+)', base)
    ids = re.findall(r'#([\w-]+)', base)
    tm = re.match(r'^([a-zA-Z][\w-]*)', base)
    tag = tm.group(1).lower() if tm else None
    return tag, [c for c in classes], ids


def comp_match(node, comp):
    tag, classes, ids = comp_parts(comp)
    if tag and node['tag'] != tag:
        return False
    for c in classes:
        if c not in node['classes']:
            return False
    for i in ids:
        if node['id'] != i:
            return False
    return True


def match_selector(nodes, idx, parts, k):
    """nodes[idx] 及其祖先能否按 parts[0..k] 逐级匹配（后代组合器）。"""
    if not comp_match(nodes[idx], parts[k]):
        return False
    if k == 0:
        return True
    a = nodes[idx]['parent']
    while a is not None:
        if match_selector(nodes, a, parts, k - 1):
            return True
        a = nodes[a]['parent']
    return False


def sel_matches(nodes, sel):
    """返回匹配该选择器的元素索引集合。"""
    parts = sel.split()
    if not parts:
        return set()
    return set(i for i in range(len(nodes)) if match_selector(nodes, i, parts, len(parts) - 1))


def parse_tokens(s):
    t = {}
    for m in re.finditer(r'(--[\w-]+)\s*:\s*([^;}]+)', s):
        t[m.group(1)] = m.group(2).strip()
    return t


def to_px(v, tokens, parent_fs=16.0):
    v = v.strip()
    m = re.match(r'^var\((--[\w-]+)\)$', v)
    if m:
        return to_px(tokens.get(m.group(1), '0'), tokens, parent_fs)
    cl = re.search(r'clamp\(([^)]*)\)', v)
    if cl:
        return max(to_px(x, tokens, parent_fs) for x in cl.group(1).split(','))
    mm = re.match(r'^([\d.]+)rem$', v)
    if mm:
        return float(mm.group(1)) * 16
    mm = re.match(r'^([\d.]+)px$', v)
    if mm:
        return float(mm.group(1))
    mm = re.match(r'^([\d.]+)em$', v)
    if mm:
        return float(mm.group(1)) * (parent_fs or 16)
    return 0.0


def analyze(css_text, html_text):
    """返回 (已补偿且需补偿, 需补偿但缺补偿, 低于阈值忽略)。"""
    s = strip_comments(css_text)
    tokens = parse_tokens(s)
    nodes = parse_dom(html_text)

    centered_sels, neg_sels, wide_rules, fs_rules = [], [], [], []
    for m in re.finditer(r'([^{}@]+)\{([^{}]*)\}', s):
        sel = ' '.join(m.group(1).split())
        body = m.group(2)
        if not sel or sel.startswith('@'):
            continue
        sq = body.replace(' ', '')
        for one in [x.strip() for x in sel.split(',') if x.strip()]:
            if 'text-align:center' in sq:
                centered_sels.append(one)
            if re.search(r'margin-right:-[0-9.]', sq) or re.search(r'margin:-[0-9.]', sq):
                neg_sels.append(one)
            # 跳过瞬态规则（:hover/:focus/:active）：
            # 它们只在指针交互时生效，触屏（本站主场景）永不触发，
            # 且 hover 时的字距变化是有意设计，不该要求静态补偿（轮62）。
            if re.search(r':(hover|focus|active|focus-visible|focus-within)\b', one):
                continue
            ls = re.search(r'letter-spacing\s*:\s*([^;}]+)', body)
            if ls:
                mm = re.match(r'^([\d.]+)em$', ls.group(1).strip())
                if mm and float(mm.group(1)) >= MIN_TRACKING_EM:
                    wide_rules.append((one, float(mm.group(1))))
            # 记录所有 font-size，供 em 沿 DOM 继承链解析
            # （.hero h1 em 的 .185em 必须相对父级 --fs-hero 算，
            #   按 16px 硬算会把 5.96px 偏移误判成 0.92px —— 轮62 自检暴露）
            fsm = re.search(r'(?<![-\w])font-size\s*:\s*([^;}]+)', body)
            if fsm:
                fs_rules.append((one, fsm.group(1).strip()))

    centered_els = set()
    for cs in centered_sels:
        centered_els |= sel_matches(nodes, cs)
    # text-align 可继承：把居中传播到后代
    grew = True
    while grew:
        grew = False
        for i, nd in enumerate(nodes):
            if i in centered_els or nd['parent'] is None:
                continue
            if nd['parent'] in centered_els:
                centered_els.add(i)
                grew = True

    neg_els = set()
    for ns in neg_sels:
        neg_els |= sel_matches(nodes, ns)

    # font-size 沿祖先链解析：em 相对父级字号，未声明则继承父级
    # 收集所有匹配规则的 font-size，取**最大值**（最坏情况）：
    # 媒体查询里的覆盖值（如移动端 2.4rem）小于桌面 clamp 上限（6.5rem），
    # 若按「后写者胜」只取一条，会把桌面 5.96px 偏移低估成 2.20px。
    fs_matched = [(sel_matches(nodes, sel), raw) for sel, raw in fs_rules]
    _memo = {}

    def font_px(i):
        if i in _memo:
            return _memo[i]
        raws = [rv for matched, rv in fs_matched if i in matched]
        parent = nodes[i]['parent']
        base = font_px(parent) if parent is not None else 16.0
        if raws:
            val = max(to_px(r, tokens, base) for r in raws)
        else:
            val = base
        _memo[i] = val
        return val

    ok, missing, below = [], [], []
    seen = set()
    for one, k in wide_rules:
        els = sel_matches(nodes, one)
        if not els:
            # 选择器匹配不到 DOM（可能带伪类），退回按字符串末段类名找元素
            tail = one.split()[-1]
            _t, cls, ids = comp_parts(tail)
            els = set(i for i, nd in enumerate(nodes)
                      if (cls and all(c in nd['classes'] for c in cls)) or
                         (ids and nd['id'] in ids))
        hit_centered = [i for i in sorted(els) if i in centered_els]
        if not hit_centered:
            continue
        fs = max(font_px(i) for i in hit_centered)
        off = (k * fs) / 2.0
        key = one
        if key in seen:
            continue
        seen.add(key)
        if off < MIN_OFFSET_PX:
            below.append((one, k, off))
        elif all(i in neg_els for i in hit_centered):
            ok.append((one, k, off))
        else:
            missing.append((one, k, off))
    return ok, missing, below


# .a 用于「自身居中」用例，.wrap>.b 用于「祖先居中」与其余用例；
# 两者必须互相独立，否则 .a 的居中会经继承污染 .b 的用例（轮62 自检抓到）。
FIXTURE = ('<div class="a">x</div>'
           '<div class="wrap"><div class="b">y</div></div>')
SELFTEST = [
    (".a{text-align:center;letter-spacing:.30em;font-size:16px}", True,
     '居中+0.30em+无补偿 → 应报'),
    (".b{text-align:center;letter-spacing:.30em;font-size:16px;margin-right:-.30em}", False,
     '居中+0.30em+有补偿 → 应放过'),
    (".b{text-align:center;letter-spacing:.05em;font-size:16px}", False,
     '居中+0.05em（窄字距）→ 应放过'),
    (".b{text-align:center;letter-spacing:.12em;font-size:10px}", False,
     '居中+0.12em 偏移仅 0.6px → 低于阈值，应放过'),
    (".b{letter-spacing:.30em;font-size:16px}", False,
     '左对齐+0.30em → 不居中就不偏，应放过'),
    (".wrap{text-align:center}\n.b{letter-spacing:.30em;font-size:16px}", True,
     '祖先居中+子级宽字距 → 应报（第一版漏掉的场景）'),
]


def selftest():
    bad = []
    for css, should_flag, desc in SELFTEST:
        _ok, missing, _below = analyze(css, FIXTURE)
        flagged = len(missing) > 0
        if flagged != should_flag:
            bad.append('%s（期望%s 实得%s）' % (
                desc, '报' if should_flag else '放过', '报' if flagged else '放过'))
    return bad


def main():
    if not (os.path.exists(CSS) and os.path.exists(HTML)):
        print('RESULT: SKIP  找不到 main.css 或 index.html')
        return 0

    bad = selftest()
    if bad:
        print('RESULT: FAIL  判据自检不通过，读数不可信：')
        for b in bad:
            print('  -', b)
        return 1
    print('[PASS] 自检 %d 个用例符合预期（含 DOM 祖先居中场景）' % len(SELFTEST))

    css = open(CSS, encoding='utf-8', errors='replace').read()
    html = open(HTML, encoding='utf-8', errors='replace').read()
    ok, missing, below = analyze(css, html)

    print('居中宽字距元素：已补偿 %d，缺补偿 %d，低于阈值忽略 %d'
          % (len(ok), len(missing), len(below)))
    for sel, k, off in sorted(ok):
        print('  [ok]     %-38s ls=%.2fem 偏移 %.2fpx 已补偿' % (sel[:38], k, off))
    for sel, k, off in sorted(missing):
        print('  [缺补偿] %-38s ls=%.2fem 偏移 %.2fpx' % (sel[:38], k, off))
    if below:
        print('  低于 %.1fpx 不要求补偿：%s' % (
            MIN_OFFSET_PX, ', '.join('%s %.2fpx' % (s, o) for s, _k, o in sorted(below)[:6])))

    print()
    if not ok and not missing:
        print('RESULT: SKIP  未找到居中宽字距元素（解析可能失效）')
        return 0
    if missing:
        print('RESULT: FAIL')
        print('  - %d 个居中宽字距元素缺末字空白补偿，墨迹会视觉左偏；'
              '加 margin-right:-<letter-spacing>' % len(missing))
        return 1
    print('RESULT: PASS  所有需补偿的居中宽字距元素都已补偿（%d 个）' % len(ok))
    return 0


if __name__ == '__main__':
    sys.exit(main())
