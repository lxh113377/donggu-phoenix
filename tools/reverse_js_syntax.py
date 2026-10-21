# -*- coding: utf-8 -*-
"""反向验证 js_syntax_test（轮96）。

判据若从没被证明能判红，就等于不知道它是不是哑的 —— 尤其这条是为
「JS 全坏而 CI 全绿」的缺口新建的，必须证明它真能堵。

## 两处实现要点（都是本轮踩出来的）
1. **注入用追加，不用锚点**。第一版想用 'function boot()' 当锚点，
   但那是凭记忆写的标识符（本会话第 N 次同类错误），实际不存在。
   往文件末尾追加一段必然语法错的代码，不依赖任何既有内容，
   且与真实代码零耦合。
2. **沙箱要显式带上 functions/**。mutate_sandbox 默认 dirs=('site','tools')，
   不含云函数 —— 于是第一次跑只扫到 8 个 JS，用例 C 根本无从注入。
   扫描面含后端是这条判据的意义所在，沙箱必须跟上。

## 用例
  A site/assets/js/main.js 追加坏码   -> 判红并点名
  B site/sw.js 追加坏码               -> 判红（离线缓存脚本也在面上）
  C functions 云函数追加坏码          -> 判红（证明扫描面含后端）
  D 未注入                            -> PASS（排除过度反应）
  E 新增合法 CJS 文件                 -> 不得判红（双模式回退有效）
  F 八进制字面量（ESM 非法、CJS 合法） -> 必须判 ok，证明回退分支真被走到
"""
import io
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)
from tools.safe_mutation import mutate_sandbox

DIRS = ('site', 'tools', 'functions')
# 追加即坏：裸记号不成句，module 与 script 两种解析都会报 SyntaxError
BROKEN = "\nvar __reverse_probe = ;( ) { ]\n"


def run(sb):
    r = sb.run_python(os.path.join('tools', 'js_syntax_test.py'), timeout=180)
    out = (r.stdout or '') + (r.stderr or '')
    res = [l.strip() for l in out.splitlines() if 'RESULT' in l]
    bad = [l.strip() for l in out.splitlines() if l.strip().startswith('- ')]
    n = [l for l in out.splitlines() if '受检 JS' in l]
    return r.returncode, (res[-1] if res else '(无 RESULT)'), bad, (n[0] if n else '')


def append_broken(sb, rel):
    p = sb.path(rel)
    with io.open(p, 'a', encoding='utf-8', newline='') as fh:
        fh.write(BROKEN)


bad = []

# D 基线（同时确认扫描面含 functions）
with mutate_sandbox(require_clean=False, dirs=DIRS) as sb:
    rc, res, _bl, cnt = run(sb)
    print('[D 未注入] %s | rc=%d %s' % (cnt.strip()[:24], rc, res[:52]))
    if rc != 0:
        bad.append('D 基线未 PASS（过度反应）')
    if 'functions' not in str(sb.run_python(
            os.path.join('tools', 'js_syntax_test.py'), timeout=180).stdout):
        bad.append('D 扫描面不含 functions（沙箱 dirs 未生效）')

# A main.js
with mutate_sandbox(require_clean=False, dirs=DIRS) as sb:
    append_broken(sb, os.path.join('site', 'assets', 'js', 'main.js'))
    rc, res, bl, _c = run(sb)
    named = [l for l in bl if 'main.js' in l]
    print('[A main.js 追加坏码] rc=%d %s' % (rc, res[:52]))
    for l in named[:1]:
        print('     ', l[:96])
    if not (rc == 1 and named):
        bad.append('A main.js 语法错未被抓到或未点名')

# B sw.js
with mutate_sandbox(require_clean=False, dirs=DIRS) as sb:
    append_broken(sb, os.path.join('site', 'sw.js'))
    rc, res, bl, _c = run(sb)
    named = [l for l in bl if 'sw.js' in l]
    print('[B sw.js 追加坏码] rc=%d %s' % (rc, res[:52]))
    for l in named[:1]:
        print('     ', l[:96])
    if not (rc == 1 and named):
        bad.append('B sw.js 语法错未被抓到')

# C 云函数
with mutate_sandbox(require_clean=False, dirs=DIRS) as sb:
    append_broken(sb, os.path.join('functions', 'api', 'admin', 'overview.js'))
    rc, res, bl, _c = run(sb)
    named = [l for l in bl if 'overview.js' in l]
    print('[C 云函数追加坏码] rc=%d %s' % (rc, res[:52]))
    for l in named[:1]:
        print('     ', l[:96])
    if not (rc == 1 and named):
        bad.append('C functions 语法错未被抓到（扫描面未含后端）')

# E 合法 CJS 不得误伤
with mutate_sandbox(require_clean=False, dirs=DIRS) as sb:
    p = sb.path(os.path.join('site', 'assets', 'js', 'cjs_probe.js'))
    io.open(p, 'w', encoding='utf-8', newline='').write(
        "var legacy = {a: 1};\n"
        "module.exports = legacy;\n"
        "function useIt(x) { return x.a + 1; }\n"
        "if (typeof window !== 'undefined') { window.__legacy = legacy; }\n")
    rc, res, bl, _c = run(sb)
    fp = [l for l in bl if 'cjs_probe' in l]
    print('[E 合法 CJS] rc=%d %s' % (rc, res[:52]))
    for l in fp[:1]:
        print('     ', l[:96])
    if rc != 0 or fp:
        bad.append('E 合法 CJS 被误判（双模式回退未生效）')

# F 覆盖 commonjs 回退分支（轮96：该分支曾因参数写错而成为空壳）
with mutate_sandbox(require_clean=False, dirs=DIRS) as sb:
    p = sb.path(os.path.join('site', 'assets', 'js', 'cjs_octal_probe.js'))
    io.open(p, 'w', encoding='utf-8', newline='').write(
        "var mode = 0755;\n"
        "if (typeof window !== 'undefined') { window.__mode = mode; }\n")
    rc, res, bl, cnt = run(sb)
    fp = [l for l in bl if 'cjs_octal_probe' in l]
    print('[F 八进制字面量 走 commonjs] rc=%d %s' % (rc, res[:48]))
    for l in fp[:1]:
        print('     ', l[:96])
    if rc != 0 or fp:
        bad.append('F 回退分支未生效（ESM 严格模式拒八进制，'
                   '只有 commonjs 能过；判红说明第二模式是空壳）')

print()
if bad:
    print('RESULT: FAIL  ' + '; '.join(bad))
    sys.exit(1)
print('RESULT: PASS  站点/后端 JS 语法错都能判红点名，合法 CJS 不误伤')
sys.exit(0)
