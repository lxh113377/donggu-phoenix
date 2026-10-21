# -*- coding: utf-8 -*-
"""反向验证 secret_leak_test：重现轮73 的真实泄漏，必须判红。

## 造的不是抽象样本
把轮73 我实际写错的那个文件（带明文 ADMIN_KEY 的同源探针页）
在沙箱副本里重建一份，跑判据看是否抓到。
这比造一个假字符串有意义得多 —— 它验的是「我上次那个错会不会再溜过去」。
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)
from tools.safe_mutation import mutate_sandbox

PROBE = os.path.join('site', '_admin_probe.html')


def run(sb):
    r = sb.run_python(os.path.join('tools', 'secret_leak_test.py'), timeout=90)
    out = (r.stdout or '') + (r.stderr or '')
    res = [l.strip() for l in out.splitlines() if 'RESULT' in l]
    hits = [l.strip() for l in out.splitlines() if l.strip().startswith('- ')]
    return r.returncode, res[-1] if res else '(无)', hits


bad = []

# A：重现轮73 —— 探针页里带真实密钥值
with mutate_sandbox(require_clean=False) as sb:
    kv = {}
    devp = os.path.join(BASE, '.dev.vars')
    if os.path.exists(devp):
        for line in open(devp, encoding='utf-8', errors='ignore'):
            if '=' in line and not line.strip().startswith('#'):
                k, v = line.split('=', 1)
                kv[k.strip()] = v.strip()
    if 'ADMIN_KEY' not in kv:
        print('本机无 .dev.vars，改用长字面量样本验证硬编码分支')
        body = ("<!doctype html><script>var KEY = '8f20a1b2c3d4e5f60718293a4b5c6d7e';"
                "</script>")
    else:
        body = ("<!doctype html><script>var KEY = '%s';</script>" % kv['ADMIN_KEY'])
    open(sb.path(PROBE), 'w', encoding='utf-8').write(body)
    rc, res, hits = run(sb)
    print('[A 探针页含密钥] rc=%d %s' % (rc, res[:56]))
    for h in hits[:2]:
        print('   ', h[:96])
    if rc != 1 or not hits:
        bad.append('A 未被抓到')

# B：只有业务文案，不得误报
with mutate_sandbox(require_clean=False) as sb:
    open(sb.path(os.path.join('site', 'ok_page.html')), 'w', encoding='utf-8').write(
        '<!doctype html><meta name="keywords" content="畲族,凤凰">'
        '<script>var apiKey = get("x");</script>')
    rc, res, hits = run(sb)
    print('[B 正常页面] rc=%d %s' % (rc, res[:56]))
    if rc != 0:
        bad.append('B 误报（正常页面被判红）')

print()
if bad:
    print('RESULT: FAIL  ' + '; '.join(bad))
    sys.exit(1)
print('RESULT: PASS  能抓到轮73 那类真实泄漏，且不误报正常页面')
sys.exit(0)
