
# -*- coding: utf-8 -*-
"""关键验证：让两个工具面对「零样本」，必须报 SKIP 而非 PASS。"""
import hashlib, sys
sys.path.insert(0, '.')
from tools.safe_mutation import mutate_sandbox

def sha(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()

# --- A: dead_data_test 面对空数据文件 ---
DATA = 'site/assets/data/culture.js'
b = sha(DATA)
with mutate_sandbox(require_clean=False) as sb:
    # 把整个文件替换成一个没有字段的壳
    open(sb.path(DATA), 'w', encoding='utf-8').write('window.CULTURE = {};\n')
    r = sb.run_python('tools/dead_data_test.py', timeout=60)
    out = ((r.stdout or '') + (r.stderr or '')).strip()
    print('[A dead_data 空数据] 退出码=%d' % r.returncode)
    for l in out.splitlines()[-3:]:
        print('   ', l.strip())
print('   真实文件未变:', b == sha(DATA))

# --- B: ring_containment 面对缺失选择器 ---
CSS = 'site/assets/css/main.css'
b2 = sha(CSS)
with mutate_sandbox(require_clean=False) as sb:
    sb.patch(CSS, [
        ('.hero-ring{', '.renamed-hero-ring{'),
        ('.hero-ring.b{', '.renamed-hero-ring-b{'),
        ('.totem-ring{', '.renamed-totem-ring{'),
        ('.totem-ring.b{', '.renamed-totem-ring-b{'),
    ])
    r = sb.run_python('tools/ring_containment_test.py', timeout=60)
    out = ((r.stdout or '') + (r.stderr or '')).strip()
    print()
    print('[B ring 选择器缺失] 退出码=%d' % r.returncode)
    for l in out.splitlines()[-3:]:
        print('   ', l.strip())
print('   真实文件未变:', b2 == sha(CSS))
