# -*- coding: utf-8 -*-
"""反向验证 cjk_punctuation_test 的扫描面真的有牙（轮83 立，轮109 重写）。

## 为什么必须做
扩面只是「把文本纳入扫描」，若正则或抽取路径有缺陷，判据会对那个面永远返回 0 ——
看起来 PASS，实际什么都没测。所以要在沙箱里往每个面注入一个已知违规，
确认判据能抓到并**点名它来自哪个面**。

## 轮109 重写的原因（本文件自己撞上了本仓第 3 次同一课）
后台改静态页时删掉了「访问明细」一节，而本文件的 B 用例硬编码锚点
'<h2>访问明细' —— 直接 AssertionError。同类事故：轮94 reverse_admin_colspan
硬编码表名（tbl-dev 已被拆掉，用例静默测了个空）、轮102 凭记忆写的不存在标识符。
**结论：反向验证脚本不得硬编码它无法保证存在的标识符，一律现场发现。**

## 四个用例（A/B/C 各一个面，D 防过度反应）
  A 后台内联 <script> 里的 HTML 模板串（含嵌套双引号 + 相邻空串，轮83 修过的形态）
  B 后台 HTML 可见文本
  C 主站内联 <script> 里的字符串字面量
  D 不注入任何违规时必须 PASS
每个注入都必须**现场发现落点**，并且注入后断言「确实落在它声称的那个构造里」
（脚本体 or 可见文本）—— 否则又会出现「判红了但测的不是它声称的东西」。
"""
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)
from tools.safe_mutation import mutate_sandbox

ADMIN = os.path.join('site', 'admin', 'index.html')
INDEX = os.path.join('site', 'index.html')
GATE = os.path.join('tools', 'cjk_punctuation_test.py')

SCRIPT_OPEN = re.compile(r'<script\b', re.I)


def in_comment(text, pos):
    """pos 是否落在 HTML 注释里。

    一手事故（轮109）：第一版用 <script(?![^>]*src=) 找内联块，
    而我自己在注释里写了「用 <script src> 而非 fetch」这句说明 ——
    那个 <script src> 没有 = 号，负向断言没排除掉它，注入点于是落进注释，
    判据剥完注释后根本看不见它，A 用例假失败。
    **注释里的字面量不是行为** —— 这条对本仓所有扫描型判据都成立。
    """
    last_open = text.rfind('<!--', 0, pos)
    if last_open < 0:
        return False
    return text.find('-->', last_open) == -1 or text.find('-->', last_open) > pos


def inline_script_positions(text):
    """真正的内联 <script> 开标签位置：不在注释里、且该标签无 src 属性。"""
    out = []
    for m in SCRIPT_OPEN.finditer(text):
        if in_comment(text, m.start()):
            continue
        gt = text.find('>', m.end())
        if gt < 0:
            continue
        tag = text[m.start():gt]
        if 'src' in tag:
            continue
        out.append(gt + 1)
    return out


def run(sb):
    r = sb.run_python(GATE, timeout=120)
    out = (r.stdout or '') + (r.stderr or '')
    res = [l.strip() for l in out.splitlines() if 'RESULT' in l]
    hits = [l.strip() for l in out.splitlines() if l.strip().startswith('- [')]
    return r.returncode, (res[-1] if res else '(无 RESULT)'), hits


def in_inline_script(text, pos):
    """pos 是否落在某个内联脚本体内（复用同一套发现逻辑，不另写一份正则）。"""
    for start in inline_script_positions(text):
        end = text.find('</script>', start)
        if end > 0 and start <= pos <= end:
            return True
    return False


def find_script_injection_point(text, label):
    """现场发现一个内联脚本体的注入落点（取最后一个内联块的开标签之后）。
    不依赖任何函数名/变量名，也不会落到注释里。"""
    hits = inline_script_positions(text)
    assert hits, '%s：文件里找不到真正的内联 <script>，用例前提不成立' % label
    return hits[-1]


def find_visible_anchor(text, label):
    """现场发现一个可见文本锚点：优先 <h2>，退到 <p、再退到 <body>。"""
    for pat in ('<h2>', '<h2 ', '<p>', '<p ', '<body>'):
        i = text.find(pat)
        if i >= 0:
            return i, pat
    raise AssertionError('%s：找不到任何可见文本锚点' % label)


bad = []

# ---------- D 基线：不注入必须 PASS ----------
with mutate_sandbox(require_clean=False) as sb:
    rc, res, hits = run(sb)
    print('[D 未注入] rc=%d %s' % (rc, res[:56]))
    if rc != 0:
        bad.append('D 基线未 PASS（判据过度反应）：%s' % (hits[:1] or ''))

# ---------- A 后台内联脚本的 HTML 模板串 ----------
with mutate_sandbox(require_clean=False) as sb:
    p = sb.path(ADMIN)
    t = open(p, encoding='utf-8', newline='').read()
    at = find_script_injection_point(t, 'A')
    inj = "  var _probe_a = '<td colspan=\"9\">测试甲,违规</td>';\n"
    t2 = t[:at] + inj + t[at:]
    assert in_inline_script(t2, at + 4), 'A：注入点不在内联脚本体内'
    open(p, 'w', encoding='utf-8', newline='').write(t2)
    rc, res, hits = run(sb)
    print('[A 后台内联模板串] rc=%d %s' % (rc, res[:56]))
    for h in hits[:2]:
        print('     ', h[:70])
    if not (rc == 1 and any('测试甲' in h for h in hits)):
        bad.append('A 后台内联模板串里的违规未被抓到（或没点名归属）')

# ---------- B 后台 HTML 可见文本 ----------
with mutate_sandbox(require_clean=False) as sb:
    p = sb.path(ADMIN)
    t = open(p, encoding='utf-8', newline='').read()
    at, pat = find_visible_anchor(t, 'B')
    inj = '<h2>可见文本乙,违规</h2>\n'
    if pat.startswith('<body'):
        inj = '<div>可见文本乙,违规</div>\n'
    t2 = t[:at] + inj + t[at:]
    assert not in_inline_script(t2, at), 'B：注入点落在脚本体内，测的就不是可见文本'
    open(p, 'w', encoding='utf-8', newline='').write(t2)
    rc, res, hits = run(sb)
    print('[B 后台可见文本] rc=%d %s' % (rc, res[:56]))
    for h in hits[:2]:
        print('     ', h[:70])
    if not (rc == 1 and any('可见文本乙' in h for h in hits)):
        bad.append('B 后台可见文本里的违规未被抓到')

# ---------- C 主站内联脚本字面量 ----------
with mutate_sandbox(require_clean=False) as sb:
    p = sb.path(INDEX)
    t = open(p, encoding='utf-8', newline='').read()
    at = find_script_injection_point(t, 'C')
    inj = "var _probe_c = '主站内联丙,违规';\n"
    t2 = t[:at] + inj + t[at:]
    assert in_inline_script(t2, at + 4), 'C：注入点不在内联脚本体内'
    open(p, 'w', encoding='utf-8', newline='').write(t2)
    rc, res, hits = run(sb)
    print('[C 主站内联脚本] rc=%d %s' % (rc, res[:56]))
    for h in hits[:2]:
        print('     ', h[:70])
    if not (rc == 1 and any('主站内联丙' in h for h in hits)):
        bad.append('C 主站内联脚本字面量里的违规未被抓到')

print()
if bad:
    print('RESULT: FAIL  ' + '; '.join(bad))
    sys.exit(1)
print('RESULT: PASS  三个面都能抓到违规且点名归属，未注入时不误报（锚点全部现场发现）')
sys.exit(0)
