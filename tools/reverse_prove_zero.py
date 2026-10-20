
# -*- coding: utf-8 -*-
"""验证两个工具面对零样本时判 SKIP（沙箱内，真实文件零改动）。"""
import hashlib, sys
sys.path.insert(0, '.')
from tools.safe_mutation import mutate_sandbox

CSS = 'site/assets/css/main.css'
def sha(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()
before = sha(CSS)

# 把所有 backdrop-filter 从 CSS 里删掉 → prove 工具应报 SKIP
with mutate_sandbox(require_clean=False) as sb:
    import re
    p = sb.path(CSS)
    content = open(p, encoding='utf-8', newline='').read()
    content2 = re.sub(r'\s*backdrop-filter\s*:\s*[^;}]+;?', '', content)
    content2 = re.sub(r'\s*-webkit-backdrop-filter\s*:\s*[^;}]+;?', '', content2)
    open(p, 'w', encoding='utf-8', newline='').write(content2)
    r = sb.run_python('tools/prove_no_visual_change.py', timeout=60)
    out = ((r.stdout or '') + (r.stderr or '')).strip()
    print('[prove 零样本] 退出码=%d' % r.returncode)
    for l in out.splitlines()[-4:]:
        if l.strip():
            print('   ', l.strip())

print()
print('真实 CSS 未变:', before == sha(CSS))
