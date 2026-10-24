# -*- coding: utf-8 -*-
r"""tools/brand_color_parity_test.py —— 两站品牌色必须同值（纯静态，CI 可跑）。

## 为什么需要（轮131 实测发现）
后台 admin/index.html 的注释自己写着：

    配色与主站同源：凤红 #B3202C、金 #D4A24E、夜色 #0B0908。

即它**声明了一条跨站不变量**。实测却发现：
  · 凤红  主站 --she-red #B3202C / 后台 --red #B3202C  一致
  · 夜色  主站 --she-ink #0B0908 / 后台 --bg  #0B0908  一致
  · **金   主站 --she-gold #D4A24C / 后台 --gold #D4A24E  差 2**
而且注释里印的也是那个错值 —— 等于「声明 + 文档 + 代码」三处一起错，
没有任何判据会响。这与 U-395（memory 4KB 硬限没人守）、
U-401（canvas 色须对齐令牌没人守）同族。

轮127 建的 admin_canvas_tokens_test 只查「canvas 色 ∈ 本页令牌」，
本页内部自洽即可通过 —— **跨站分叉它看不见**，这是它的边界。

## 判据范围 = 注释声明的不变量，不外扩
只锁三项：凤红 / 金 / 夜色。
不锁 --fg（主站 #F4EDE1 是纸色、后台 #EDE6DC 是暗面板正文色，
两种用途，注释也没声明它同源）—— 判据不该把「我认为应该一致」
当成「代码声明了必须一致」，否则就是拿臆断当规格，会误伤合理设计。

## 判据
  A 从两站各解析 :root 的色值令牌表。
  B 按语义配对表逐项比对，十六进制必须完全相等。
  C 后台注释里若出现这三项的十六进制字面量，也必须与配对值一致
    （本轮的错正是注释与代码一起错，只比代码会漏掉文档漂移）。
  D 品牌金在两站的所有使用点（含 canvas 硬编码）都不得残留旧值。

## 尺子有效性自检（U-149/U-151）
  S1 把后台 --gold 改回 D4A24E -> 必须 FAIL（跨站分叉要能抓到）
  S2 只把注释里的金改错、代码不动 -> 必须 FAIL（文档漂移要能抓到）
  S3 两站全一致时不得误报
任一失效即判 FAIL —— 否则本判据是恒真的安慰剂。
自检在内存里改文本，不写盘。

## 诚实语义
读不到任一文件 / 解析不出令牌 -> SKIP 并说明，不判 PASS。
"""
import io
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN_CSS = os.path.join(BASE, 'site', 'assets', 'css', 'main.css')
ADMIN_HTML = os.path.join(BASE, 'site', 'admin', 'index.html')

# 语义配对：(中文名, 主站令牌, 后台令牌)
PAIRS = [
    ('凤红', '--she-red', '--red'),
    ('品牌金', '--she-gold', '--gold'),
    ('夜色底', '--she-ink', '--bg'),
]
# 注释里可能出现的写法：中文名 -> 应有的值（由主站侧决定）
LABEL_TO_MAIN = {'凤红': '--she-red', '金': '--she-gold', '夜色': '--she-ink'}


def strip_comments(t):
    """剥掉 CSS/JS 块注释、HTML 注释与行首 //。

    残留扫描必须先剥注释：注释里允许出现旧值（本轮就刻意写了
    「原先注释与 --gold 都写成 D4A24E 结尾」来说明改了什么）。
    若不剥，将来任何人写一条带 #D4A24E 的说明注释就会把判据点红 ——
    那是靠巧合才绿的判据，不是可靠的判据。
    """
    t = re.sub(r'/\*.*?\*/', '', t, flags=re.S)
    t = re.sub(r'<!--.*?-->', '', t, flags=re.S)
    t = re.sub(r'^\s*//.*$', '', t, flags=re.M)
    return t


def norm(h):
    h = h.lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    return ('#' + h[:6]).upper()


def parse_root(path):
    """解析文件里 :root{...} 的色值令牌。"""
    s = io.open(path, encoding='utf-8', errors='ignore').read()
    out = {}
    for m in re.finditer(r':root\s*\{(.*?)\}', s, flags=re.S):
        for _m in re.finditer(r'(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{3,8})\b',
                                m.group(1)):
            out[_m.group(1)] = norm(_m.group(2))
    return out, s


def check_parity(main_tok, adm_tok):
    bad = []
    for label, mk, ak in PAIRS:
        mv, av = main_tok.get(mk), adm_tok.get(ak)
        if mv is None or av is None:
            bad.append('%s：令牌缺失（主站 %s=%s / 后台 %s=%s）'
                       % (label, mk, mv, ak, av))
        elif mv != av:
            bad.append('%s跨站分叉：主站 %s=%s，后台 %s=%s'
                       % (label, mk, mv, ak, av))
    return bad


def check_comment(admin_src, main_tok):
    """后台注释里写的十六进制值必须与主站一致（文档漂移也要抓）。"""
    bad = []
    # 只扫注释区（/* ... */），避免把代码里的正确值当注释
    for cm in re.finditer(r'/\*.*?\*/', admin_src, flags=re.S):
        blk = cm.group(0)
        if '配色' not in blk and '同源' not in blk:
            continue
        for m in re.finditer(r'(凤红|金|夜色)\s*(#[0-9a-fA-F]{6})\b', blk):
            label, val = m.group(1), norm(m.group(2))
            want = main_tok.get(LABEL_TO_MAIN[label])
            if want and val != want:
                bad.append('注释里的%s写成 %s，主站是 %s（文档与实现分叉）'
                           % (label, val, want))
    return bad


def check_no_stale(admin_src, adm_tok):
    """后台所有使用点都必须是当前 --gold 值，不得残留旧品牌色。"""
    bad = []
    gold = adm_tok.get('--gold')
    if not gold:
        return ['后台解析不到 --gold']
    r_, g_, b_ = (int(gold[i:i + 2], 16) for i in (1, 3, 5))
    stale = []
    # 行号仍按原文算：先剥注释得到「干净文本」，但为了报出可读的行号，
    # 这里在原文上匹配、再用干净文本判断该位置是否落在注释里。
    _clean = strip_comments(admin_src)
    for m in re.finditer(r'#[0-9a-fA-F]{6}\b', admin_src):
        if m.group(0) not in _clean:
            continue   # 该字面量只存在于注释中，不算代码残留
        v = norm(m.group(0))
        # 与品牌金只差 1~4 且不在令牌表里 -> 判定为残留旧值
        if v != gold and v not in adm_tok.values():
            dr, dg, db = (abs(int(v[i:i + 2], 16) - int(gold[i:i + 2], 16))
                          for i in (1, 3, 5))
            if dr <= 4 and dg <= 4 and db <= 4 and max(dr, dg, db) >= 1:
                ln = admin_src[:m.start()].count('\n') + 1
                stale.append('%s（行 %d，与 --gold 差 R%d/G%d/B%d）'
                             % (v, ln, dr, dg, db))
    if stale:
        bad.append('疑似品牌金残留旧值：%s' % '; '.join(sorted(set(stale))))
    return bad


def run_check(main_src, adm_src):
    mt = parse_root_from(main_src)
    at = parse_root_from(adm_src)
    bad = check_parity(mt, at)
    bad += check_comment(adm_src, mt)
    bad += check_no_stale(adm_src, at)
    return bad, mt, at


def strip_media(src, keyword='print'):
    """按大括号配对剥掉 @media <keyword>{...} 整块。

    打印态是为「白底打印」重新配色的（轮181 在 @media print 里翻转
    :root 令牌），那些覆盖值不是品牌色分叉，不该参与跨站品牌比对。
    正则 .*? 配第一个右花括号会在嵌套块中途停下，故必须按括号深度切。"""
    out = []
    i = 0
    pat = re.compile(r'@media[^{]*\b' + keyword + r'\b[^{]*\{')
    while True:
        m = pat.search(src, i)
        if not m:
            out.append(src[i:])
            break
        out.append(src[i:m.start()])
        depth = 1
        j = m.end()
        while j < len(src) and depth > 0:
            if src[j] == '{':
                depth += 1
            elif src[j] == '}':
                depth -= 1
            j += 1
        i = j
    return ''.join(out)


def parse_root_from(src):
    out = {}
    src = strip_media(src, 'print')
    for m in re.finditer(r':root\s*\{(.*?)\}', src, flags=re.S):
        for _m in re.finditer(r'(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{3,8})\b',
                                m.group(1)):
            out[_m.group(1)] = norm(_m.group(2))
    return out


def selftest(main_src, adm_src):
    """证明判据能抓到三类真实漂移。"""
    bad = []
    mt = parse_root_from(main_src)
    gold_main = mt.get('--she-gold')
    if not gold_main:
        return ['主站解析不到 --she-gold，自检无法进行']

    # S0（轮181）：主站 @media print 里覆盖品牌令牌，不得被当成跨站分叉。
    # 这条锁死「打印态专用覆盖不参与品牌比对」的语义 —— 我加 print
    # 令牌翻转时正是被旧解析器（扫所有 :root、后来者胜）误判成分叉。
    # S0 的期望值必须来自**独立来源**：后台的 --gold。
    # 上一版用 mt.get('--she-gold') 当基准，而 mt 本身就来自被污染的
    # 同一份解析 —— 自己跟自己比恒等，去掉 strip_media 后两边一起变脏，
    # S0 仍是空检查（牙齿测试实测抓到）。
    at_self = parse_root_from(adm_src)
    gold_admin = at_self.get('--gold')
    if not gold_admin:
        bad.append('S0 构造失败：后台解析不到 --gold，没有独立基准')
    else:
        # ① 主站解析结果必须等于后台真值，才说明 print 覆盖被剥掉了
        if norm(gold_main) != norm(gold_admin):
            bad.append('S0 主站品牌金解析到 %r，与后台真值 %r 不符 '
                       '—— @media print 里的令牌覆盖未被剥离'
                       % (gold_main, gold_admin))
        # ② 追加一个 print 覆盖块后，解析结果仍须等于后台真值
        with_print = (main_src + '\n@media print{\n'
                      '  :root{--she-gold:#8a5f14;'
                      '--she-ink:#fff}\n}\n')
        mp = parse_root_from(with_print)
        if mp.get('--she-gold') != norm(gold_admin):
            bad.append('S0 追加 print 覆盖后解析到 %r（应仍为 %s）'
                       ' —— strip_media 未生效'
                       % (mp.get('--she-gold'), norm(gold_admin)))
    # S1：后台 --gold 改回旧的错值
    s1 = adm_src.replace('--gold:' + gold_main.lstrip('#'),
                         '--gold:D4A24E', 1)
    if s1 == adm_src:
        s1 = re.sub(r'(--gold\s*:\s*#[0-9a-fA-F]{6})', r'--gold:#D4A24E',
                    adm_src, count=1)
    if s1 == adm_src:
        bad.append('S1 构造失败：改不动 --gold')
    else:
        b1 = check_parity(mt, parse_root_from(s1))
        hit = any('跨站分叉' in x and '品牌金' in x for x in b1)
        print('  [%s] S1 后台 --gold 改成 D4A24E -> %s'
              % ('ok' if hit else 'X', '被抓到' if hit else '没抓到（判据无牙）'))
        if not hit:
            bad.append('S1 未抓到跨站分叉')

    # S2：只把注释里的金改错，代码不动
    s2 = re.sub(r'(金\s*#)[0-9a-fA-F]{6}', r'\g<1>D4A24E', adm_src, count=1)
    if s2 == adm_src:
        bad.append('S2 构造失败：注释里没有「金 #xxxxxx」写法')
    else:
        b2 = check_comment(s2, mt)
        hit2 = any('文档与实现分叉' in x for x in b2)
        print('  [%s] S2 只改注释里的金 -> %s'
              % ('ok' if hit2 else 'X', '被抓到' if hit2 else '没抓到（文档漂移无人守）'))
        if not hit2:
            bad.append('S2 未抓到注释漂移')

    # S4：注释里出现旧值（带 #）不得被当成代码残留
    s4 = adm_src.replace('配色与主站同源',
                         '配色与主站同源（历史值 #D4A24E）', 1)
    if s4 == adm_src:
        bad.append('S4 构造失败：改不动注释')
    else:
        b4 = check_no_stale(s4, parse_root_from(s4))
        hit4 = not any('残留旧值' in x for x in b4)
        print('  [%s] S4 注释里写 #D4A24E -> %s'
              % ('ok' if hit4 else 'X',
                 '不误报（正确）' if hit4 else '被当成代码残留（靠巧合才绿的判据）'))
        if not hit4:
            bad.append('S4 注释里的旧值被误判成代码残留')

    # S3：当前状态不得误报
    b3, _, _ = run_check(main_src, adm_src)
    print('  [%s] S3 当前两站状态 -> %s'
          % ('ok' if not b3 else 'X', '无误报' if not b3 else str(b3)[:70]))
    if b3:
        bad.append('S3 当前状态被误报：%s' % b3[:1])
    return bad


def main():
    for p, nm in ((MAIN_CSS, '主站 main.css'), (ADMIN_HTML, '后台页')):
        if not os.path.exists(p):
            print('RESULT: SKIP  找不到%s（未测不等于通过）' % nm)
            return 0
    main_src = io.open(MAIN_CSS, encoding='utf-8', errors='ignore').read()
    adm_src = io.open(ADMIN_HTML, encoding='utf-8', errors='ignore').read()
    mt = parse_root_from(main_src)
    at = parse_root_from(adm_src)
    if len(mt) < 5 or len(at) < 5:
        print('RESULT: SKIP  令牌解析异常（主站 %d / 后台 %d）' % (len(mt), len(at)))
        return 0

    print('=== 品牌色跨站比对（范围 = 后台注释声明的三项）===')
    for label, mk, ak in PAIRS:
        mv, av = mt.get(mk), at.get(ak)
        print('  %-6s 主站 %-9s 后台 %-9s %s' % (
            label, mv or '缺', av or '缺',
            '一致' if mv and mv == av else '** 分叉 **'))
    print('  （--fg 不在范围内：主站是纸色、后台是暗面板正文色，用途不同，注释也未声明同源）')
    print()
    print('=== 尺子有效性自检 ===')
    bad_self = selftest(main_src, adm_src)
    print()
    if bad_self:
        print('RESULT: FAIL  判据自检不通过，读数不可信：')
        for b in bad_self:
            print('  -', b)
        return 1
    bad, _, _ = run_check(main_src, adm_src)
    if bad:
        print('RESULT: FAIL')
        for b in bad:
            print('  -', b)
        return 1
    print('RESULT: PASS  三项品牌色跨站一致，且自检证明「改代码」与「改注释」两类漂移都能被抓到')
    return 0


if __name__ == '__main__':
    sys.exit(main())
