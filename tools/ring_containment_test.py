# -*- coding: utf-8 -*-
"""tools/ring_containment_test.py —— 装饰元素必须天然不溢出（U-07 防护）。

为什么单独立这条：
  修复前 totem-ring.b 用 inset:-5% 向外扩，实测宽 399px > 视口 390px（左右各溢 5px），
  完全靠祖先 overflow 裁切兜住。页面看着正常，但那是隐式依赖 ——
  容器去掉 overflow 或换布局，就会露横向滚动条。

双轨判据（静态必过，浏览器可用时再验位置）：
  静态：装饰环不得用「负 inset」或「超广 width」这类会扩大布局盒的写法
        （应改用 transform:scale —— transform 不参与布局盒计算，天然不产生滚动）
  浏览器：去掉裁切后 scrollWidth 仍 <= innerWidth

一手教训（轮11）：
  1) 最初判据用 scrollWidth > clientWidth，但内容把视口撑宽时两者会一起变大（都 1248），
     比值永远不成立 -> 漏判。基准必须是 window.innerWidth。
  2) 本机浏览器会话不稳定，若把它当唯一判据，门禁本身就不可靠。
     所以加静态判据兜底：浏览器挂掉时静态仍能守住回退。
"""
import json, os, re, subprocess, time, uuid

PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
WD = r'C:\Users\37533\Desktop\workspace\项目\新建文件夹'


def ps(cmd, timeout=50):
    try:
        r = subprocess.run([PS, '-NoProfile', '-Command', cmd], capture_output=True, text=True,
                           cwd=WD, timeout=timeout, encoding='utf-8', errors='replace')
        return ((r.stdout or '') + (r.stderr or '')).strip()
    except subprocess.TimeoutExpired:
        return 'TIMEOUT'


def json_of(out):
    for line in reversed((out or '').splitlines()):
        line = line.strip()
        if line.startswith('"') and line.endswith('"'):
            try:
                return json.loads(json.loads(line))
            except Exception:
                continue
    return None


def static_checks():
    css_path = os.path.join(WD, 'site', 'assets', 'css', 'main.css')
    css = open(css_path, encoding='utf-8').read()
    fails = []
    for sel in ['.hero-ring{', '.hero-ring.b{', '.totem-ring{', '.totem-ring.b{']:
        i = css.find(sel)
        if i < 0:
            fails.append('找不到规则 %s' % sel)
            continue
        rule = css[i: css.find('}', i)]
        if re.search(r'inset:\s*-', rule):
            fails.append('%s 使用负 inset，会向外扩布局盒' % sel.rstrip('{'))
        mw = re.search(r'width:\s*min\(\s*\d+%\s*,\s*(\d+)px\s*\)', rule)
        if mw and int(mw.group(1)) >= 500:
            fails.append('%s 的 width 上限 %spx 过大，可能撑大布局盒' % (sel.rstrip('{'), mw.group(1)))
    return fails


PROBE = ("JSON.stringify({"
         "rings:[].slice.call(document.querySelectorAll('.hero-ring, .totem-ring')).map(function(e){"
         "var r=e.getBoundingClientRect();"
         "return {c:String(e.className),left:Math.round(r.left),right:Math.round(r.right)};}),"
         "vw:innerWidth})")

UNCLIP = ("var a=document.querySelector('.hero-visual');if(a)a.style.overflow='visible';"
          "var b=document.querySelector('.totem-hit');if(b)b.style.overflow='visible';1")

SCROLL = ("JSON.stringify({sw:document.documentElement.scrollWidth,"
          "cw:document.documentElement.clientWidth,iw:window.innerWidth})")


def main():
    fails = static_checks()
    if fails:
        print('静态判据 FAIL：')
        for f in fails:
            print('  -', f)
    else:
        print('静态判据 PASS：装饰环未用负 inset / 超宽 width')

    ps('agent-browser close --all')
    time.sleep(0.8)
    ps('agent-browser set viewport 390 844')
    ps('agent-browser open "http://127.0.0.1:8791/?ring=%s"' % uuid.uuid4().hex[:6])
    ps('agent-browser wait --load networkidle')
    time.sleep(1.8)

    rings = json_of(ps('agent-browser eval "%s"' % PROBE.replace('"', '\\"')))
    if not rings:
        if fails:
            print('RESULT: FAIL  静态判据未通过')
            return 1
        print('RESULT: SKIP  静态通过；浏览器不可用，未能验位置')
        return 0

    vw = rings['vw']
    for r in rings['rings']:
        if r['left'] < -0.5 or r['right'] > vw + 0.5:
            fails.append('%s 溢出视口（left=%d right=%d vw=%d）' % (r['c'], r['left'], r['right'], vw))
    print('环位置：' + ' | '.join('%s[%d,%d]' % (r['c'], r['left'], r['right']) for r in rings['rings']))

    ps('agent-browser eval "%s"' % UNCLIP.replace('"', '\\"'))
    time.sleep(0.3)
    sc = json_of(ps("agent-browser eval '%s'" % SCROLL))
    if sc:
        base = sc.get('iw') or sc['cw']
        print('去掉裁切后：scrollWidth=%d clientWidth=%d innerWidth=%d' % (sc['sw'], sc['cw'], base))
        if sc['sw'] > base + 1:
            fails.append('去裁切后横向溢出（scrollWidth %d > innerWidth %d）' % (sc['sw'], base))
        if sc['cw'] > base + 1:
            fails.append('布局视口被内容撑宽（clientWidth %d > innerWidth %d）' % (sc['cw'], base))
    else:
        print('（去裁切读数未取到，跳过该子项）')

    print()
    if fails:
        print('RESULT: FAIL')
        for f in fails:
            print('  -', f)
        return 1
    print('RESULT: PASS  装饰环天然不溢出')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
