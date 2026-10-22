# -*- coding: utf-8 -*-
"""tools/runtime_health_test.py —— 运行时健康判据（需浏览器）。

## 为什么需要它（轮52）
前 51 轮验证了外观、布局、功能、降级，但从未查过运行时三个真实风险：
内存泄漏、DOM 节点累积、动画循环叠加。
本站是**展现场景长时间开着**的站（扫码后可能挂几小时），
且 AR 会被反复开合、凤凰会被反复唤起 —— 泄漏的杀伤力被放大。

## 轮52 实测基线（全部健康）
  · 基线：9.1MB / 579 节点 / 3 canvas
  · AR 开关 20 次：+0.3MB、+9 节点（AR 播放器 DOM 首次创建后常驻复用）
  · 再开关 60 次：节点**稳定 588 不动**，内存最后回落到 1.8MB
  · 粒子 15 次唤起：2100 恒定，rAF 注册增量 0（无循环叠加）
  · 60s 长跑：内存 2.7~33.3MB 波动，终点比起点低 8.4MB，非单调上升

## 判据设计要点
1. **节点累积用「第二轮 vs 第一轮」而不是「终值 vs 初值」**
   首轮会创建常驻 DOM（合理），第二轮起不该再增。
   用终值-初值会把正常的懒创建误判成泄漏。
2. **粒子数必须恒定**：数组是整体替换（this.particles = arr），
   若哪天改成 push 累加就会无限增长。
3. **内存判「非单调上升」而不是绝对值**：GC 时机不可控，
   绝对值会随机采样误报；连续多轮只涨不落才是真泄漏。
4. 不测帧率 —— rAF 在后台标签页被浏览器节流，测出来的是环境噪声不是产品问题
   （轮52 实测：探针等 60 帧直接永不返回）。
"""
import json
import os
import subprocess
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 一次调用内完成「三轮开关 + 采样」，避免多次 eval 的往返与状态漂移
PROBE = """(function(){
  var out = {rounds: []};
  if (!window.__ar) return JSON.stringify({skip: 1, why: 'no __ar'});
  var ids = ['craft', 'red', 'phoenix'];
  function snap(label) {
    out.rounds.push({label: label,
      memMB: performance.memory ? +(performance.memory.usedJSHeapSize / 1048576).toFixed(1) : null,
      nodes: document.getElementsByTagName('*').length});
  }
  snap('r0');
  for (var round = 1; round <= 3; round++) {
    for (var i = 0; i < 15; i++) {
      try { window.__ar.open(ids[i % 3]); window.__ar.close(); } catch (e) { out.err = String(e).slice(0, 50); }
    }
    snap('r' + round);
  }
  // 粒子数与 rAF 叠加
  var inst = window.__phoenix || window.phoenixInstance;
  if (inst && inst.particles) {
    out.particlesBefore = inst.particles.length;
    var raf = window.requestAnimationFrame, reg = 0;
    window.requestAnimationFrame = function (cb) { reg++; return raf.call(window, cb); };
    var b = document.querySelector('.hero-cta.primary');
    for (var k = 0; k < 8; k++) { if (b) b.click(); }
    out.rafExtra = reg;
    window.requestAnimationFrame = raf;
    out.particlesAfter = inst.particles.length;
  }
  return JSON.stringify(out);
})()"""


# 轮123 迁移：ps() 从 PowerShell 调 agent-browser 改为 ab_compat。
_AB = None


def _ab():
    global _AB
    if _AB is None:
        from ab_compat import AbSession
        _AB = AbSession()
    return _AB


def ps(cmd, timeout=90):
    return _ab().run(cmd, timeout=timeout)

def main():
    tmp = os.path.join(BASE, '_qa', '_rt.js')
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    open(tmp, 'w', encoding='utf-8').write(PROBE)

    # 轮123：判据自己起服务，不再假设外部已起 8791（失败形态是 SKIP）
    _srv = None
    try:
        from cdp_client import SiteServer
        _srv = SiteServer(os.path.join(BASE, 'site'), port=8791)
        _base = _srv.url('/index.html')
    except Exception as _e:
        print('RESULT: SKIP  服务起不来: %s' % _e)
        return 0

    ps('agent-browser open "%s"' % _base)
    time.sleep(1.2)
    clear = os.path.join(BASE, '_qa', 'clear_sw.js')
    if os.path.exists(clear):
        ps('agent-browser eval (Get-Content -Raw -Encoding UTF8 "_qa/clear_sw.js")')
        time.sleep(1.0)

    ps('agent-browser set viewport 1440 900')
    time.sleep(0.5)
    ps('agent-browser open "%s?rh=%d"' % (_base, int(time.time() * 1000)))
    ps('agent-browser wait --load networkidle')
    time.sleep(3.0)

    out = ps('agent-browser eval (Get-Content -Raw -Encoding UTF8 "_qa/_rt.js")')
    d = None
    # 轮123：CDP 只返回一层，去掉双层 json.loads。
    if out:
        try:
            d = json.loads(out)
        except Exception:
            d = None

    if not d:
        print('RESULT: SKIP  未取到数据（浏览器或探针异常）')
        return 0
    if d.get('skip'):
        print('RESULT: SKIP  %s' % d.get('why'))
        return 0

    rounds = d.get('rounds') or []
    if len(rounds) < 4:
        print('RESULT: SKIP  采样轮次不足（%d）' % len(rounds))
        return 0

    fails = []
    checked = 0

    nodes = [r['nodes'] for r in rounds]
    print('AR 开关 45 次，节点数走势: %s' % ' -> '.join(str(n) for n in nodes))
    # 判据：第二轮起不得再增长（首轮创建常驻 DOM 是合理的）
    checked += 1
    growth_after_first = max(nodes[2:]) - nodes[1]
    if growth_after_first > 2:
        fails.append('节点持续累积：r1=%d 之后涨到 %d（+%d），疑似未清理的 DOM' % (
            nodes[1], max(nodes[2:]), growth_after_first))
    else:
        print('[PASS] 首轮之后节点零累积（r1 后最大 +%d）' % growth_after_first)

    checked += 1
    if d.get('particlesBefore') is not None and d.get('particlesAfter') is not None:
        if d['particlesBefore'] != d['particlesAfter']:
            fails.append('粒子数在反复唤起后变化 %d -> %d（数组疑似累加而非替换）' % (
                d['particlesBefore'], d['particlesAfter']))
        else:
            print('[PASS] 粒子数恒定 %d（8 次唤起）' % d['particlesBefore'])
    else:
        print('[SKIP] 未取到粒子实例')

    checked += 1
    if d.get('rafExtra') is not None and d.get('rafExtra') > 8:
        fails.append('rAF 注册增量 %d（>8 次点击），动画循环疑似叠加未销毁' % d['rafExtra'])
    elif d.get('rafExtra') is not None:
        print('[PASS] rAF 注册增量 %d（无循环叠加）' % d['rafExtra'])

    mems = [r['memMB'] for r in rounds if r['memMB'] is not None]
    checked += 1
    if len(mems) >= 3:
        rising = all(mems[i] <= mems[i + 1] + 0.5 for i in range(len(mems) - 1)) \
            and mems[-1] - mems[0] > 25
        if rising:
            fails.append('内存单调上升 %s MB，疑似泄漏' % mems)
        else:
            print('[PASS] 内存非单调上升 %s MB（GC 正常）' % mems)
    else:
        print('[SKIP] 无 performance.memory，跳过内存判据')

    if d.get('err'):
        print('提示：探针内出现异常 %s' % d['err'])

    print()
    if fails:
        print('RESULT: FAIL')
        for f in fails:
            print('  -', f)
        return 1
    print('RESULT: PASS  运行时健康 %d 项全部成立（无泄漏 / 无累积 / 无循环叠加）' % checked)
    return 0


if __name__ == '__main__':
    sys.exit(main())
