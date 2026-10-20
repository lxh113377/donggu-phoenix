# -*- coding: utf-8 -*-
"""反向验证出处渲染门禁（沙箱）。"""
import hashlib, re, sys
sys.path.insert(0, '.')
from tools.safe_mutation import mutate_sandbox

JS = 'site/assets/js/ar.js'
def sha(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()
before = sha(JS)

with mutate_sandbox(require_clean=False) as sb:
    js = open(JS, encoding='utf-8').read()
    m = re.search(r'      var extra = "";.*?\n      \}', js, re.S)
    if not m:
        print('未能定位 extra 块')
    else:
        plain = ('      var extra = s.sources && s.sources.length ? '
                 '"<span class=\'kick\'>素材出处 " + s.sources.length + " 条</span>" : "";')
        sb.patch(JS, [(m.group(0), plain)])
        r = sb.run_python('tools/ci_design_static.py', timeout=60)
        out = ((r.stdout or '') + (r.stderr or ''))
        print('退出码:', r.returncode)
        for l in out.splitlines():
            if '出处' in l or 'RESULT' in l or l.strip().startswith('- '):
                print('  ', l.strip())

print()
print('真实文件未变:', before == sha(JS))