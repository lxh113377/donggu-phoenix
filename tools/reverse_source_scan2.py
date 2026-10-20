
# -*- coding: utf-8 -*-
"""反向验证：真实代码里的违禁词必须仍被抓到（剥注释不能把真问题也剥掉）。"""
import hashlib, sys
sys.path.insert(0, '.')
from tools.safe_mutation import mutate_sandbox

CSS = 'site/assets/css/main.css'
def sha(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()
before = sha(CSS)

# 在真实 CSS 规则里（非注释）注入违禁色
with mutate_sandbox(require_clean=False) as sb:
    target = sb.path(CSS)
    content = open(target, encoding='utf-8', newline='').read()
    # 找一个真实规则内部插入
    marker = '.hero-tag{'
    i = content.find(marker)
    assert i > 0, 'marker not found'
    content = content[:i] + '.poison-test{color:#667eea}' + chr(10) + content[i:]
    open(target, 'w', encoding='utf-8', newline='').write(content)
    r = sb.run_python('tools/ci_design_static.py', timeout=60)
    out = (r.stdout or '') + (r.stderr or '')
    fails = [l.strip() for l in out.splitlines() if l.strip().startswith('- ')]
    print('[真实代码注入 #667eea] 退出码=%d' % r.returncode)
    print('  结果:', '✓ 抓到（正确）' if r.returncode != 0 else '✗ 漏掉了（严重问题）')
    for f in fails[:2]:
        print('  ', f)

print()
print('真实文件未变:', before == sha(CSS))
