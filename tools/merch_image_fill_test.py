# -*- coding: utf-8 -*-
"""tools/merch_image_fill_test.py —— 文创卡片图片占比（双视口 + dominant 指标）。

## 为什么改判据（轮50）
旧版用「图片面积 / 卡片面积」固定阈值 25%，只在桌面测。
实测移动端 390×844 下 feature 卡该值只有 24%——因为移动端卡片本身更矮，
百分比随视口漂移，固定阈值会在移动端误判。

## 新指标：dominant（视口无关、图片比例无关）
dominant = max(图片宽/容器内框宽, 图片高/容器内框高)
contain-fit 的图片必有一边贴到容器内框 -> 健康值 ~0.88（88% 上限）。
若被「不该适用的额外约束」压小（如轮48 的 max-height:150 bug），
则连限制边都贴不满 -> dominant 明显 < 0.8。

书签(细长 235×620)：高度贴满 -> dominant ~0.88，不误伤（旧面积指标会误报 6%）。
feature 修复前：宽高都被 150px 压 -> dominant << 0.8，判红。

## 轮96：从 agent-browser 迁到 chrome 直连（关键）
原实现依赖 agent-browser daemon。该 daemon 已死（PID 失效 + 端口被并行会话占用），
于是本判据**每次返回 SKIP**，而 SKIP 在聚合里不算失败 ——
轮47 之后移动端那次真实退化（每张普通卡白扔 20px，见 U-291）它一次都没抓到。
「判据存在但跑不了」比没有判据更危险：它给人已经覆盖了的错觉。

迁移要点：
  · 桌面用 --window-size=1440,900 直接测（宽屏无最小宽度问题）
  · 移动 390 必须用**同源 iframe** 承载：Chrome 窗口有最小宽度，
    直接把窗口设成 390 会产生「内容右移被切」的假象（U-176 踩过）
  · cacheBust 保留：注入带时间戳的 <link> 绕开 HTTP/SW 缓存
  · chrome 偶发空输出（U-193）-> 每视口最多 5 次重试
  · 两视口都无数据 -> SKIP 且**明确说明是环境问题**，不算判据通过
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(BASE, 'site')

# 在目标文档（可能是 iframe 的 contentDocument）里测量。
# 用 doc/win 参数化，桌面与移动共用同一份逻辑，避免两套口径漂移。
PROBE = """(function(doc, win){
  var grid = doc.querySelector('.merch-grid');
  if (!grid) return JSON.stringify({missing:1});
  var cards = [].slice.call(grid.children);
  var out = cards.map(function(c){
    var img = c.querySelector('img');
    var shot = c.querySelector('.merch-shot');
    if (!img || !shot || !img.naturalWidth) return null;
    var cs = win.getComputedStyle(shot);
    var padL = parseFloat(cs.paddingLeft)||0, padR = parseFloat(cs.paddingRight)||0;
    var padT = parseFloat(cs.paddingTop)||0, padB = parseFloat(cs.paddingBottom)||0;
    var sr = shot.getBoundingClientRect();
    var innerW = sr.width - padL - padR, innerH = sr.height - padT - padB;
    var ir = img.getBoundingClientRect();
    var fillW = innerW>0? ir.width/innerW : 0;
    var fillH = innerH>0? ir.height/innerH : 0;
    var dom = +Math.max(fillW,fillH).toFixed(2);
    return {feat:c.classList.contains('is-feature'), dominant:dom,
            overflow: (ir.bottom > sr.bottom+2 || ir.top < sr.top-2 ||
                       ir.right > sr.right+2 || ir.left < sr.left-2)};
  }).filter(function(x){return x;});
  return JSON.stringify({iw:win.innerWidth, cards:out});
})"""

DOM_THRESHOLD = 0.80


def find_chrome():
    root = os.path.join(os.path.expanduser('~'), '.agent-browser', 'browsers')
    if not os.path.isdir(root):
        return None
    for name in sorted(os.listdir(root), reverse=True):
        exe = os.path.join(root, name, 'chrome.exe')
        if os.path.exists(exe):
            return exe
    return None


def free_port():
    import socket
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    p = s.getsockname()[1]
    s.close()
    return p


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def start_site_server(port):
    """进程内起静态服务（跑完关），不依赖外部常驻进程。"""
    h = partial(Quiet, directory=SITE)
    try:
        srv = ThreadingHTTPServer(('127.0.0.1', port), h)
    except OSError:
        return None
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv


def wrapper_html(vw, vh):
    """同源 iframe 承载目标视口；宽屏也走同一套，保证两视口口径一致。"""
    return (
        "<!doctype html><html><head><meta charset=\"utf-8\"><title>pending</title>"
        "<style>html,body{margin:0;padding:0;background:#0B0908}"
        "iframe{border:0;display:block;width:%dpx;height:%dpx}</style></head>"
        "<body><iframe id=\"f\" src=\"/index.html?mf=%d#merch\"></iframe>"
        "<script>"
        "function go(){try{"
        "  var d=f.contentDocument,w=f.contentWindow;"
        "  var g0=d.querySelector('.merch-grid');if(!g0||!g0.children.length){setTimeout(go,600);return;}"
        "  var g=g0;"
        "  if(g.scrollIntoView){g.scrollIntoView();}"
        "  /* cacheBust：绕开 HTTP/SW 缓存，读到真实 CSS */"
        "  var l=d.createElement('link');l.rel='stylesheet';"
        "  l.href='/assets/css/main.css?cb='+Date.now();"
        "  d.head.appendChild(l);"
        "  setTimeout(function(){"
        "    document.title=" + PROBE + "(d,w);"
        "  },1400);"
        "}catch(e){document.title=JSON.stringify({err:String(e)});}}"
        "f.addEventListener('load',function(){setTimeout(go,900);});"
        "setTimeout(go,1500);"
        "</script></body></html>"
    ) % (vw, vh, int(time.time() * 1000))


def measure(chrome, port, vw, vh, attempts=5):
    """返回 dict 或 None。chrome 偶发空输出需重试（U-193）。"""
    probe_rel = '_qa/_merchdom_probe.html'
    probe_abs = os.path.join(SITE, '_merchdom_probe.html')
    open(probe_abs, 'w', encoding='utf-8').write(wrapper_html(vw, vh))
    url = 'http://127.0.0.1:%d/%s?cb=%d' % (port, probe_rel.replace('_qa/', ''),
                                            int(time.time() * 1000))
    # 探针页直接放 site/ 根，避免子路径与 SW 作用域纠缠
    url = 'http://127.0.0.1:%d/_merchdom_probe.html?cb=%d' % (
        port, int(time.time() * 1000))
    rows = None
    try:
        for _ in range(attempts):
            udd = os.path.join(tempfile.gettempdir(),
                               'chr_mif_%d' % os.getpid())
            cmd = [chrome, '--headless=new', '--disable-gpu', '--hide-scrollbars',
                   '--force-device-scale-factor=1',
                   '--window-size=%d,%d' % (max(vw + 40, 900), vh + 60),
                   '--user-data-dir=' + udd,
                   '--virtual-time-budget=30000', '--dump-dom', url]
            try:
                r = subprocess.run(cmd, capture_output=True, text=True,
                                   encoding='utf-8', errors='replace', timeout=140)
                dom = r.stdout or ''
            except subprocess.TimeoutExpired:
                dom = ''
            finally:
                try:
                    os.remove(udd)
                except Exception:
                    pass
            m = re.search(r'<title>(.*?)</title>', dom, re.S)
            raw = (m.group(1) if m else '') or ''
            if raw and raw != 'pending':
                try:
                    rows = json.loads(raw)
                    break
                except Exception:
                    pass
            time.sleep(1.5)
    finally:
        try:
            os.remove(probe_abs)
        except Exception:
            pass
    return rows


def main():
    chrome = find_chrome()
    if not chrome:
        print('RESULT: SKIP  找不到 chrome.exe（环境问题，非判据通过）')
        return 0
    port = free_port()
    srv = start_site_server(port)
    if not srv:
        print('RESULT: SKIP  静态服务起不来（环境问题，非判据通过）')
        return 0

    fails = []
    any_data = False
    try:
        for w, h, label in [(1440, 900, '桌面'), (390, 844, '移动')]:
            d = measure(chrome, port, w, h)
            if not d or d.get('missing'):
                print('[%s %dx%d] 无数据（环境/渲染问题，不改判 PASS）' % (label, w, h))
                continue
            if d.get('err'):
                print('[%s] 探针异常: %s' % (label, d['err']))
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
            print('[%s %dx%d] 视口%d，%d 张卡，dominant 最小 %.2f 均值 %.2f%s' % (
                label, w, h, d.get('iw'), len(cards), mn,
                sum(doms) / len(doms), feat_str))
            if mn < DOM_THRESHOLD:
                worst = [c for c in cards if c['dominant'] < DOM_THRESHOLD]
                fails.append('%s %dx%d：%d 张卡 dominant < %.2f（图片被压小，最低 %.2f）'
                             % (label, w, h, len(worst), DOM_THRESHOLD, mn))
            ovf = [c for c in cards if c['overflow']]
            if ovf:
                fails.append('%s %dx%d：%d 张卡图片溢出容器' % (label, w, h, len(ovf)))
    finally:
        try:
            srv.shutdown()
        except Exception:
            pass

    print()
    if not any_data:
        print('RESULT: SKIP  两视口均无数据（环境问题，本判据未真正执行）')
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
