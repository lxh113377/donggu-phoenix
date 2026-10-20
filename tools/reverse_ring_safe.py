
# -*- coding: utf-8 -*-
"""反向验证 ring 门禁 —— 全程在 safe_mutation 副本里，真实工作区零污染。"""
import hashlib, sys
sys.path.insert(0, '.')
from tools.safe_mutation import mutate_sandbox

CSS = 'site/assets/css/main.css'
def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()

real_before = sha(CSS)
css_text = open(CSS, encoding='utf-8').read()

cases = [
    ('A 负 inset', [(css_text[css_text.index('.totem-ring.b{'):css_text.index('}', css_text.index('.totem-ring.b{'))+1],
                    '.totem-ring.b{inset:-5%;border-style:dashed;opacity:.5;animation-delay:-1.4s}')]),
    ('B 超宽 width', [('width:min(66%,420px);transform:translate(-50%,-50%) scale(1.10);',
                       'width:min(100%,560px);')]),
    ('C keyframes 丢 scale', [('@keyframes slowSpin{from{transform:translate(-50%,-50%) scale(1.10) rotate(0)}to{transform:translate(-50%,-50%) scale(1.10) rotate(360deg)}}',
                              '@keyframes slowSpin{from{transform:translate(-50%,-50%) rotate(0)}to{transform:translate(-50%,-50%) rotate(360deg)}}')]),
]

for label, patches in cases:
    try:
        with mutate_sandbox(require_clean=False) as sb:
            sb.patch(CSS, patches)
            r = sb.run_python('tools/ring_containment_test.py', timeout=60)
            out = ((r.stdout or '') + (r.stderr or '')).strip()
            verdict = [l.strip() for l in out.splitlines() if 'RESULT' in l or l.startswith('  -')]
            print('[%s] 退出码=%d' % (label, r.returncode))
            for v in verdict[:2]:
                print('   ', v)
    except Exception as e:
        print('[%s] 异常: %s' % (label, str(e)[:100]))

real_after = sha(CSS)
print()
print('真实 CSS 未变:', real_before == real_after)
