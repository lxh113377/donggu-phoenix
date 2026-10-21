# -*- coding: utf-8 -*-
"""反向验证 multi_viewport_test：在真实站点 CSS 注入一个越界元素，必须判红。

## 为什么还要做这个
判据自带的自检只证明「内核能识别合成页面里的越界」。
但传输链（占位符、iframe、同源、重试）任何一环坏掉，
都可能让真实站点探针静默返回「无读数 -> SKIP」——
SKIP 看起来不是 FAIL，很容易被当成通过。
所以必须证明：真实站点一旦真有越界，端到端会 FAIL。

## 做法
在 safe_mutation 沙箱副本里给 .hero-tag 加一条
  transform: translateX(400px)
（320 视口下必然越界），跑判据看是否判红。真实工作区只读。
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)
from tools.safe_mutation import mutate_sandbox

CSS = os.path.join('site', 'assets', 'css', 'main.css')

# 注入点：.hero-tag 规则块内追加 transform（不依赖换行，避开 CRLF 坑）
INJECT = 'transform:translateX(400px);'

with mutate_sandbox(require_clean=False) as sb:
    p = sb.path(CSS)
    t = open(p, encoding='utf-8', newline='').read()
    i = t.find('.hero-tag{')
    if i < 0:
        print('RESULT: FAIL  找不到 .hero-tag 注入点')
        sys.exit(1)
    j = t.find('{', i)
    t2 = t[:j + 1] + INJECT + t[j + 1:]
    open(p, 'w', encoding='utf-8', newline='').write(t2)
    r = sb.run_python(os.path.join('tools', 'multi_viewport_test.py'), timeout=180)
    out = (r.stdout or '') + (r.stderr or '')
    res = [l.strip() for l in out.splitlines() if 'RESULT' in l]
    hit = [l.strip() for l in out.splitlines() if l.strip().startswith('- ')]
    print('rc =', r.returncode)
    print(res[-1][:60] if res else '(无 RESULT 行)')
    for h in hit[:3]:
        print('  ', h[:96])
    ok = r.returncode == 1 and 'RESULT: FAIL' in out
    print()
    print('结论:', 'OK 真实站点注入越界后端到端判红'
          if ok else '**未判红：传输链可能静默失效，判据不可信**')
    sys.exit(0 if ok else 1)
