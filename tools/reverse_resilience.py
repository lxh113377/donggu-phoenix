# -*- coding: utf-8 -*-
'''反向验证 resilience_test。'''
import hashlib, sys
sys.path.insert(0, '.')
from tools.safe_mutation import mutate_sandbox

HTML = 'site/index.html'
SW = 'site/sw.js'
def sha(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()
b_html, b_sw = sha(HTML), sha(SW)

cases = [
    ('A 删掉 noscript', HTML, '<noscript>', '<!-- removed --><noscript hidden>'),
    ('B 删掉 skipWaiting', SW, 'skipWaiting', '/*removed*/'),
]

for label, path, old, new in cases:
    with mutate_sandbox(require_clean=False) as sb:
        try:
            sb.patch(path, [(old, new)])
        except AssertionError as e:
            print('[%s] 替换失败: %s' % (label, str(e)[:50]))
            continue
        r = sb.run_python('tools/resilience_test.py', timeout=50)
        out = ((r.stdout or '') + (r.stderr or ''))
        fl = [l.strip() for l in out.splitlines() if l.strip().startswith('- ')]
        print('[%s] 退出码=%d' % (label, r.returncode))
        for f in fl[:3]:
            print('    ', f)

print()
print('真实文件未变:', b_html == sha(HTML) and b_sw == sha(SW))