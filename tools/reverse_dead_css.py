# -*- coding: utf-8 -*-
"""反向验证 dead_css_decl_test（轮84 补做 —— 轮59 建判据时漏了这一步）。

## 为什么必须补
一条判据若从没被证明能判红，就等于不知道它是不是哑的。
本轮盘点扫描面时发现判据不剥注释（59 个 selector 带注释残渣），
而重复声明的 key 是 (selector, media, prop) —— 归属错会让真重复**漏报**。
没有反向验证，这个漏报可能已存在 25 轮而无人知。

## 注入方式：不依赖现有锚点
第一版想用 .ar-icon{display:grid;place-items:center} 当锚点 ——
但那条正是轮59 我自己清理掉的（改成了注释），锚点根本不存在。
教训：反向验证不要依赖「某条具体业务规则还在」，
注入**全新的、唯一的选择器**最稳，也不会与真实代码耦合。

## 用例
  A 注入同值重复            -> 必须判红并点名
  B 注入「规则前带注释」的同值重复 -> 必须判红
     （专防注释残渣：不剥注释时 selector 变成 '/* ... */\n.sel'，
       与真声明的 key 不一致，重复检不出来 = 假通过）
  C 注入同属性不同值        -> 不得判红（渐进增强/有意覆盖合法，只 WARN）
  D 未注入                  -> 必须 PASS（排除过度反应）
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)
from tools.safe_mutation import mutate_sandbox

CSS = os.path.join('site', 'assets', 'css', 'main.css')
SEL = '.zz-reverse-probe'
RULE = SEL + '{display:grid;place-items:center}'


def run(sb):
    r = sb.run_python(os.path.join('tools', 'dead_css_decl_test.py'), timeout=90)
    out = (r.stdout or '') + (r.stderr or '')
    res = [l.strip() for l in out.splitlines() if 'RESULT' in l]
    dups = [l.strip() for l in out.splitlines() if l.strip().startswith('- [')]
    return r.returncode, (res[-1] if res else '(无 RESULT)'), dups


def append_css(sb, extra):
    p = sb.path(CSS)
    t = open(p, encoding='utf-8', newline='').read()
    open(p, 'w', encoding='utf-8', newline='').write(t + extra)


bad = []

# D 基线
with mutate_sandbox(require_clean=False) as sb:
    rc, res, _ = run(sb)
    print('[D 未注入] rc=%d %s' % (rc, res[:58]))
    if rc != 0:
        bad.append('D 基线未 PASS（过度反应）')

# A 同值重复
with mutate_sandbox(require_clean=False) as sb:
    append_css(sb, '\n' + RULE + '\n' + RULE + '\n')
    rc, res, dups = run(sb)
    print('[A 同值重复] rc=%d %s' % (rc, res[:58]))
    for d in dups[:2]:
        print('     ', d[:80])
    if not (rc == 1 and any('zz-reverse-probe' in d for d in dups)):
        bad.append('A 同值重复未被抓到')

# B 规则前带注释的同值重复（专防注释残渣导致的假通过）
with mutate_sandbox(require_clean=False) as sb:
    append_css(sb, '\n' + RULE + '\n'
               '/* 轮84 反向验证：注释里也提 display:grid 与 place-items:center */\n'
               + RULE + '\n')
    rc, res, dups = run(sb)
    print('[B 注释+重复] rc=%d %s' % (rc, res[:58]))
    for d in dups[:2]:
        print('     ', d[:80])
    if not (rc == 1 and any('zz-reverse-probe' in d for d in dups)):
        bad.append('B 注释残渣导致漏报（带注释的同值重复未抓到）')

# C 同属性不同值 -> 只 WARN，不判红
with mutate_sandbox(require_clean=False) as sb:
    append_css(sb, '\n' + RULE + '\n' + SEL + '{display:flex}\n')
    rc, res, dups = run(sb)
    print('[C 同属性异值] rc=%d %s' % (rc, res[:58]))
    if rc != 0:
        bad.append('C 异值被误判红（应只 WARN）')

print()
if bad:
    print('RESULT: FAIL  ' + '; '.join(bad))
    sys.exit(1)
print('RESULT: PASS  同值重复能判红（含带注释的），异值不误判，基线不过度反应')
sys.exit(0)
