# -*- coding: utf-8 -*-
"""反向验证 dead_data_test（沙箱）。"""
import hashlib, sys
sys.path.insert(0, '.')
from tools.safe_mutation import mutate_sandbox

DATA = 'site/assets/data/culture.js'
def sha(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()
before = sha(DATA)

# 注入一个绝不会被前端引用的字段
with mutate_sandbox(require_clean=False) as sb:
    sb.patch(DATA, [("  meta: {", "  meta: {" + chr(10) + "    ghostFieldXyz: 'never used',")])
    r = sb.run_python('tools/dead_data_test.py', timeout=60)
    out = ((r.stdout or '') + (r.stderr or ''))
    print('退出码:', r.returncode)
    for l in out.splitlines():
        if 'RESULT' in l or l.strip().startswith('- ') or '检查' in l:
            print('  ', l.strip())

print()
print('真实文件未变:', before == sha(DATA))