
# -*- coding: utf-8 -*-
"""验证：注释里写入「违禁词」时，判据不应误报。

这是本轮的核心验证 —— 证明统一扫描层真的堵住了系统性风险。
用 safe_mutation 沙箱，真实文件零改动。
"""
import hashlib, sys
sys.path.insert(0, '.')
from tools.safe_mutation import mutate_sandbox

CSS = 'site/assets/css/main.css'
HTML = 'site/index.html'
def sha(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()
b_css, b_html = sha(CSS), sha(HTML)

POISON_CSS = '/* 这里故意写 tailwind bootstrap @apply #667eea #764ba2 测试注释隔离 */'
POISON_HTML = '<!-- 这里故意写 fonts.googleapis.com Inter Roboto 测试注释隔离 -->'

cases = [
    ('CSS 注释注入违禁词', CSS, ('\n', POISON_CSS + chr(10)), 'tools/ci_design_static.py', 'ci_design_static'),
    ('HTML 注释注入违禁词', HTML, ('\n', POISON_HTML + chr(10)), 'tools/ci_design_static.py', 'ci_design_static'),
]

for label, path, (anchor, poison), script, tag in cases:
    with mutate_sandbox(require_clean=False) as sb:
        target = sb.path(path)
        content = open(target, encoding='utf-8', newline='').read()
        open(target, 'w', encoding='utf-8', newline='').write(poison + content)
        r = sb.run_python(script, timeout=60)
        out = (r.stdout or '') + (r.stderr or '')
        fails = [l.strip() for l in out.splitlines() if l.strip().startswith('- ')]
        print('[%s] 退出码=%d' % (label, r.returncode))
        if r.returncode == 0:
            print('   ✓ 未误报（注释被正确忽略）')
        else:
            print('   ✗ 误报:', fails[:2])

print()
print('真实文件未变:', b_css == sha(CSS) and b_html == sha(HTML))
