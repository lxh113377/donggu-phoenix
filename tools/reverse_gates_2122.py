
# -*- coding: utf-8 -*-
"""反向验证 gate 21/22（安全沙箱，真实文件零改动）。"""
import hashlib, sys
sys.path.insert(0, '.')
from tools.safe_mutation import mutate_sandbox

def sha(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()
JS = 'site/assets/js/main.js'
CSS = 'site/assets/css/main.css'
b_js, b_css = sha(JS), sha(CSS)

# A: 恢复 line2 + meta.title 的重复拼接
with mutate_sandbox(require_clean=False) as sb:
    js = open(JS, encoding='utf-8').read()
    import re
    m = re.search(r"t\.innerHTML = .*?;", js)
    if m:
        sb.patch(JS, [(m.group(0),
                       "t.innerHTML = C.hero.line2 + '<em>' + C.meta.title + '</em>';")])
        r = sb.run_python('tools/ci_design_static.py', timeout=60)
        hits = [l for l in ((r.stdout or '')+(r.stderr or '')).splitlines() if 'H1' in l or 'RESULT' in l]
        print('[A H1重复]', r.returncode, hits[:2])

# B: 去掉 grid-template-rows 锁行高
with mutate_sandbox(require_clean=False) as sb:
    sb.patch(CSS, [('display:grid;grid-template-rows:100%;grid-template-columns:100%;',
                    'display:grid;')])
    r = sb.run_python('tools/ci_design_static.py', timeout=60)
    hits = [l for l in ((r.stdout or '')+(r.stderr or '')).splitlines() if '商品图' in l or 'RESULT' in l]
    print('[B 未锁行高]', r.returncode, hits[:2])

# C: max-height 改回百分比
with mutate_sandbox(require_clean=False) as sb:
    sb.patch(CSS, [('max-width:100%;max-height:150px;object-fit:contain;',
                    'max-width:100%;max-height:78%;object-fit:contain;')])
    r = sb.run_python('tools/ci_design_static.py', timeout=60)
    hits = [l for l in ((r.stdout or '')+(r.stderr or '')).splitlines() if '商品图' in l or 'RESULT' in l]
    print('[C 百分比max-height]', r.returncode, hits[:2])

print()
print('真实文件未变:', b_js == sha(JS) and b_css == sha(CSS))
