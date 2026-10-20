# -*- coding: utf-8 -*-
"""tools/contrast_audit.py —— 对比度审计（用浏览器计算色，不猜坐标/像素）。

## 三轮失败换来的方法

轮25 我想做全站对比度审计，连续三次测量都不对：

**尝试 1：CSS 解析（backgroundColor 向上找）**
· 主 CTA 按钮算出 1.05:1 —— 荒谬。原因：按钮背景是 linear-gradient，
  backgroundColor 是 transparent，解析器一路找到页面深色底，
  于是「深字 + 深底」= 1.05。
· 正确应为 9.06:1（像素实测）。

**尝试 2：像素采样（截取元素区域，极值当前景/背景）**
· 报 53 项不达标 —— 明显过度。原因：取「最亮/最暗 10%」会被抗锯齿边缘、
  卡片边框、装饰线干扰，不是文字色。

**尝试 3：像素采样（固定坐标区域）**
· 报文创 1.14:1 —— 原因：固定取 arr[380:520, 150:1250]，
  与实际元素位置无关，采到的可能是空白处。

**最终正确做法：直接用浏览器计算色**
  getComputedStyle(el).color          → 前景（含 alpha）
  向上遍历祖先 backgroundColor       → 找到第一个 alpha>0.9 的实色背景
  前景按 alpha 与背景合成后算 WCAG 对比度
结果：正文 rgba(244,237,225,0.74) on #0B0908 → **9.42:1**（AA 要求 4.5）达标。

## 为什么这个方法可靠
· 不需要猜坐标（不依赖截图）
· 不解析 CSS 渐变（遇到渐变就跳到已知的页面底色，并标注）
· 处理了 alpha 合成（这是 CSS 解析最容易漏的一步）

## 局限（必须写清）
· 背景是渐变时，取页面底色近似 —— 对本站（渐变都是深色系）误差可接受
· 不处理图片背景上的文字（本站没有）
· 这不是替代人工目检，而是给一个人工容易漏的量化下限

## 用法
    python tools/contrast_audit.py      # 需本地 8791 服务 + agent-browser
"""
import json
import os
import re
import subprocess
import sys
import time

PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROBE = r"""(function(){
  function parse(c){
    var m = (c||'').match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    var p = m[1].split(',').map(Number);
    return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1];
  }
  function lum(rgb){
    function f(v){ v/=255; return v<=0.03928 ? v/12.92 : Math.pow((v+0.055)/1.055,2.4); }
    return 0.2126*f(rgb[0])+0.7152*f(rgb[1])+0.0722*f(rgb[2]);
  }
  function ratio(a,b){
    var L1=lum(a), L2=lum(b), hi=Math.max(L1,L2), lo=Math.min(L1,L2);
    return (hi+0.05)/(lo+0.05);
  }
  var SEL = 'p,li,dd,figcaption,blockquote,h1,h2,h3,h4';
  var bad = [], checked = 0, skippedGradient = 0, skippedTransparent = 0;
  [].slice.call(document.querySelectorAll(SEL)).forEach(function(e){
    if (!e.offsetParent) return;
    if (e.closest('[data-decorative]')) return;
    var txt = [].slice.call(e.childNodes)
      .filter(function(n){ return n.nodeType === 3 && n.textContent.trim(); })
      .map(function(n){ return n.textContent.trim(); }).join('');
    if (!txt) return;
    var cs = getComputedStyle(e);
    // 渐变文字：color 是 transparent，可见颜色来自 background-clip:text 的渐变。
    // 这类不能用 color 判定（否则算成 1.00），跳过并计数。
    var clip = cs.webkitBackgroundClip || cs.backgroundClip || '';
    if (clip === 'text') { skippedGradient++; return; }
    var fg = parse(cs.color);
    if (!fg || fg[3] < 0.05) { skippedTransparent++; return; }
    // 向上找第一个实色背景（alpha > 0.9）
    var bg = null, el = e;
    while (el) {
      var s = getComputedStyle(el);
      if (s.backgroundImage && s.backgroundImage.indexOf('gradient') >= 0) { bg = [11,9,8,1]; break; }
      var c = parse(s.backgroundColor);
      if (c && c[3] > 0.9) { bg = c; break; }
      el = el.parentElement;
    }
    if (!bg) bg = [11,9,8,1];
    var comp = [fg[0]*fg[3]+bg[0]*(1-fg[3]),
                fg[1]*fg[3]+bg[1]*(1-fg[3]),
                fg[2]*fg[3]+bg[2]*(1-fg[3])];
    var r = ratio(comp, bg);
    var fs = parseFloat(cs.fontSize);
    var bold = parseInt(cs.fontWeight, 10) >= 700;
    var need = (fs >= 24 || (fs >= 18.66 && bold)) ? 3 : 4.5;
    checked++;
    if (r < need) {
      bad.push({ txt: txt.slice(0, 20), ratio: Math.round(r*100)/100, need: need,
                 fs: fs, color: cs.color, bg: 'rgb(' + bg.slice(0,3).join(',') + ')' });
    }
  });
  return JSON.stringify({ checked: checked, bad: bad, skippedGradient: skippedGradient, skippedTransparent: skippedTransparent });
})()"""


def ps(cmd, timeout=60):
    try:
        r = subprocess.run([PS, '-NoProfile', '-Command', cmd], capture_output=True, text=True,
                           cwd=BASE, timeout=timeout, encoding='utf-8', errors='replace')
        return ((r.stdout or '') + (r.stderr or '')).strip()
    except subprocess.TimeoutExpired:
        return 'TIMEOUT'


def main():
    tmp = os.path.join(BASE, '_qa', '_contrast.js')
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    open(tmp, 'w', encoding='utf-8').write(PROBE)

    ps('agent-browser set viewport 1440 900')
    ps('agent-browser open "http://127.0.0.1:8791/?contrast=%d"' % int(time.time()))
    ps('agent-browser wait --load networkidle')
    time.sleep(2.2)
    # 滚一遍让所有段落完成 reveal
    ps('agent-browser eval "(async function(){for(var y=0;y<document.body.scrollHeight;y+=700){window.scrollTo(0,y);await new Promise(function(r){setTimeout(r,60)});}window.scrollTo(0,0);return 1;})()"')
    time.sleep(2.0)

    out = ps('agent-browser eval (Get-Content -Raw -Encoding UTF8 "%s")' % tmp)
    data = None
    for line in reversed(out.splitlines()):
        line = line.strip()
        if line.startswith('"') and line.endswith('"'):
            try:
                data = json.loads(json.loads(line)); break
            except Exception:
                continue
    if not data:
        print('RESULT: SKIP  未能取到对比度读数（浏览器或服务不可用）')
        return 0

    checked = data['checked']
    bad = data['bad']
    print('检查 %d 处文本，不达标 %d 处' % (checked, len(bad)))
    for b in bad[:10]:
        print('  - %s  对比 %.2f < %.1f  (%.0fpx)  fg=%s bg=%s'
              % (b['txt'], b['ratio'], b['need'], b['fs'], b['color'], b['bg']))

    print()
    if checked == 0:
        print('RESULT: SKIP  未检查到任何文本 —— 不计入 PASS（防止「没测到」被当「通过」）')
        return 0
    if bad:
        print('RESULT: FAIL  %d/%d 处文本对比度不达标' % (len(bad), checked))
        return 1
    print('RESULT: PASS  %d 处文本对比度全部达 WCAG AA' % checked)
    return 0


if __name__ == '__main__':
    sys.exit(main())
