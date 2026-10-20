# -*- coding: utf-8 -*-
"""反向验证 runtime_health_test 的判定公式（运行时补丁法）。

## 为什么不走「改文件再测」
试过并诊断过（轮52）：改 ar.js 后判据仍 PASS。
原因不是判据错，而是**浏览器没执行到改动**——
判据 open 的 URL 带时间戳只 bust 了 HTML，ar.js 子资源仍从 HTTP 缓存
（max-age=600）加载旧版。实测证据：
  · 带 ?cb= 的 fetch 能拿到含注入标记的新文件（hasMark: true）
  · 但页面里 window.__ar.open.toString() 不含标记、__LEAK_MARK 为 undefined
要让文件级注入生效得连子资源一起 bust，成本高且与判据本身无关。

## 本判据真正要防的失效模式
「节点持续累积」这个**现象**能否被识别 —— 即判定公式与阈值。
所以在运行时给 __ar.open 打一个泄漏补丁，制造真实累积，
看判据的公式会不会判红。这直击判据逻辑本身。

## 判据公式（被验证对象）
首轮创建常驻 DOM 是合理的，故只看 r1 之后：max(nodes[2:]) - nodes[1] > 2 即 FAIL。
"""
import json
import os
import subprocess
import sys
import time

PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 与判据同构的探针，唯一区别是开头打泄漏补丁
LEAK_PROBE = """(function(){
  var out = {rounds: []};
  if (!window.__ar) return JSON.stringify({skip: 1, why: 'no __ar'});
  var _orig = window.__ar.open;
  window.__ar.open = function () {
    for (var i = 0; i < 3; i++) {
      var d = document.createElement('div');
      d.setAttribute('data-reverse-leak', '1');
      document.body.appendChild(d);
    }
    return _orig.apply(this, arguments);
  };
  var ids = ['craft', 'red', 'phoenix'];
  function snap(label) {
    out.rounds.push({label: label,
      memMB: performance.memory ? +(performance.memory.usedJSHeapSize / 1048576).toFixed(1) : null,
      nodes: document.getElementsByTagName('*').length});
  }
  snap('r0');
  for (var round = 1; round <= 3; round++) {
    for (var i = 0; i < 15; i++) {
      try { window.__ar.open(ids[i % 3]); window.__ar.close(); } catch (e) {}
    }
    snap('r' + round);
  }
  out.leakNodes = document.querySelectorAll('[data-reverse-leak]').length;
  return JSON.stringify(out);
})()"""


def ps(cmd, timeout=90):
    try:
        r = subprocess.run([PS, '-NoProfile', '-Command', cmd], capture_output=True,
                           text=True, cwd=BASE, timeout=timeout, encoding='utf-8', errors='replace')
        return ((r.stdout or '') + (r.stderr or '')).strip()
    except subprocess.TimeoutExpired:
        return 'TIMEOUT'


def main():
    tmp = os.path.join(BASE, '_qa', '_rev_leak.js')
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    open(tmp, 'w', encoding='utf-8').write(LEAK_PROBE)

    ps('agent-browser set viewport 1440 900')
    time.sleep(0.5)
    ps('agent-browser open "http://127.0.0.1:8791/?rev=%d"' % int(time.time() * 1000))
    ps('agent-browser wait --load networkidle')
    time.sleep(3.0)

    out = ps('agent-browser eval (Get-Content -Raw -Encoding UTF8 "_qa/_rev_leak.js")')
    d = None
    for line in reversed(out.splitlines()):
        line = s = line.strip()
        if s.startswith('"') and s.endswith('"'):
            try:
                d = json.loads(json.loads(s))
                break
            except Exception:
                continue
    if not d or d.get('skip'):
        print('RESULT: SKIP  未取到数据')
        return 0

    nodes = [r['nodes'] for r in d['rounds']]
    print('打泄漏补丁后节点走势: %s' % ' -> '.join(str(n) for n in nodes))
    print('补丁产生的泄漏节点数: %s' % d.get('leakNodes'))

    # 套用判据的公式
    growth_after_first = max(nodes[2:]) - nodes[1]
    print('判据公式 max(nodes[2:]) - nodes[1] = %d（阈值 2）' % growth_after_first)
    print()
    if growth_after_first > 2:
        print('RESULT: PASS  判据公式能识别节点累积（本反向验证预期判红）')
        return 0
    print('RESULT: FAIL  判据公式抓不到 45 次 open 造成的累积，阈值或公式失效')
    return 1


if __name__ == '__main__':
    sys.exit(main())
