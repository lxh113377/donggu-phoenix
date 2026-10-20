# -*- coding: utf-8 -*-
'''反向验证 reduced_motion_test。'''
import hashlib, sys
sys.path.insert(0, '.')
from tools.safe_mutation import mutate_sandbox

CSS = 'site/assets/css/main.css'
def sha(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()
before = sha(CSS)

# 破坏1：把新加的覆盖块删掉
old_block = '''@media (prefers-reduced-motion:reduce){
  #boot .seal::after,
  .btn--primary::after,
  .ar-brand .ar-dot,
  #cam .guide::after{animation:none}
}'''

with mutate_sandbox(require_clean=False) as sb:
    try:
        sb.patch(CSS, [(old_block, '')])
    except AssertionError as e:
        print('[删除覆盖块] 替换失败:', str(e)[:60])
    else:
        r = sb.run_python('tools/reduced_motion_test.py', timeout=50)
        out = ((r.stdout or '') + (r.stderr or ''))
        fl = [l.strip() for l in out.splitlines() if l.strip().startswith('- ')]
        print('[删除覆盖块] 退出码=%d' % r.returncode)
        for f in fl[:4]:
            print('   ', f)

# 破坏2：新增一个未覆盖的无限动画
with mutate_sandbox(require_clean=False) as sb2:
    sb2.patch(CSS, [('.scroll-hint::after{',
                    '.ghost-anim::after{animation:spin 2s linear infinite}' + chr(10) + '.scroll-hint::after{')])
    r2 = sb2.run_python('tools/reduced_motion_test.py', timeout=50)
    out2 = ((r2.stdout or '') + (r2.stderr or ''))
    fl2 = [l.strip() for l in out2.splitlines() if l.strip().startswith('- ')]
    print('[新增未覆盖动画] 退出码=%d' % r2.returncode)
    for f in fl2[:2]:
        print('   ', f)

print()
print('真实文件未变:', before == sha(CSS))