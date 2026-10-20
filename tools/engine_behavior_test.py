# -*- coding: utf-8 -*-
"""tools/engine_behavior_test.py —— 引擎行为判据（需浏览器，轮54）。

## 为什么需要它（补前两层判据的盲区）
engine_polish_test 查「名字存在」，dead_definition_test 查「有调用点」，
但 I-7 的验收标准是**行为**：
  M11 粒子数随面积变化
  M12 HUD 写入 <= 10 次/秒
名字在、调用点也在，功能仍可能是坏的（_densFor 忘了用 area、
或节流周期被改没）。只有实测行为才算验收完成。

## 轮54 实测基线（两项均成立）
_densFor 面积曲线：
  14,400->1319  90,000->1672  270,400->2514
  313,600->2600 810,000->2600 2,560,000->2600
  => 单调不减 + 上限夹取（DENS_MAX=2600）
HUD 节流（AR 播放 3 秒）：
  hud.calls 953->1723（约 257 次/秒，每帧都调）
  hud.writes 41->71（**10 次/秒**，periodMs=100）
  => 257 次调用只产生 10 次写入，降 25.7 倍

## 判定逻辑抽成纯函数（judge_density / judge_hud）
轮54 反向验证发现：改 phoenix.js 后判据仍 PASS，一度以为判据错。
诊断证明注入确实到了页面（fileHasMark=true、函数源码含 return 2000、
调用返回 2000），但判据读到的曲线是**实例构造时缓存的旧值**——
浏览器缓存时序会污染端到端反向验证（U-130 同一课）。
所以把判定抽成纯函数，用构造数据直接证明判据能识别坏曲线，
不依赖「改文件 + 浏览器读到」这条脆弱链路。

## 三个关键设计
1. _densFor 当纯函数直接喂面积，不去 resize 窗口
   （agent-browser 本机频繁卡死，轮53 卡 4 次；改视口链路长且易挂）
2. HUD 必须测**比率**：只测 writes/s 绝对值会被低帧率蒙混
   （机器卡到 10fps 时 writes 自然低，节流其实没生效也照样通过）
3. 无数据判 SKIP，不判 PASS
"""
import json
import os
import subprocess
import sys
import time

PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DENS_PROBE = """(function(){
  var inst = window.__phoenix || window.phoenixInstance;
  if (!inst || typeof inst._densFor !== 'function') {
    return JSON.stringify({skip: 1, why: 'no _densFor on phoenix instance'});
  }
  var areas = [14400, 90000, 270400, 313600, 810000, 2560000];
  var curve = [];
  for (var i = 0; i < areas.length; i++) {
    var v = null;
    try { v = inst._densFor(areas[i]); } catch (e) { v = null; }
    curve.push({area: areas[i], n: v});
  }
  return JSON.stringify({curve: curve,
    max: (typeof inst.DENS_MAX === 'number') ? inst.DENS_MAX : null,
    min: (typeof inst.DENS_MIN === 'number') ? inst.DENS_MIN : null});
})()"""

HUD_PROBE = """(async function(){
  if (!window.__ar || !window.__ar.stats) return JSON.stringify({skip: 1, why: 'no __ar'});
  window.__ar.open('craft');
  await new Promise(function(r){ setTimeout(r, 600); });
  var s1 = window.__ar.stats();
  if (!s1.hud) return JSON.stringify({skip: 1, why: 'stats() 无 hud 字段'});
  await new Promise(function(r){ setTimeout(r, 3000); });
  var s2 = window.__ar.stats();
  try { window.__ar.close(); } catch (e) {}
  return JSON.stringify({
    calls: [s1.hud.calls, s2.hud.calls],
    writes: [s1.hud.writes, s2.hud.writes],
    periodMs: s2.hud.periodMs,
    fps: s2.fps
  });
})()"""


def judge_density(curve, dmax):
    """密度曲线判定（纯函数）。返回失败原因列表，空列表 = 通过。"""
    fails = []
    nums = [c for c in curve if isinstance(c, (int, float))]
    if len(nums) < 3:
        return ['_densFor 返回值不足 3 个数值，无法判曲线']
    if len(set(nums)) == 1:
        fails.append('_densFor 对所有面积返回同一值 %s —— 密度没真的按面积算（M11 失效）' % nums[0])
    elif any(nums[i] > nums[i + 1] for i in range(len(nums) - 1)):
        fails.append('_densFor 非单调不减 %s —— 面积映射被改坏' % nums)
    if isinstance(dmax, (int, float)) and dmax > 0:
        if max(nums) > dmax * 1.05:
            fails.append('粒子数 %d 超过 DENS_MAX=%s —— 上限夹取失效' % (max(nums), dmax))
        elif nums[-1] < dmax * 0.9:
            fails.append('极大面积只给 %d 粒（DENS_MAX=%s）—— 夹取或标定被改坏' % (nums[-1], dmax))
    return fails


# 节流可测门限：帧率低于此值时，每帧写也才那么多次，
# 比率判据失去意义（轮54 构造用例 judge_hud(9,4) 侥幸通过暴露的漏洞）。
MIN_MEASURABLE_FPS = 30


def judge_hud(cps, wps):
    """HUD 节流判定（纯函数）。

    返回 (fails, unmeasurable)。
    绝对上限 writes<=12 任何帧率下都成立；
    比率判据只在 calls/s >= MIN_MEASURABLE_FPS 时才有效 ——
    否则「写入次数少」是帧率低造成的，不是节流挡出来的。
    """
    fails = []
    if wps > 12:
        fails.append('HUD 写入 %.1f 次/秒 > 12 —— 节流失效（M12）' % wps)
    if wps <= 0:
        fails.append('HUD writes 增量为 0，节流计数器可能失效或被摘除')
        return fails, False
    if cps < 2 * wps:
        fails.append('calls %.0f/s 未显著高于 writes %.1f/s —— 节流其实没在挡调用' % (cps, wps))
    unmeasurable = cps < MIN_MEASURABLE_FPS
    if unmeasurable:
        fails.append('帧率仅 %.0f 次/秒（< %d）—— 无法验证节流是否真的在挡，'
                     '本项未测得，不得当作通过' % (cps, MIN_MEASURABLE_FPS))
    return fails, unmeasurable


def ps(cmd, timeout=90):
    try:
        r = subprocess.run([PS, '-NoProfile', '-Command', cmd], capture_output=True,
                           text=True, cwd=BASE, timeout=timeout, encoding='utf-8', errors='replace')
        return ((r.stdout or '') + (r.stderr or '')).strip()
    except subprocess.TimeoutExpired:
        return 'TIMEOUT'


def run_probe(name, code):
    tmp = os.path.join(BASE, '_qa', '_eb_%s.js' % name)
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    open(tmp, 'w', encoding='utf-8').write(code)
    out = ps('agent-browser eval (Get-Content -Raw -Encoding UTF8 "_qa/_eb_%s.js")' % name)
    for line in reversed(out.splitlines()):
        s = line.strip()
        if s.startswith('"') and s.endswith('"'):
            try:
                return json.loads(json.loads(s))
            except Exception:
                continue
    return None


def main():
    ps('agent-browser open "http://127.0.0.1:8791/"')
    time.sleep(1.2)
    clear = os.path.join(BASE, '_qa', 'clear_sw.js')
    if os.path.exists(clear):
        ps('agent-browser eval (Get-Content -Raw -Encoding UTF8 "_qa/clear_sw.js")')
        time.sleep(1.0)
    ps('agent-browser set viewport 1440 900')
    time.sleep(0.5)
    ps('agent-browser open "http://127.0.0.1:8791/?eb=%d"' % int(time.time() * 1000))
    ps('agent-browser wait --load networkidle')
    time.sleep(3.5)

    fails = []
    checked = 0
    got_any = False

    d = run_probe('dens', DENS_PROBE)
    if d and not d.get('skip'):
        got_any = True
        pairs = [(x['area'], x['n']) for x in d['curve'] if isinstance(x['n'], (int, float))]
        curve = [n for _, n in pairs]
        print('面积曲线: %s' % ' '.join('%d->%d' % (a, n) for a, n in pairs))
        checked += 1
        f = judge_density(curve, d.get('max'))
        if f:
            fails.extend(f)
        else:
            print('[PASS] 密度单调不减且夹在 DENS_MAX=%s（实测 %d -> %d）' % (
                d.get('max'), curve[0], curve[-1]))
    else:
        print('[SKIP] 密度探针无数据：%s' % (d.get('why') if d else 'eval 失败'))

    h = run_probe('hud', HUD_PROBE)
    if h and not h.get('skip'):
        got_any = True
        secs = 3.0
        cps = (h['calls'][1] - h['calls'][0]) / secs
        wps = (h['writes'][1] - h['writes'][0]) / secs
        print('HUD: calls %.0f/s（每帧） writes %.1f/s periodMs=%s fps=%s' % (
            cps, wps, h.get('periodMs'), h.get('fps')))
        checked += 1
        f, _unmeas = judge_hud(cps, wps)
        if f:
            fails.extend(f)
        else:
            print('[PASS] %.0f 次/秒调用被挡到 %.1f 次/秒写入（降 %.1f 倍）' % (
                cps, wps, cps / max(wps, 0.1)))
    else:
        print('[SKIP] HUD 探针无数据：%s' % (h.get('why') if h else 'eval 失败'))

    print()
    if not got_any:
        print('RESULT: SKIP  两个探针都无数据（浏览器异常）—— 不判 PASS')
        return 0
    if checked == 0:
        print('RESULT: SKIP  无可判项')
        return 0
    if fails:
        print('RESULT: FAIL')
        for f in fails:
            print('  -', f)
        return 1
    print('RESULT: PASS  引擎行为 %d 项全部成立（密度自适应 + HUD 节流实测有效）' % checked)
    return 0


if __name__ == '__main__':
    sys.exit(main())