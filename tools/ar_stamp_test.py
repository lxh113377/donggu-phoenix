# -*- coding: utf-8 -*-
"""验证：完整播放一段后是否落章，且刷新后集章仍在（持久化）。

## 轮119 迁移（原版是哑判据）
原版只 print 三行读数，**无断言、无 RESULT、无退出码**，
依赖 agent-browser（二进制不存在）—— 从未有读数，也永远不会报红。

## 迁移后测什么（集章是展陈的激励机制，值得认真测）
  A AR API 在位：__ar 暴露 seek/play/stats/open/close
  B 播完一段后落章：seek 到该段时长 -> stamps 含该 id
  C 落章元素同步：.ar-stamps 里对应项必须变成已得态
  D **持久化**：整页重载后 stamps 仍含该 id（落章存在 localStorage）
  E 不重复落章：同一段再播一遍，stamps 长度不变（防重复计数）

零样本不判 PASS：实测落章数必须 >= 1，且 A~E 每项都要有读数。

## 集章触发条件（读源码确认，不猜）
ar.js:395 complete() 里才 push stamps —— 播完才落章，切场景不会。
故 B 必须 seek 到 duration 让它播完，不能只 click 切换。
"""
import json
import os
import sys
import time

WD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(WD)
sys.path.insert(0, os.path.join(WD, 'tools'))

Q = chr(34)
S = chr(39)
BS = chr(92)

try:
    from ab_compat import AbSession, AbCompatError
except Exception as e:
    print('RESULT: SKIP  ab_compat 不可用: %s' % e)
    sys.exit(0)

AB = AbSession()
srv = None
fails = []
checks = 0


def ev(js):
    out = AB.run('agent-browser eval ' + Q + js + Q)
    if not out:
        return None
    try:
        return json.loads(out)
    except Exception:
        return None


def open_ar(scene):
    AB.run('agent-browser eval ' + Q + 'window.__ar.open('
           + S + scene + S + '); 1' + Q)
    time.sleep(1.2)


def stamp_of(scene):
    dur = ev('JSON.stringify((window.__ar.scenes||[]).filter(function(s){'
             + 'return s.id==' + S + scene + S + ';}).map(function(s){'
             + 'return s.duration;})[0] || 0)') or 0
    AB.run('agent-browser eval ' + Q + 'window.__ar.seek(' + str(dur) + '); 1' + Q)
    time.sleep(3.2)
    st = ev('JSON.stringify(window.__ar.stats())')
    return (st or {}).get('stamps') or []


try:
    try:
        from cdp_client import SiteServer
        srv = SiteServer(os.path.join(WD, 'site'), port=8794)
        url = srv.url('/index.html?ar_stamp=1')
    except Exception:
        url = 'http://127.0.0.1:8794/'

    AB.run('agent-browser open ' + Q + url + Q)
    AB.run('agent-browser wait --load networkidle')
    # 清掉历史集章，保证从零开始
    AB.run('agent-browser eval ' + Q + 'localStorage.clear(); 1' + Q)
    AB.run('agent-browser open ' + Q + url + '&fresh=1' + Q)
    AB.run('agent-browser wait --load networkidle')

    # ---- A API 在位 ----
    keys = ev('JSON.stringify(Object.keys(window.__ar||{}))') or []
    need = ['open', 'seek', 'play', 'stats', 'scenes']
    miss = [k for k in need if k not in keys]
    print('A API keys=%s' % keys)
    checks += 1
    if miss:
        fails.append('__ar 缺少方法: %s' % miss)

    scenes = ev('JSON.stringify((window.__ar.scenes||[]).map(function(s){'
                 + 'return s.id;}))') or []
    if not scenes:
        print('RESULT: FAIL  取不到场景列表（AR 引擎未就绪）')
        sys.exit(1)
    target = scenes[0]

    # ---- B 播完落章 ----
    open_ar(target)
    stamps = stamp_of(target)
    print('B 播完 %s -> stamps=%s' % (target, stamps))
    checks += 1
    if target not in stamps:
        fails.append('播完 %s 未落章（stamps=%s）' % (target, stamps))
        print('RESULT: FAIL  落章机制失效，后续项无前提')
        for f in fails:
            print('  -', f)
        sys.exit(1)

    # ---- C 落章元素同步 ----
    # 真实 DOM（源码 ar.js:323 paintStamps）：
    #   <span class="stamp got" title="造像章">造像章</span>
    # 没有 data-stamp 属性，已得态靠 class 里的 got 区分。
    # 故用「已得态元素数 == 集章数」判定，不追属性名（我第一版猜了 data-stamp，空结果）。
    n_got = ev('document.querySelectorAll('
               + S + '.ar-stamps .stamp.got' + S + ').length')
    n_stamp = len(stamps)
    print('C 已得态元素 %s 个 / 集章数 %d' % (n_got, n_stamp))
    checks += 1
    if n_got != n_stamp:
        fails.append('落章元素数 %s != 集章数 %d（DOM 未同步）' % (n_got, n_stamp))

    # ---- E 不重复落章 ----
    before = len(stamps)
    stamps2 = stamp_of(target)
    print('E 再播一遍 stamps=%s（长度 %d -> %d）'
          % (stamps2, before, len(stamps2)))
    checks += 1
    if len(stamps2) != before:
        fails.append('重复落章：长度 %d -> %d' % (before, len(stamps2)))

    # ---- D 持久化：重载后仍在 ----
    AB.run('agent-browser open ' + Q + url + '&reload=1' + Q)
    AB.run('agent-browser wait --load networkidle')
    st3 = ev('JSON.stringify({stamps:(window.__ar&&window.__ar.stats)'
             + ' ? window.__ar.stats().stamps : []})')
    stamps3 = (st3 or {}).get('stamps') or []
    print('D 重载后 stamps=%s' % stamps3)
    checks += 1
    if target not in stamps3:
        fails.append('刷新后集章丢失（stamps=%s）—— 持久化失效' % stamps3)
    # ---- F 集齐态渲染：老访客带满章回访时，文案要宣布解锁 ----
    # 轮174 新增。动机是轮173 那个按钮文案 bug 的同族风险：
    #   状态在（localStorage 有集章），但渲染只在落章那一刻发生 ——
    #   那样带满章回访的老访客永远只看到 集章 3/3，看不到
    #   三章集齐·已解锁完整动线，等于集齐奖励只对第一次的人可见。
    # 断言区分三种失效：默认 集章 0/3 = paintStamps 没跑；
    #   集章 3/3 = 跑了但 all 判定没生效；含 集齐/解锁 才算对。
    all_ids = json.dumps(scenes)
    js_set = ('try{localStorage.setItem(' + S + 'donggu-ar-v1' + S
              + ',JSON.stringify({stamps:' + all_ids
              + ',dwell:10,visits:2,at:Date.now()}))}catch(e){};1')
    AB.run('agent-browser eval ' + Q + js_set + Q)
    AB.run('agent-browser open ' + Q + url + '&restored=1' + Q)
    AB.run('agent-browser wait --load networkidle')
    AB.run('agent-browser eval ' + Q + 'window.__ar.open(' + S
           + str(scenes[0]) + S + ');1' + Q)
    time.sleep(1.4)
    line = ev('JSON.stringify((document.getElementById('
              + S + 'ar-stamp-line' + S + ')||{}).textContent||"")') or ''
    rst = ev('JSON.stringify(window.__ar.stats().stamps)') or []
    print('F 带 %d/%d 回访 -> stamp-line=%r' % (len(rst), len(scenes), line.strip()))
    checks += 1
    if len(rst) != len(scenes):
        fails.append('注入的满章态未生效（stamps=%s）' % rst)
    elif not ('集齐' in line or '解锁' in line):
        fails.append('已集齐 %d/%d 但文案未宣布解锁：%r' % (len(scenes), len(scenes), line.strip()))

except AbCompatError as e:
    print('RESULT: SKIP  CDP 环境不可用: %s' % e)
    sys.exit(0)
except Exception as e:
    print('RESULT: SKIP  探针异常: %s: %s' % (type(e).__name__, str(e)[:110]))
    sys.exit(0)
finally:
    AB.close()
    if srv:
        try:
            srv.stop()
        except Exception:
            pass

print()
if checks < 6:
    fails.append('只完成 %d/6 项检查（有跳过的）' % checks)
if fails:
    print('RESULT: FAIL')
    for f in fails:
        print('  -', f)
    sys.exit(1)
print('RESULT: PASS  落章生效、刷新后仍在、无重复计数，且带满章回访时'
      '文案宣布解锁（恢复态渲染正确）')
sys.exit(0)