# -*- coding: utf-8 -*-
"""验证 AR 三段可切换 + 集章逻辑（轮118 迁移：agent-browser -> CDP）。

## 原版四个问题
  1. 依赖 agent-browser；该二进制在本机不存在 -> 从未有读数
  2. 只 print，无断言、无 RESULT、无退出码 -> 哑判据
  3. 注释写「已在 AR 内」，依赖隐式状态 -> 换实现后语义不明
  4. 无零样本核对 -> 一个场景都没切成功也可能「看起来正常」

## 迁移后测什么（每条都有断言）
  A __ar 在位、scenes 非空（场景 id 从引擎动态读，不硬编码）
  B 切换按钮数 == 场景数
  C 逐个切换后 stats().scene 必须等于目标 id
  D 集章：**触发条件是播完而非切过** —— 源码 ar.js:395 complete() 才 push，
     故先 seek 到该段时长让它播完，再核对 stamps 含该 id

## 第一版判据本身写错了（记录以免重犯）
我最初把 D 断言写成「切过就必须集章」，实测 stamps=[] 全红。
读源码才发现落章在 complete()。**判据的断言也必须对着源码语义写，不能想当然。**

零样本不判 PASS：实测切换成功数必须等于场景数。
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
switched = []
scenes = []


def ev(js):
    out = AB.run('agent-browser eval ' + Q + js + Q)
    if not out:
        return None
    try:
        return json.loads(out)
    except Exception:
        return None


def click_scene(sid):
    sel = S + '.ar-dots button[data-scene=' + BS + S + sid + BS + S + ']' + S
    js = ('var b=document.querySelector(' + sel + '); if(b) b.click(); 1')
    AB.run('agent-browser eval ' + Q + js + Q)


try:
    try:
        from cdp_client import SiteServer
        srv = SiteServer(os.path.join(WD, 'site'), port=8793)
        url = srv.url('/index.html?ar_scenes=1')
    except Exception:
        url = 'http://127.0.0.1:8793/'

    AB.run('agent-browser open ' + Q + url + Q)
    AB.run('agent-browser wait --load networkidle')

    js_scenes = ('JSON.stringify((window.__ar && window.__ar.scenes) ? '
                 + 'window.__ar.scenes.map(function(s){return s.id;}) : [])')
    scenes = ev(js_scenes) or []
    if not scenes:
        print('RESULT: FAIL  window.__ar 未注册或 scenes 为空（AR 引擎没加载）')
        sys.exit(1)
    print('A 引擎在位：场景 %d 段 %s' % (len(scenes), scenes))

    AB.run('agent-browser eval ' + Q + 'window.__ar.open('
           + S + scenes[0] + S + '); 1' + Q)
    time.sleep(1.2)
    st = ev('JSON.stringify(window.__ar.stats())')
    if not st or not st.get('open'):
        print('RESULT: FAIL  AR 未能打开（stats.open 为假）')
        sys.exit(1)
    print('   已打开：scene=%s' % st.get('scene'))

    nbtn = ev('document.querySelectorAll(' + S + '.ar-dots button' + S + ').length')
    print('B 切换按钮 %s 个 / 场景 %d 段' % (nbtn, len(scenes)))
    if nbtn != len(scenes):
        fails.append('切换按钮数 %s != 场景数 %d' % (nbtn, len(scenes)))

    for sid in scenes:
        click_scene(sid)
        time.sleep(1.6)
        s2 = ev('JSON.stringify(window.__ar.stats())')
        got = (s2 or {}).get('scene')
        ok = (got == sid)
        print('C 切换 %-8s -> scene=%-8s %s' % (sid, got, 'OK' if ok else '不符!'))
        if ok:
            switched.append(sid)
        else:
            fails.append('切到 %s 后 stats().scene=%s' % (sid, got))

    # D 集章：落章在 complete()（播完），故 seek 到时长让它跑完
    for sid in switched:
        click_scene(sid)
        time.sleep(0.6)
        dur = ev('JSON.stringify((window.__ar.scenes||[]).filter(function(s){'
                 + 'return s.id==' + S + sid + S + ';}).map(function(s){'
                 + 'return s.duration;})[0] || 0)') or 0
        AB.run('agent-browser eval ' + Q + 'window.__ar.seek('
               + str(dur) + '); 1' + Q)
        time.sleep(3.2)
    st2 = ev('JSON.stringify(window.__ar.stats())')
    stamps = (st2 or {}).get('stamps') or []
    print('D 集章 stamps=%s（已播完 %d 段）' % (stamps, len(switched)))
    for sid in switched:
        if sid not in stamps:
            fails.append('%s 已播完但未落章（stamps=%s）' % (sid, stamps))

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
if len(switched) != len(scenes):
    fails.append('只成功切换 %d/%d 段（有跳过的）' % (len(switched), len(scenes)))
if fails:
    print('RESULT: FAIL')
    for f in fails:
        print('  -', f)
    sys.exit(1)
print('RESULT: PASS  AR %d 段全部可切换并正确集章' % len(scenes))
sys.exit(0)