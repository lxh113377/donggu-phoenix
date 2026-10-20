# -*- coding: utf-8 -*-
'''反向验证 originality_audit 能否判红。'''
import hashlib, sys
sys.path.insert(0, '.')
from tools.safe_mutation import mutate_sandbox

CSS = 'site/assets/css/main.css'
def sha(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()
before = sha(CSS)

# 注入 AI 紫渐变（原始判据会检测到）
with mutate_sandbox(require_clean=False) as sb:
    css = open(CSS, encoding='utf-8').read()
    # 找任意位置插入
    broken = css + chr(10) + '.test-ai-purple{background:linear-gradient(90deg,#667eea,#764ba2)}' + chr(10)
    open(sb.path(CSS), 'w', encoding='utf-8', newline='').write(broken)
    r = sb.run_python('tools/originality_audit.py', timeout=50)
    out = ((r.stdout or '') + (r.stderr or ''))
    print('退出码:', r.returncode)
    for l in out.splitlines():
        if 'WARN' in l or 'RESULT' in l or l.strip().startswith('- '):
            print('  ', l.strip()[:80])

print()
print('真实文件未变:', before == sha(CSS))