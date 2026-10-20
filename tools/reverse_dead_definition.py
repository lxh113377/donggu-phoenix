# -*- coding: utf-8 -*-
'''反向验证 dead_definition_test（v3）。

## v2 造成的真实事故（务必记住）
finally 里写了 open(PH,'w').write(open(PH).read()) ——
写模式先截断文件，再读时已空，等于把 phoenix.js 清成 0 字节。靠 git checkout 才救回。
教训：绝不用 open(p,'w') 做原地自我改写；要改就先把原文读进内存变量。

## v1 的 A/C 用例为什么没判红（是脚本错，不是判据错）
safe_mutation.patch 内部是 s.replace(old, new, 1)，只替换第一处。
_densFor 有 2 处调用，断开 1 处后另一处仍生效 —— 判据 PASS 是**正确**的。
C 用例的 old 串在定义行里也出现，误伤定义，归因错了。

## 本版做法
在沙箱副本上手工做**全局**替换（真实工作区全程只读，不重复 v2 的事故）。
'''
import hashlib, os, sys
sys.path.insert(0, '.')
from tools.safe_mutation import mutate_sandbox

PH = 'site/assets/js/phoenix.js'
WT = 'site/assets/js/wood-to-statue.js'

def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
b0 = (sha(PH), sha(WT))

# (说明, 文件, 待全局替换串, 替换后串, 期望判据提到的方法名)
cases = [
    ('A 断开 _densFor 全部调用', PH, 'this._densFor(', 'this._densOFF(', '_densFor'),
    ('B 断开 _resampleDensity 唯一调用', PH, 'self._resampleDensity()', 'self._noop()', '_resampleDensity'),
    ('C 断开 _sampleArea 全部调用', PH, 'this._sampleArea()', 'this._noArea()', '_sampleArea'),
    ('D 断开 revealStatue 调用（保留定义）', WT, '    revealStatue(ctx', '    void(ctx', 'revealStatue'),
]

for label, rel, old, new, expect in cases:
    with mutate_sandbox(require_clean=False) as sb:
        p = sb.path(rel)
        txt = open(p, encoding='utf-8', newline='').read()
        if old not in txt:
            print('[%s] 未命中 %r' % (label, old[:34])); continue
        n = txt.count(old)
        open(p, 'w', encoding='utf-8', newline='').write(txt.replace(old, new))
        r = sb.run_python('tools/dead_definition_test.py', timeout=60)
        out = ((r.stdout or '') + (r.stderr or ''))
        res = [l.strip() for l in out.splitlines() if 'RESULT' in l]
        hit = [l.strip() for l in out.splitlines() if expect in l and l.strip().startswith('- ')]
        ok = r.returncode == 1 and bool(hit)
        print('[%s] 断开 %d 处 -> rc=%d %s | %s' % (
            label, n, r.returncode, (res[-1][:34] if res else '(无)'), 'OK' if ok else '**未判红**'))
        for h in hit[:1]:
            print('      ', h[:86])

print()
print('真实工作区未被改动:', b0 == (sha(PH), sha(WT)))