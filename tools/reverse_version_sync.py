# -*- coding: utf-8 -*-
'''反向验证 critical_path_test 的 VERSION_SYNC 判据。'''
import hashlib, sys
sys.path.insert(0, '.')
from tools.safe_mutation import mutate_sandbox

HTML = 'site/index.html'
def sha(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()
before = sha(HTML)

# 破坏：把 HTML BUILD 改成不匹配的值
import re
s = open(HTML, encoding='utf-8').read()
m = re.search(r"var BUILD = '(\d+)';", s)
cur = m.group(1)
bad = str(int(cur) - 1)
print('当前 BUILD=%s，破坏为 %s' % (cur, bad))

with mutate_sandbox(require_clean=False) as sb:
    sb.patch(HTML, [("var BUILD = '%s';" % cur, "var BUILD = '%s';" % bad)])
    r = sb.run_python('tools/critical_path_test.py', timeout=50)
    out = ((r.stdout or '') + (r.stderr or ''))
    print('退出码:', r.returncode)
    for l in out.splitlines():
        if 'RESULT' in l or l.strip().startswith('- '):
            print('  ', l.strip()[:90])

print()
print('真实文件未变:', before == sha(HTML))