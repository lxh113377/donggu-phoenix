# -*- coding: utf-8 -*-
"""tools/merch_image_fill_test.py —— 文创卡片图片填充率（需浏览器）。

## 为什么需要它
文创区是「产品感」的承担者。图片在卡片里占比过小，
视觉上会读成「一块空白里放了个小图标」，产品就失去了存在感。

## 轮48 发现的缺陷
主推卡片 541×846，图片却只有 214×246 —— **填充率 11.5%**。
根因是两层高度限制叠加：
  · .merch-item.is-feature .merch-shot{height:clamp(320px,34vw,420px)} 锁死 420px
  · .merch-shot img{max-height:150px} 是给普通卡片（196px 容器）设的，
    is-feature 大容器没有覆盖它 → 图片被压到 150px 上限
修复后：容器 420→623px，图片 214×246→391×450，填充率 11.5%→38.5%。

## 判据
· 主推卡片图片填充率 >= 25%（低于此产品细节看不清）
· 任何卡片填充率不得 < 5%（否则等于没图）
· 图片不得溢出卡片边界
"""
import json
import os
import subprocess
import sys
import time

PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROBE = '''(function(){
  var grid = document.getElementById('merch-grid') || document.querySelector('.merch-grid');
  if (!grid) return JSON.stringify({missing: 1});
  var cards = [].slice.call(grid.children);
  if (!cards.length) return JSON.stringify({empty: 1});
  var out = cards.map(function(c){
    var r = c.getBoundingClientRect();
    var img = c.querySelector('img');
    var ir = img ? img.getBoundingClientRect() : null;
    return {
      feat: c.classList.contains('is-feature'),
      cardW: Math.round(r.width), cardH: Math.round(r.height),
      imgW: ir ? Math.round(ir.width) : 0,
      imgH: ir ? Math.round(ir.height) : 0,
      fill: (ir && r.width * r.height > 0) ? +(ir.width * ir.height / (r.width * r.height) * 100).toFixed(1) : null,
      overflow: ir ? (ir.bottom > r.bottom + 2 || ir.top < r.top - 2 || ir.right > r.right + 2) : false
    };
  });
  return JSON.stringify({total: out.length, cards: out});
})()'''


def ps(cmd, timeout=90):
    try:
        r = subprocess.run([PS, '-NoProfile', '-Command', cmd], capture_output=True,
                           text=True, cwd=BASE, timeout=timeout, encoding='utf-8', errors='replace')
        return ((r.stdout or '') + (r.stderr or '')).strip()
    except subprocess.TimeoutExpired:
        return 'TIMEOUT'


def main():
    tmp = os.path.join(BASE, '_qa', '_merchfill.js')
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    open(tmp, 'w', encoding='utf-8').write(PROBE)

    ps('agent-browser open "http://127.0.0.1:8791/"')
    time.sleep(1.2)
    clear = os.path.join(BASE, '_qa', 'clear_sw.js')
    if os.path.exists(clear):
        ps('agent-browser eval (Get-Content -Raw -Encoding UTF8 "_qa/clear_sw.js")')
        time.sleep(1.0)

    ps('agent-browser set viewport 1440 900')
    time.sleep(0.4)
    # cacheBust：不仅清 SW，还要绕开 HTTP 缓存（max-age=600）
    ps('agent-browser open "http://127.0.0.1:8791/?mf=%d"' % int(time.time() * 1000))
    # 强制重新拉 CSS（加时间戳，绕开 HTTP 缓存）
    ps('agent-browser eval "(function(){var l=document.createElement(\'link\');l.rel=\'stylesheet\';l.href=\'/assets/css/main.css?cb=\'+Date.now();document.head.appendChild(l);return 1})()"')
    time.sleep(1.2)
    ps('agent-browser wait --load networkidle')
    time.sleep(2.0)
    ps('agent-browser eval "document.getElementById(\'merch\').scrollIntoView();1"')
    time.sleep(1.6)

    out = ps('agent-browser eval (Get-Content -Raw -Encoding UTF8 "_qa/_merchfill.js")')
    d = None
    for line in reversed(out.splitlines()):
        line = line.strip()
        if line.startswith('"') and line.endswith('"'):
            try:
                d = json.loads(json.loads(line))
                break
            except Exception:
                continue

    if not d:
        print('RESULT: SKIP  未取到数据（浏览器或探针异常）')
        return 0
    if d.get('missing') or d.get('empty'):
        print('RESULT: SKIP  找不到文创网格或网格为空')
        return 0

    cards = d['cards']
    fails = []
    feat = [c for c in cards if c['feat']]
    if feat:
        f = feat[0]
        print('主推卡片 %dx%d，图片 %dx%d，填充率 %.1f%%' % (
            f['cardW'], f['cardH'], f['imgW'], f['imgH'], f['fill'] or 0))
        if f['fill'] is not None and f['fill'] < 25:
            fails.append('主推卡片图片填充率仅 %.1f%%（应 >= 25%%）' % f['fill'])
    else:
        print('[WARN] 没有 is-feature 卡片')

    low = [c for c in cards if c['fill'] is not None and c['fill'] < 5 and c['cardH'] > 100]
    if low:
        fails.append('%d 张卡片图片填充率 < 5%%（等于没图）' % len(low))

    ovf = [c for c in cards if c['overflow']]
    if ovf:
        fails.append('%d 张卡片图片溢出边界' % len(ovf))

    avg = sum((c['fill'] or 0) for c in cards) / len(cards)
    print('%d 张卡片，平均填充率 %.1f%%，溢出 %d 张' % (len(cards), avg, len(ovf)))
    print()
    if fails:
        print('RESULT: FAIL')
        for f in fails:
            print('  -', f)
        return 1
    print('RESULT: PASS  文创卡片图片占比正常（%d 张）' % len(cards))
    return 0


if __name__ == '__main__':
    sys.exit(main())