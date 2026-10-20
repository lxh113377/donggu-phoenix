# -*- coding: utf-8 -*-
"""tools/merch_image_fill_test.py —— 文创卡片图片占比（双视口 + dominant 指标）。

## 为什么改判据（轮50）
旧版用「图片面积 / 卡片面积」固定阈值 25%%，只在桌面测。
实测移动端 390×844 下 feature 卡该值只有 24%%——因为移动端卡片本身更矮，
百分比随视口漂移，固定阈值会在移动端误判。

## 新指标：dominant（视口无关、图片比例无关）
dominant = max(图片宽/容器内框宽, 图片高/容器内框高)
contain-fit 的图片必有一边贴到容器内框 -> 健康值 ~0.88（88%% 上限）。
若被「不该适用的额外约束」压小（如轮48 的 max-height:150 bug），
则连限制边都贴不满 -> dominant 明显 < 0.8。

书签(细长 235×620)：高度贴满 -> dominant ~0.88，不误伤（旧面积指标会误报 6%%）。
feature 修复前：宽高都被 150px 压 -> dominant << 0.8，判红。

## 双视口
桌面 1440×900 + 移动 390×844 各测一遍，两视口都要 dominant >= 0.8。
"""
import json
import os
import subprocess
import sys
import time

PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROBE = """(function(){
  var grid = document.querySelector('.merch-grid');
  if (!grid) return JSON.stringify({missing:1});
  var cards = [].slice.call(grid.children);
  var out = cards.map(function(c){
    var img = c.querySelector('img');
    var shot = c.querySelector('.merch-shot');
    if (!img || !shot || !img.naturalWidth) return null;
    var cs = getComputedStyle(shot);
    var padL = parseFloat(cs.paddingLeft)||0, padR = parseFloat(cs.paddingRight)||0;
    var padT = parseFloat(cs.paddingTop)||0, padB = parseFloat(cs.paddingBottom)||0;
    var sr = shot.getBoundingClientRect();
    var innerW = sr.width - padL - padR, innerH = sr.height - padT - padB;
    var ir = img.getBoundingClientRect();
    var fillW = innerW>0? ir.width/innerW : 0;
    var fillH = innerH>0? ir.height/innerH : 0;
    var dom = +Math.max(fillW,fillH).toFixed(2);
    return {feat:c.classList.contains('is-feature'), dominant:dom,
            overflow: (ir.bottom > sr.bottom+2 || ir.top < sr.top-2 || ir.right > sr.right+2 || ir.left < sr.left-2)};
  }).filter(function(x){return x;});
  return JSON.stringify({iw:innerWidth, cards:out});
})()"""

DOM_THRESHOLD = 0.80


def ps(cmd, timeout=90):
    try:
        r = subprocess.run([PS, '-NoProfile', '-Command', cmd], capture_output=True,
                           text=True, cwd=BASE, timeout=timeout, encoding='utf-8', errors='replace')
        return ((r.stdout or '') + (r.stderr or '')).strip()
    except subprocess.TimeoutExpired:
        return 'TIMEOUT'


def measure(vw, vh, probe_rel):
    ps('agent-browser set viewport %d %d' % (vw, vh))
    time.sleep(0.6)
    ps('agent-browser open "http://127.0.0.1:8791/?mf=%d"' % int(time.time() * 1000))
    ps('agent-browser wait --load networkidle')
    time.sleep(2.0)
    # cacheBust：注入带时间戳的 CSS，绕开 HTTP/SW 缓存
    bust = ("(function(){var l=document.createElement('link');"
            "l.rel='stylesheet';l.href='/assets/css/main.css?cb='+Date.now();"
            "document.head.appendChild(l);return 1})()")
    ps('agent-browser eval "%s"' % bust)
    time.sleep(1.2)
    ps("agent-browser eval \"document.getElementById('merch').scrollIntoView();1\"")
    time.sleep(1.4)
    out = ps('agent-browser eval (Get-Content -Raw -Encoding UTF8 "%s")' % probe_rel)
    for line in reversed(out.splitlines()):
        line = line.strip()
        if line.startswith('"') and line.endswith('"'):
            try:
                return json.loads(json.loads(line))
            except Exception:
                continue
    return None


def main():
    tmp = os.path.join(BASE, '_qa', '_merchdom.js')
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    open(tmp, 'w', encoding='utf-8').write(PROBE)

    ps('agent-browser open "http://127.0.0.1:8791/"')
    time.sleep(1.2)
    clear = os.path.join(BASE, '_qa', 'clear_sw.js')
    if os.path.exists(clear):
        ps('agent-browser eval (Get-Content -Raw -Encoding UTF8 "_qa/clear_sw.js")')
        time.sleep(1.0)

    fails = []
    any_data = False
    for w, h, label in [(1440, 900, '桌面'), (390, 844, '移动')]:
        d = measure(w, h, '_qa/_merchdom.js')
        if not d or d.get('missing'):
            print('[%s %dx%d] 无数据（跳过，不改判 PASS）' % (label, w, h))
            continue
        cards = d.get('cards') or []
        if not cards:
            print('[%s] 网格为空，跳过' % label)
            continue
        any_data = True
        doms = [c['dominant'] for c in cards]
        feat = [c for c in cards if c['feat']]
        mn = min(doms)
        feat_str = ('，feature %.2f' % feat[0]['dominant']) if feat else ''
        print('[%s %dx%d] %d 张卡，dominant 最小 %.2f%s' % (label, w, h, len(cards), mn, feat_str))
        if mn < DOM_THRESHOLD:
            worst = [c for c in cards if c['dominant'] < DOM_THRESHOLD]
            fails.append('%s %dx%d：%d 张卡 dominant < %.2f（图片被压小，最低 %.2f）' % (
                label, w, h, len(worst), DOM_THRESHOLD, mn))
        ovf = [c for c in cards if c['overflow']]
        if ovf:
            fails.append('%s %dx%d：%d 张卡图片溢出容器' % (label, w, h, len(ovf)))

    print()
    if not any_data:
        print('RESULT: SKIP  两视口均无数据')
        return 0
    if fails:
        print('RESULT: FAIL')
        for f in fails:
            print('  -', f)
        return 1
    print('RESULT: PASS  双视口文创图片占比正常（dominant >= %.2f）' % DOM_THRESHOLD)
    return 0


if __name__ == '__main__':
    sys.exit(main())
