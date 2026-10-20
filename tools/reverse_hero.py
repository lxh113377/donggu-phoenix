
# -*- coding: utf-8 -*-
"""反向验证 hero_height_test（安全沙箱，真实文件零改动）。"""
import hashlib, sys
sys.path.insert(0, '.')
from tools.safe_mutation import mutate_sandbox

CSS = 'site/assets/css/main.css'
def sha(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()
before = sha(CSS)

css = open(CSS, encoding='utf-8').read()
# 拿到手机断点里 .hero 那行
import re
m = re.search(r'\.hero\{height:100svh;min-height:100svh;[^}]*\}', css)
hero_line = m.group(0) if m else None
print('找到 .hero 手机规则:', bool(hero_line))

cases = [
    ('A 去掉 height:100svh', [(hero_line, hero_line.replace('height:100svh;', ''))] if hero_line else []),
    ('B .hero-visual 改回固定 min-height',
     [('.hero-visual{min-height:0;height:100%}', '.hero-visual{min-height:58svh;height:100%}')]),
]

for label, patches in cases:
    if not patches:
        print('[%s] 跳过（未找到目标）' % label)
        continue
    with mutate_sandbox(require_clean=False) as sb:
        try:
            sb.patch(CSS, patches)
        except AssertionError as e:
            print('[%s] 替换失败: %s' % (label, str(e)[:80]))
            continue
        r = sb.run_python('tools/hero_height_test.py', timeout=60)
        out = ((r.stdout or '') + (r.stderr or ''))
        print('[%s] 退出码=%d' % (label, r.returncode))
        for l in out.splitlines():
            if 'RESULT' in l or l.strip().startswith('- '):
                print('   ', l.strip())

print()
print('真实 CSS 未变:', before == sha(CSS))
