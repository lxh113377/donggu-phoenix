# -*- coding: utf-8 -*-
"""反向验证 reduced_motion_test 的 admin 扫描面（轮76）。

## 要证明的
第 27 行原来只读 main.css。我把扫描面扩到 admin 的 <style>，
但「加了个文件路径」和「真的能扫到那个文件里的样式」是两件事 ——
如果 extract_css 抽不出 <style> 内容，admin 源会静默贡献 0 个动画，
判据照样 PASS，看上去扩了面其实没扩。

## 做法
在沙箱副本里给 admin 注入一个**未覆盖的无限动画**：
  · 若扫描面真的生效 -> 判红并点名 admin
  · 若仍 PASS      -> 扩面是假的（抽样式或源清单有问题）
同时验证反向情形：注入后又在 reduced-motion 块里覆盖它 -> 应转绿，
排除「任何改动都判红」的过度反应。

## 本脚本自身也错过一次（轮76，值得记）
第一版没捕获判据的明细输出行，只看 RESULT 行里有没有 'admin' 字样 ——
但 RESULT 汇总行本来就不含文件名，于是判据明明判对了（rc=1、admin 行显示
「未覆盖 1」）却被我报成「A 未判红」。反向验证脚本自己也是被测对象。
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)
from tools.safe_mutation import mutate_sandbox

ADMIN = os.path.join('site', 'admin', 'index.html')
# 注入锚点：admin 已有的 .dot 无限动画之后（同一条规则族，最贴近真实场景）
ANCHOR = '.dot{width:8px;height:8px;'
INJECT_RULE = '.livedot{width:9px;height:9px;border-radius:50%;background:#0f0;animation:pulse 2s infinite}\n'


def run(sb):
    r = sb.run_python(os.path.join('tools', 'reduced_motion_test.py'), timeout=90)
    out = (r.stdout or '') + (r.stderr or '')
    res = [l.strip() for l in out.splitlines() if 'RESULT' in l]
    # 明细行：源清单行（含 admin 路径与计数）与失败行（含选择器）
    src_line = [l.strip() for l in out.splitlines() if 'site/admin' in l]
    fail_line = [l.strip() for l in out.splitlines() if l.strip().startswith('- ')]
    return (r.returncode, (res[-1] if res else '(无)'),
            (src_line[0] if src_line else ''), '; '.join(fail_line[:2]))


bad = []

# A：注入未覆盖的 admin 无限动画 -> 必须判红并点名 admin
with mutate_sandbox(require_clean=False) as sb:
    p = sb.path(ADMIN)
    t = open(p, encoding='utf-8', newline='').read()
    assert ANCHOR in t, 'admin 注入锚点未找到'
    open(p, 'w', encoding='utf-8', newline='').write(t.replace(
        ANCHOR, INJECT_RULE + ANCHOR, 1))
    rc, res, src, det = run(sb)
    print('[A 注入未覆盖动画] rc=%d %s' % (rc, res[:52]))
    print('   %s' % src[:70])
    print('   明细: %s' % det[:80])
    ok_a = (rc == 1 and '未覆盖 1' in src and 'livedot' in det)
    if not ok_a:
        bad.append('A 未判红/未点名 admin（扩面可能是假的）')

# B：注入并在 reduced-motion 块覆盖 -> 必须转绿
with mutate_sandbox(require_clean=False) as sb:
    p = sb.path(ADMIN)
    t = open(p, encoding='utf-8', newline='').read()
    t2 = t.replace(ANCHOR, INJECT_RULE + ANCHOR, 1)
    # 在 reduced-motion 块里覆盖
    rm_anchor = '.dot{animation:none}'
    assert rm_anchor in t2, 'rm 锚点未找到'
    t2 = t2.replace(rm_anchor, '.dot,.livedot{animation:none}', 1)
    open(p, 'w', encoding='utf-8', newline='').write(t2)
    rc, res, src, det = run(sb)
    print('[B 注入且已覆盖] rc=%d %s' % (rc, res[:52]))
    print('   %s' % src[:70])
    ok_b = rc == 0 and 'PASS' in res
    if not ok_b:
        bad.append('B 已覆盖却仍判红（判据过度反应）')

print()
if bad:
    print('RESULT: FAIL  ' + '; '.join(bad))
    sys.exit(1)
print('RESULT: PASS  admin 扫描面真实生效（未覆盖能判红、已覆盖不误判）')
sys.exit(0)
