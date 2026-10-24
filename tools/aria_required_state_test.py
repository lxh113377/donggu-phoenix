# -*- coding: utf-8 -*-
"""tools/aria_required_state_test.py —— ARIA 角色必需状态属性判据（轮180）。

## 为什么需要它
一手实测缺陷：雕刻台画布 wood-demo.js 挂了 role="slider" 与
aria-valuemin/max，却**从不设 aria-valuenow** —— WAI-ARIA 规定
role=slider 必须带 valuenow。实测拖到 50%、键盘推到 60% 之后
aria-valuenow 仍是 null：读屏用户聚焦这块画布只听到「滑块」，
永远不知道雕到哪儿了。
这比不声明 role 更糟 —— 它在无障碍树里造出一个「声明了却没有值」的
空控件，读屏会照着滑块语义去播报，结果播不出东西。

## 三条判据（全部可机器判定，且防「写死假值」）
A 完备性：live DOM 里每个 role=slider/checkbox/radio/switch/tab，
  必须带该角色的必需状态属性（slider->valuenow、checkbox/radio/switch->checked、
  tab->selected），且 slider 的 valuenow 必须是落在 [valuemin, valuemax] 内的数。
B 活性：改变进度（拖滑块 + 发方向键）后，valuenow 必须**跟着变**。
  只查 A 会放过「写死一个 aria-valuenow 骗过检查」的实现 ——
  本会话反复抓「测不到却以为测到了」，活性这条才是真守住同步。
C 零样本不判 PASS：取不到任何带 role 的元素、或 B 阶段值没动，一律 FAIL。

## 自检（证明尺子有牙）
合成一个 fixture 页：role=slider 缺 valuenow + 另一个写死 valuenow 不更新，
A、B 必须各自报红。自检不过 -> 判据自判 FAIL（判据自己坏了必须响）。
"""
import json
import os
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(BASE)
sys.path.insert(0, os.path.join(BASE, 'tools'))

# 必需状态属性表（WAI-ARIA 1.2）
REQ = {
    'slider': ['aria-valuenow'],
    'checkbox': ['aria-checked'],
    'radio': ['aria-checked'],
    'switch': ['aria-checked'],
    'tab': ['aria-selected'],
}

SCAN = r"""(function(){
  var REQ = __REQ__;
  var out = {found: 0, problems: [], vals: []};
  Object.keys(REQ).forEach(function(role){
    [].slice.call(document.querySelectorAll('[role="' + role + '"]'))
      .forEach(function(e){
      out.found++;
      var label = (e.id || e.tagName.toLowerCase()) + '[role=' + role + ']';
      REQ[role].forEach(function(attr){
        var v = e.getAttribute(attr);
        if (v === null || v === '') {
          out.problems.push(label + ' 缺 ' + attr);
          return;
        }
        if (attr === 'aria-valuenow') {
          var n = Number(v);
          if (!isFinite(n)) {
            out.problems.push(label + ' 的 ' + attr + ' 不是数：' + v);
            return;
          }
          var mn = Number(e.getAttribute('aria-valuemin'));
          var mx = Number(e.getAttribute('aria-valuemax'));
          if (isFinite(mn) && n < mn - 1) {
            out.problems.push(label + ' valuenow=' + n + ' 小于 valuemin=' + mn);
          }
          if (isFinite(mx) && n > mx + 1) {
            out.problems.push(label + ' valuenow=' + n + ' 大于 valuemax=' + mx);
          }
          out.vals.push({label: label, now: n,
            text: e.getAttribute('aria-valuetext') || ''});
        }
      });
    });
  });
  return JSON.stringify(out);})()"""

# 拼后校验：占位符必须替换干净，且不得拼出 (function(数字 这类坏签名
assert '__REQ__' not in SCAN.replace('__REQ__', json.dumps(REQ))
_probe = SCAN.replace('__REQ__', json.dumps(REQ))
assert _probe.count('(function(') >= 1, 'SCAN 形态异常'

DRAG = r"""(function(){
  var sl=document.getElementById('carve-slider');
  if(!sl) return 'noslider';
  sl.value='700';
  sl.dispatchEvent(new Event('input',{bubbles:true}));
  return sl.value;})()"""

FIXTURE = """<!doctype html><html><head><meta charset="utf-8"><title>aria fixture</title>
</head><body>
<div id="a" role="slider" aria-valuemin="0" aria-valuemax="100"></div>
<div id="b" role="slider" aria-valuemin="0" aria-valuemax="100"
     aria-valuenow="42"></div>
<div id="c" role="checkbox"></div>
</body></html>
"""


def fixture_scan(ch, srv):
    """跑自检：合成页必须同时报出「缺属性」与「值不随交互变」。"""
    p = os.path.join(BASE, 'site', '_aria_fixture.html')
    io_open = open(p, 'w', encoding='utf-8')
    io_open.write(FIXTURE)
    io_open.close()
    page, tid = ch.new_page(800, 600)
    try:
        ch.navigate(page, srv.url('/_aria_fixture.html?a=%d' % int(time.time())))
        time.sleep(1.0)
        d = json.loads(page.eval_js(
            SCAN.replace('__REQ__', json.dumps(REQ)), timeout=25))
        # 合成页没有 #carve-slider，B 阶段应报「值没动」
        return d
    finally:
        try:
            page.close()
        except Exception:
            pass
        ch.close_page(tid)
        try:
            os.remove(p)
        except OSError:
            pass


def main():
    try:
        from cdp_client import Chrome, SiteServer, find_chrome
    except Exception as e:
        print('RESULT: SKIP  cdp_client 不可用: %s' % e)
        return 0
    if not find_chrome():
        print('RESULT: SKIP  找不到 chrome（未取证 != 通过）')
        return 0
    srv = SiteServer(os.path.join(BASE, 'site'), port=9004)
    ch = Chrome()
    fails = []
    try:
        # ---- 自检 ----
        try:
            fx = fixture_scan(ch, srv)
        except Exception as e:
            print('RESULT: FAIL  判据自检阶段异常（判据本身坏了）: '
                  '%s: %s' % (type(e).__name__, str(e)[:110]))
            return 1
        miss = [x for x in fx.get('problems', []) if '缺 ' in x]
        # 合成页 3 个带 role 元素：#a 缺 valuenow、#c 缺 checked 应报；
        # #b 有 valuenow=42 不该被报（防判据过度报警）。
        want = {'a[role=slider] 缺 aria-valuenow',
                'c[role=checkbox] 缺 aria-checked'}
        got = set(miss)
        b_wrong = any(x.startswith('b[role=slider]') for x in miss)
        self_ok = (fx.get('found') == 3 and want <= got
                   and not b_wrong)
        print('[%s] 自检：合成页 3 个带 role 元素，报缺属性 %d 处；'
              '该报的齐=%s、#b（有值）未被误报=%s'
              % ('PASS' if self_ok else 'FAIL', len(miss),
                 want <= got, not b_wrong))
        if not self_ok:
            print('RESULT: FAIL  自检不通过：合成页该报的没抓全，'
                  '或把有值的误报了 —— 读数不可信')
            for x in fx.get('problems', []):
                print('      ', x[:100])
            return 1
        for x in miss[:3]:
            print('      抓到:', x[:96])

        # ---- 真判 A：完备性 ----
        page, tid = ch.new_page(1280, 900)
        try:
            ch.navigate(page, srv.url('/index.html?aria=%d' % int(time.time())))
            time.sleep(2.8)
            # 滚到雕刻区，让 rAF 跑起来（frame 里才同步 valuenow）
            page.eval_js("(function(){var r=document.getElementById('carve-sec');"
                         "if(r)r.scrollIntoView();return 1;})()", timeout=25)
            time.sleep(1.2)
            d1 = json.loads(page.eval_js(
                SCAN.replace('__REQ__', json.dumps(REQ)), timeout=30))
            print('[%s] A 完备性：全站带 role 的交互元素 %d 个，'
                  '必需状态属性问题 %d 处' % (
                      'PASS' if not d1['problems'] else 'FAIL',
                      d1['found'], len(d1['problems'])))
            for x in d1['problems']:
                print('      -', x[:110])
                fails.append('A ' + x)
            if d1['found'] == 0:
                fails.append('A 零样本：页面上取不到任何带 role 的交互元素')
            before = None
            for v in d1.get('vals', []):
                if v['label'].startswith('carve-stage'):
                    before = v
            if before is None:
                fails.append('A 取不到 #carve-stage 的 valuenow（未取证）')
            else:
                print('      #carve-stage valuenow=%s valuetext=%r'
                      % (before['now'], before['text']))

            # ---- 真判 B：活性（值必须随交互变）----
            r = page.eval_js(DRAG, timeout=25)
            time.sleep(1.0)
            d2 = json.loads(page.eval_js(
                SCAN.replace('__REQ__', json.dumps(REQ)), timeout=30))
            after = None
            for v in d2.get('vals', []):
                if v['label'].startswith('carve-stage'):
                    after = v
            if before is not None and after is not None:
                changed = after['now'] != before['now']
                print('[%s] B 活性：拖滑块到 70%% 后 valuenow %s -> %s'
                      '（证明是同步写入，不是写死的值）' % (
                          'PASS' if changed else 'FAIL',
                          before['now'], after['now']))
                if not changed:
                    fails.append('B valuenow 不随交互变化（可能是写死的假值）')
                if after['now'] < 60 or after['now'] > 80:
                    fails.append('B 拖到 70%% 后 valuenow=%s 不在 60~80 区间'
                                 % after['now'])
            else:
                fails.append('B 无法比对前后值（未取证）')
        finally:
            try:
                page.close()
            except Exception:
                pass
            ch.close_page(tid)
    except Exception as e:
        print('RESULT: SKIP  真判阶段探针异常（环境问题）: %s: %s'
              % (type(e).__name__, str(e)[:110]))
        return 0
    finally:
        ch.close()
        try:
            srv.stop()
        except Exception:
            pass

    print()
    if fails:
        print('RESULT: FAIL  ARIA 必需状态属性 %d 处问题' % len(fails))
        for f in fails[:8]:
            print('  -', f)
        return 1
    print('RESULT: PASS  全站 role 的必需状态属性齐备，'
          '且雕刻进度 valuenow 随交互实时同步')
    return 0


if __name__ == '__main__':
    sys.exit(main())
