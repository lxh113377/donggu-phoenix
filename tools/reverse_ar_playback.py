# -*- coding: utf-8 -*-
r"""反向验证 ar_playback_test（轮108）。

## 为什么这条尤其需要
旧版 ar_playback_test 是 34 行探测脚本：agent-browser 二进制不存在、
每次调用抛异常、**退出码恒 0**。也就是说它「绿」了很多轮，
而从没验证过本站的核心功能（AR 展陈）。
新版刚 PASS，必须证明它能在 AR 真坏时报红 —— 否则又是一条哑判据。

## 破坏点打在产品行为上，不打在探针上
  B 注释掉 ar.js:203 的 state.t += dt/1000  -> 播放不再推进
  C 删掉一行 register("red", ...)            -> 有数据但未注册
     （这正是 ar-scenes.js:55 报错文案自己列的故障模式
      「② 新场景忘了 register()」。上一版我猜注册表是
      SCENE_REGISTRY = { ... } 字面量去删 key，实际它是
      Object.create(null) 再由 register() 填充 —— 猜结构会失败）
  D 改掉 global.__ar 赋值                    -> 引擎没加载
若只改探针（比如让探针返回假 stats），判据会变红但那证明不了它能发现产品问题。

## 用例
  A 基线                       -> PASS
  B 播放不推进                 -> FAIL（且点名 t 未推进）
  C 场景未注册                 -> FAIL（点名「有数据但未注册」）
  D __ar 未注册（引擎没加载）  -> FAIL，不得 SKIP/PASS 蒙混
"""
import io
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)
from tools.safe_mutation import mutate_sandbox

GATE = os.path.join('tools', 'ar_playback_test.py')
ARJS = os.path.join('site', 'assets', 'js', 'ar.js')
SCENES = os.path.join('site', 'assets', 'js', 'ar-scenes.js')
DIRS = ('site', 'tools')


def run(sb):
    r = sb.run_python(GATE, timeout=300)
    out = (r.stdout or '') + (r.stderr or '')
    res = [l.strip() for l in out.splitlines() if 'RESULT' in l]
    return r.returncode, (res[-1] if res else '(无 RESULT)'), out


def edit(sb, rel, old, new):
    p = sb.path(rel)
    t = io.open(p, encoding='utf-8', newline='').read()
    assert old in t, '%s 锚点未找到' % rel
    io.open(p, 'w', encoding='utf-8', newline='').write(t.replace(old, new, 1))


bad = []

# A 基线
with mutate_sandbox(require_clean=False, dirs=DIRS) as sb:
    rc, res, out = run(sb)
    print('[A 基线] rc=%d %s' % (rc, res[:64]))
    if rc != 0:
        bad.append('A 基线未 PASS')

# B 播放不推进
with mutate_sandbox(require_clean=False, dirs=DIRS) as sb:
    edit(sb, ARJS, 'state.t += dt / 1000;',
         '/* reverse probe: 故意不推进 */ state.t += 0;')
    rc, res, out = run(sb)
    why = [l.strip() for l in out.splitlines() if '未推进' in l]
    print('[B 播放不推进] rc=%d %s' % (rc, res[:64]))
    for w in why[:2]:
        print('      ', w[:100])
    if not (rc == 1 and why):
        bad.append('B 播放停滞未被抓到（或未点名原因）')

# C 场景未注册（删一行 register，即产品文案自列的故障模式）
with mutate_sandbox(require_clean=False, dirs=DIRS) as sb:
    edit(sb, SCENES, 'register("red", RedScene);',
         '/* reverse probe: 故意漏注册 red */')
    rc, res, out = run(sb)
    why = [l.strip() for l in out.splitlines()
           if '未注册' in l or '不符' in l]
    print('[C 场景未注册] rc=%d %s' % (rc, res[:64]))
    for w in why[:2]:
        print('      ', w[:100])
    if not (rc == 1 and why):
        bad.append('C 场景未注册未被抓到')

# D 引擎未加载
with mutate_sandbox(require_clean=False, dirs=DIRS) as sb:
    edit(sb, ARJS, 'global.__ar = {', 'global.__ar_disabled_probe = {')
    rc, res, out = run(sb)
    print('[D __ar 未注册] rc=%d %s' % (rc, res[:64]))
    if rc == 0:
        bad.append('D 引擎缺失却判 PASS/SKIP（应判 FAIL）')

print()
if bad:
    print('RESULT: FAIL  ' + '; '.join(bad))
    sys.exit(1)
print('RESULT: PASS  播放停滞/漏注册/引擎缺失三种真故障都能判红')
sys.exit(0)
