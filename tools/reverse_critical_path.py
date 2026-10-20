# -*- coding: utf-8 -*-
'''反向验证 critical_path_test。'''
import hashlib, sys
sys.path.insert(0, '.')
from tools.safe_mutation import mutate_sandbox

HTML = 'site/index.html'
def sha(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()
before = sha(HTML)

cases = [
    ('A 去掉 main.js 的 defer', '<script src="assets/js/main.js" defer></script>', '<script src="assets/js/main.js"></script>'),
    ('B 去掉 phoenix.js 的 defer', '<script src="assets/js/phoenix.js" defer></script>', '<script src="assets/js/phoenix.js"></script>'),
]

for label, old, new in cases:
    with mutate_sandbox(require_clean=False) as sb:
        try:
            sb.patch(HTML, [(old, new)])
        except AssertionError as e:
            print('[%s] 替换失败: %s' % (label, str(e)[:50]))
            continue
        r = sb.run_python('tools/critical_path_test.py', timeout=50)
        out = ((r.stdout or '') + (r.stderr or ''))
        fl = [l.strip() for l in out.splitlines() if l.strip().startswith('- ')]
        print('[%s] 退出码=%d' % (label, r.returncode))
        for f in fl[:2]:
            print('    ', f)

print()
print('真实文件未变:', before == sha(HTML))