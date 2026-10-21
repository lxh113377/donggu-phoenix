# -*- coding: utf-8 -*-
"""反向验证 admin_responsive_test：撤掉触控基线，必须判红。

## 为什么必须做
这条判据 PASS 只说明「现在没测出问题」。它能不能测出问题，
要靠故意造一个已知缺陷来证明 —— 否则它可能是哑的（轮67 的 touch_target
就是活例：阈值用错 20 轮没人发现，且依赖死 daemon 从没产出过读数）。

## 破坏方式
在 safe_mutation 沙箱副本里把 .btn 与 select 的 min-height:44px 撤掉，
还原成轮79 实测到的缺陷态（.btn 38px / select 31px）。
判据必须：rc=1、点名 .btn 或 select、给出 < 44px 的具体尺寸。
真实工作区只读。

## 沙箱必须自带 .dev.vars（轮79 踩到，与轮58 同族）
safe_mutation 复制的是 git 跟踪面，而 .dev.vars 被 gitignore ——
副本里没有它，判据会直接 SKIP「读不到 ADMIN_KEY」。
SKIP 不是 FAIL：如果不把密钥文件带进沙箱，反向验证会永远测不到真链路，
误以为判据是哑的。修法是把 .dev.vars 复制进沙箱根。
"""
import os
import shutil
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)
from tools.safe_mutation import mutate_sandbox

ADMIN = os.path.join('site', 'admin', 'index.html')
DEVVARS = os.path.join(BASE, '.dev.vars')

CASES = [
    ('A 撤 .btn 基线', 'padding:7px 14px;min-height:44px;', 'padding:7px 14px;'),
    ('B 撤 select 基线', 'outline:none;min-height:44px;line-height:1.4;', 'outline:none;'),
]


def run(sb):
    r = sb.run_python(os.path.join('tools', 'admin_responsive_test.py'), timeout=220)
    out = (r.stdout or '') + (r.stderr or '')
    res = [l.strip() for l in out.splitlines() if 'RESULT' in l]
    hits = [l.strip() for l in out.splitlines() if l.strip().startswith('- ')]
    return r.returncode, (res[-1] if res else '(无 RESULT)'), hits


if not os.path.exists(DEVVARS):
    print('RESULT: SKIP  本机无 .dev.vars，无法让沙箱内的判据登录')
    sys.exit(0)

bad = []
try:
    for label, old, new in CASES:
        with mutate_sandbox(require_clean=False) as sb:
            # 把密钥带进沙箱（副本是临时目录，跑完即删）
            shutil.copy(DEVVARS, os.path.join(sb.root, '.dev.vars'))
            p = sb.path(ADMIN)
            t = open(p, encoding='utf-8', newline='').read()
            if old not in t:
                print('[%s] 锚点不存在（改法可能已变）' % label)
                bad.append(label)
                continue
            open(p, 'w', encoding='utf-8', newline='').write(t.replace(old, new, 1))
            rc, res, hits = run(sb)
            named = [h for h in hits if ('btn' in h or 'select' in h)]
            print('[%s] rc=%d %s' % (label, rc, res[:56]))
            for h in named[:2]:
                print('      %s' % h[:88])
            if not (rc == 1 and 'FAIL' in res and named):
                bad.append(label)
except Exception as e:
    print('执行异常: %s' % e)
    bad.append('exception')

print()
if bad:
    print('RESULT: FAIL  未被抓到: %s' % ', '.join(bad))
    sys.exit(1)
print('RESULT: PASS  撤掉任一触控基线都能判红并点名元素')
sys.exit(0)
