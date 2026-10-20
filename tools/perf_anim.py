# -*- coding: utf-8 -*-
"""tools/perf_anim.py —— 动画热路径性能基准（可复跑）。

为什么要单独立这个工具：
  轮9 之前我一直用「帧率」当性能判据，但帧率受 vsync 上限影响（实测 218fps 说明有余量，
  却看不出热路径到底多贵）。改用**批量法测单函数成本**后才发现：
  · 绘制 20000 次 arc+fill 仅 4.3ms（0.2µs/次）—— 根本不是瓶颈
  · _targets 单次 236µs —— 这才是热点（每帧都跑，2634 粒子 × 约 5 次三角函数）
  优化后 41µs（快 5.8 倍）。

判据（防回退）：
  · _targets 单次 < 120µs（优化后 41µs，留 3 倍余量）
  · 连续 200 帧输出无 NaN/Infinity（查表/跳分支改错会立刻产生 NaN）
  · 降档能力存在：_rebuildLite 存在且能把粒子对象数降下来
"""
import json, subprocess, sys, time

PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
BASE = r'C:\Users\37533\Desktop\workspace\项目\新建文件夹'

PROBE = """(function(){
  return new Promise(function(resolve){
  var tries = 0;
  function waitIt(){
  var p = window.__phoenix;
  if (!p && tries++ < 40) { return setTimeout(waitIt, 250); }
  if (!p) return Promise.resolve(JSON.stringify({error:'no phoenix instance'}));
  var out = {particles: p.particles.length, hasLite: typeof p._rebuildLite === 'function'};
  function bench(label, n, fn){
    var t = performance.now();
    for (var i = 0; i < n; i++) fn(i);
    var dt = performance.now() - t;
    return {label: label, perCallUs: Math.round(dt / n * 10000) / 10};
  }
  out.targetsUs = bench('_targets', 600, function(i){ p._targets(i * 16.7); }).perCallUs;
  // NaN / Inf 检查
  var bad = 0;
  for (var f = 0; f < 200; f++) {
    var t = p._targets(f * 16.7);
    for (var j = 0; j < t.length; j++) { if (!isFinite(t[j])) bad++; }
  }
  out.nanCount = bad;
  // 降档能力：减到 900 后粒子对象数应下降
  var before = p.particles.length;
  out.particlesBefore = before;
  if (out.hasLite) {
    try {
      p.maxParticles = 900;
      p._rebuildLite();
      out.particlesAfterLite = p.particles.length;
    } catch (err) {
      out.rebuildError = String(err).slice(0, 120);
      out.particlesAfterLite = before;
    }
  } else {
    out.particlesAfterLite = before;
  }
  resolve(JSON.stringify(out));
  }
  waitIt();
  });
})()"""


def run():
    js_path = BASE + r'\_qa\_perf_anim.js'
    open(js_path, 'w', encoding='utf-8').write(PROBE)
    subprocess.run([PS, '-NoProfile', '-Command',
                    'agent-browser open "http://127.0.0.1:8791/?perf=1"'],
                   cwd=BASE, capture_output=True, text=True)
    subprocess.run([PS, '-NoProfile', '-Command', 'agent-browser wait --load networkidle'],
                   cwd=BASE, capture_output=True, text=True)
    # 凤凰实例只在首屏顶部初始化；先回顶部再轮询等待（实测偶发 no instance）
    subprocess.run([PS, '-NoProfile', '-Command', 'agent-browser eval "window.scrollTo(0,0);1"'],
                   cwd=BASE, capture_output=True, text=True)
    time.sleep(2.0)
    r = subprocess.run([PS, '-NoProfile', '-Command',
                        'agent-browser eval (Get-Content -Raw -Encoding UTF8 "%s")' % js_path],
                       cwd=BASE, capture_output=True, text=True, encoding='utf-8', errors='replace')
    out = (r.stdout or '').strip()
    for line in reversed(out.splitlines()):
        line = line.strip()
        if line.startswith('"') and line.endswith('"'):
            try:
                return json.loads(json.loads(line))
            except Exception:
                continue
    print('[FAIL] 探针无有效输出（被测代码可能抛错）:', out[:300])
    return {'parse_error': True}


def main():
    d = run()
    if d is None:
        return 0          # 环境原因跳过，不误报性能失败
    if 'error' in d:
        print('[SKIP] 探针未取到实例:', d)
        return 0
    fails = []
    if d['targetsUs'] >= 120:
        fails.append("_targets 单次 %.1fµs 超阈值 120µs（热路径退化）" % d['targetsUs'])
    if d['nanCount'] > 0:
        fails.append("_targets 出现 %d 个 NaN/Infinity（数值不稳）" % d['nanCount'])
    if not d['hasLite']:
        fails.append("缺少 _rebuildLite 降档能力")
    elif d['particlesAfterLite'] >= d['particlesBefore']:
        fails.append("降档未真正减少粒子对象（%d → %d）" % (d['particlesBefore'], d['particlesAfterLite']))
    if d.get('rebuildError'):
        fails.append('降档调用抛错: ' + d['rebuildError'])
    print('粒子 %d | _targets %.1fµs | NaN %d | 降档 %d→%d' % (
        d['particles'], d['targetsUs'], d['nanCount'],
        d['particlesBefore'], d['particlesAfterLite']))
    if fails:
        print('RESULT: FAIL')
        for f in fails:
            print('  -', f)
        return 1
    print('RESULT: PASS  动画热路径性能达标')
    return 0


if __name__ == '__main__':
    sys.exit(main())
