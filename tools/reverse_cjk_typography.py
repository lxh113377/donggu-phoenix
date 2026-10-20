# -*- coding: utf-8 -*-
'''反向验证 cjk_typography_test。'''
import hashlib, sys
sys.path.insert(0, '.')
from tools.safe_mutation import mutate_sandbox

CSS = 'site/assets/css/main.css'
HTML = 'site/index.html'
def sha(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()
b_css, b_html = sha(CSS), sha(HTML)

cases = [
    ('A 中文正文用 break-all', CSS,
     'max-width:26em;white-space:pre-line;',
     'max-width:26em;white-space:pre-line;word-break:break-all;'),
    ('B html lang 改成 en', HTML, '<html lang="zh-CN"', '<html lang="en"'),
]

for label, path, old, new in cases:
    with mutate_sandbox(require_clean=False) as sb:
        try:
            sb.patch(path, [(old, new)])
        except AssertionError as e:
            print('[%s] 替换失败: %s' % (label, str(e)[:50]))
            continue
        r = sb.run_python('tools/cjk_typography_test.py', timeout=50)
        out = ((r.stdout or '') + (r.stderr or ''))
        fl = [l.strip() for l in out.splitlines() if l.strip().startswith('- ')]
        print('[%s] 退出码=%d' % (label, r.returncode))
        for f in fl[:2]:
            print('    ', f)

print()
print('真实文件未变:', b_css == sha(CSS) and b_html == sha(HTML))