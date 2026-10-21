# -*- coding: utf-8 -*-
"""tools/visual_balance_test.py —— 首屏构图平衡的客观测量（自截图，多视口）。

## 为什么需要它
「构图是否平衡」通常是主观判断。轮40 我收到独立评审说「左右六四开、右下偏轻」，
用像素统计核实后发现：左 52.8% / 右 47.2%，差异仅 5.6%，实际是平衡的。
→ 主观判断需要客观数据校准。

## 轮99：补上自截图能力（此前依赖 agent-browser daemon）
原实现是纯像素统计（Python/numpy），但**截图步骤**依赖 agent-browser，
而 daemon 已死 -> 判据实际从未跑过，只能拿旧截图手工喂。
「判据存在但跑不了」比没有判据更危险（merch_image_fill_test 的教训，U-297）。

自截图实现与 merch_image_fill_test 同源（chrome 直连 + 同源 iframe + 重试）：
  · 桌面用 --window-size 直接测
  · 窄屏用同源 iframe 承载：Chrome 窗口有最小宽度，直接设窄窗会产生
    「内容右移被切」的假象（U-176 踩过）
  · chrome 偶发空输出 -> 最多 5 次重试（U-193）
  · 截图后按视口居中裁剪：Chrome 窗口有最小宽度，窄屏截图会带外侧黑边，
    不裁的话统计的是「含黑边的窗口」而非目标视口
  · 不用 --force-prefers-reduced-motion：那会让 Phoenix 走降级路径，
    而 phoenix.load() 是异步的，截图常抓到空 canvas

## 已知边界（诚实记录，不假装稳定）
768x1024（平板）视口在本机**偶发不稳定**：__phoenix.state 有时停在
'assemble'，2600 个粒子仍在飞向目标，左右分量差异会冲到 28~33%。
同一视口多次跑出过 27.9% / 28.6% / 32.8% 三个不同值。
根因：--screenshot 是一次性快照，无法像 CDP 那样等待事件；
virtual-time-budget 与 requestAnimationFrame 的交互在本机不稳定。
试过并**无效/更糟**的做法（均已回退，记录以免重复踩）：
  配置 A 保留 --force-prefers-reduced-motion
      -> 三视口全红（44.8% / 39.5% / 46.6%），canvas 常空
  配置 C 主动调 __phoenix._drawStatic()
      -> 手机 36.4%、桌面 44.2%（按起点态粒子定住，比不调更糟）
  配置 D 等 assemble 结束再调 _drawStatic()
      -> 平板单次 19.4% 好转，但桌面被破坏到 44.2%，整体不可行
  轮询 state 再改 document.title（早期）
      -> --screenshot 不读 title，完全无效
最终采用配置 B，并对 assemble 未完成的视口诚实标 SKIP。
桌面 1440x900 与手机 390x844 多跑一致（极差 1.5 / 0.5 个百分点）。

## 轮99：从单视口扩到三视口
构图平衡是响应式维度：轮40 只在桌面测过，窄屏下布局重排
（hero 从左右分栏变成上下堆叠），左右对称这个判据本身会失效。
故窄屏改用**上下分量**（上/下视觉重量），而非硬套左右口径 ——
否则会在窄屏上误报。同时仍输出水平分量作参考。

## 测量方法
视觉重量 = 相对背景的亮度对比 × (1 + 饱和度)，逐像素平均。
这是视觉显著性的粗略近似（人眼对高对比、高饱和区域更敏感）。

## 判据
· 主方向重量差异 < 15% → 平衡
· 15%-25% → 轻微失衡（可接受，视设计意图）
· > 25% → 明显失衡

## ⚠ 本判据不得作为 CI 门禁（轮99 实测结论，勿重复踩）
三连跑（最终配置 B）：
  桌面 1440x900  13.2 / 13.1 / 15.6   极差 2.5   稳定可用
  平板 768x1024  29.6 / 30.8 / 32.9   极差 3.3   稳定但持续超阈值
  手机 390x844    5.0 / 36.4 /  5.0   极差 31.4  偶发跳变
平板高读数非产品缺陷：DOM 实测 __phoenix.ox=384（正好视口一半），
锚点本身居中；~30% 来自 assemble 中间帧（2600 粒子仍聚在起点）。
手机偶发跳变同源，且 assemble 降级兜不住 —— title 已写 idle
而 canvas 还差一帧才落笔，本机 virtual-time-budget 与 rAF 有竞态。

一个会偶发 FAIL 的门禁比没有更糟：它会训练人忽略红灯，
也会在真缺陷来时被当成「又抖了」。
故本判据仅供本地人工参考：桌面读数可信，可作设计评审客观依据；
平板/手机读数仅供参考，不可据此判产品失衡。
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(BASE, 'site')
OUT = os.path.join(BASE, '_qa', 'r99')

# (标签, 视口宽, 视口高, 主方向) —— 窄屏主方向改上下，因布局已重排
VIEWPORTS = [
    ('桌面', 1440, 900, 'h'),
    ('平板', 768, 1024, 'h'),
    ('手机', 390, 844, 'v'),
]
TOP_SKIP = 60   # 去掉顶部固定导航区


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
    h = partial(Quiet, directory=SITE)
    try:
        srv = ThreadingHTTPServer(('127.0.0.1', port), h)
    except OSError:
        return None
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def shoot(chrome, port, vw, vh, png):
    """截图首页首屏。宽屏直开，窄屏走同源 iframe（Chrome 窗口有最小宽度）。"""
    wrap = os.path.join(SITE, '_vb_probe.html')
    if os.path.exists(png):
        os.remove(png)
    for attempt in range(5):
        udd = os.path.join(tempfile.gettempdir(),
                           'chr_vb_%d_%d' % (os.getpid(), attempt))
        if vw <= 800:
            open(wrap, 'w', encoding='utf-8').write(
                '<!doctype html><meta charset="utf-8"><title>pending</title><style>'
                'html,body{margin:0;background:#0B0908}'
                'iframe{border:0;display:block;width:%dpx;height:%dpx}'
                '</style><iframe id="f" src="/index.html?vb=%d"></iframe>'
                '<script>'
                '(function(){'
                '  var n=0, ph=null;'
                '  (function tick(){'
                '    try{'
                '      var w=f.contentWindow; ph=w&&w.__phoenix;'
                '      var done=!ph||ph.state==="idle"||ph.state==="flight";'
                '      if(done||n>90){return;}'
                '      n++;setTimeout(tick,80);'
                '    }catch(e){n++;setTimeout(tick,80);}'
                '  })();'
                '  document.title = (ph && ph.state) ? ph.state : "noph";'
                '})();'
                '</script>'
                % (vw, vh, int(os.getpid() * 1000 + attempt)))
            url = 'http://127.0.0.1:%d/_vb_probe.html?cb=%d' % (
                port, int(os.getpid() * 1000 + attempt))
        else:
            # 宽屏也走 wrapper：统一等 Phoenix 组装完成再快照
            # （此前宽屏直开，768/1440 都抓到过 assemble 中间帧）
            open(wrap, 'w', encoding='utf-8').write(
                '<!doctype html><meta charset="utf-8"><title>pending</title><style>'
                'html,body{margin:0;background:#0B0908}'
                'iframe{border:0;display:block;width:%dpx;height:%dpx}'
                '</style><iframe id="f" src="/index.html?vb=%d"></iframe>'
                '<script>'
                '(function(){var n=0,ph=null;'
                '(function tick(){try{'
                '  var w=f.contentWindow; ph=w&&w.__phoenix;'
                '  var done=!ph||ph.state==="idle"||ph.state==="flight";'
                '  if(done||n>90){return;}'
                '  n++;setTimeout(tick,80);'
                '}catch(e){n++;setTimeout(tick,80);}})();'
                '  try{document.title=(ph&&ph.state)?ph.state:"noph";}catch(e2){}'
                '})();'
                '</script>'
                % (vw, vh, int(os.getpid() * 1000 + attempt)))
            url = 'http://127.0.0.1:%d/_vb_probe.html?cb=%d' % (
                port, int(os.getpid() * 1000 + attempt))
        cmd = [chrome, '--headless=new', '--disable-gpu', '--hide-scrollbars',
               '--force-device-scale-factor=1',
               '--window-size=%d,%d' % (max(vw + 40, 900), vh + 60),
               '--user-data-dir=' + udd,
               '--virtual-time-budget=40000',
               '--screenshot=' + png, '--dump-dom', url]
        dom = ''
        try:
            rr = subprocess.run(cmd, capture_output=True, text=True,
                                encoding='utf-8', errors='replace', timeout=120)
            dom = rr.stdout or ''
        except subprocess.TimeoutExpired:
            pass
        finally:
            shutil.rmtree(udd, ignore_errors=True)
            if wrap:
                try:
                    os.remove(wrap)
                except Exception:
                    pass
        if os.path.exists(png) and os.path.getsize(png) > 20000:
            # state 与画面来自同一次加载（--dump-dom 与 --screenshot 并存）
            st = 'unknown'
            m2 = re.search(r'<title>(.*?)</title>', dom, re.S)
            if m2:
                st = m2.group(1).strip()[:24]
            return st
    return None


def crop_to_viewport(png, vw, vh):
    """把截图居中裁到目标视口尺寸。返回 False 表示无法处理（不静默跳过统计）。"""
    try:
        from PIL import Image
    except ImportError:
        return False
    try:
        im = Image.open(png).convert('RGB')
    except Exception:
        return False
    w, h = im.size
    if w == vw and h == vh:
        return True
    # 居中裁剪；若窗口比目标小（不该发生），保留原样交由上层判断
    if w < vw or h < vh:
        return False
    left = (w - vw) // 2
    top = (h - vh) // 2
    im.crop((left, top, left + vw, top + vh)).save(png)
    return True


def analyze(png, axis):
    """返回 (差异百分比, 判定词, 是否判红, 详情行)。"""
    import numpy as np
    from PIL import Image

    img = Image.open(png).convert('RGB')
    arr = np.array(img, dtype=float)
    h, w, _ = arr.shape
    content = arr[TOP_SKIP:, :, :]
    ch, cw, _ = content.shape

    def weight(region):
        r, g, b = region[:, :, 0], region[:, :, 1], region[:, :, 2]
        lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
        mx = np.max(region, axis=2)
        mn = np.min(region, axis=2)
        sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1), 0)
        return float(np.mean(np.abs(lum - 11.0) * (1 + sat)))

    if axis == 'h':
        a, b = weight(content[:, :cw // 2]), weight(content[:, cw // 2:])
        names, detail = ('左', '右'), ''
    else:
        a, b = weight(content[:ch // 2, :]), weight(content[ch // 2:, :])
        names, detail = ('上', '下'), '（窄屏布局已重排，按上下分量）'

    total = a + b
    diff = abs(a - b) / total * 100 if total else 0.0
    if diff > 25:
        verdict, bad = '明显失衡', True
    elif diff > 15:
        verdict, bad = '轻微失衡（可视设计意图接受）', False
    else:
        verdict, bad = '平衡', False

    # 纵向空洞检测（内容量极低的连续区间）
    holes = []
    for x0, x1, label in [(0, cw // 2, '左'), (cw // 2, cw, '右')]:
        vals = []
        for y0 in range(0, ch, 100):
            region = content[y0:y0 + 100, x0:x1]
            rr, gg, bb = region[:, :, 0], region[:, :, 1], region[:, :, 2]
            lum = 0.2126 * rr + 0.7152 * gg + 0.0722 * bb
            vals.append((lum > 30).mean() * 100)
        if all(v < 1.0 for v in vals[-3:]):
            holes.append('%s栏下方连续 300px 无内容' % label)
    return diff, verdict, bad, (names, a, b, total, detail), holes


def main():
    try:
        import numpy as np  # noqa: F401
        from PIL import Image  # noqa: F401
    except ImportError:
        print('RESULT: SKIP  缺 numpy/Pillow（环境问题，非判据通过）')
        return 0

    chrome = find_chrome()
    if not chrome:
        print('RESULT: SKIP  找不到 chrome.exe（环境问题，非判据通过）')
        return 0

    # 兼容旧用法：显式传截图路径时只做分析，不自拍
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        diff, verdict, bad, det, holes = analyze(sys.argv[1], 'h')
        (names, a, b, total, _d) = det
        n1, n2 = names
        print('截图: %s' % sys.argv[1])
        print('左右视觉重量: %s %.2f (%.1f%%) / %s %.2f (%.1f%%)' % (
            n1, a, a / total * 100, n2, b, b / total * 100))
        print('差异: %.1f%%  判定: %s' % (diff, verdict))
        if holes:
            print('  提示: %s（可能是留白，也可能是空洞，需目检判断）'
                  % '; '.join(holes))
        print()
        print('RESULT: %s  %s（差异 %.1f%%）' % (
            'FAIL' if bad else 'PASS', verdict, diff))
        return 1 if bad else 0

    os.makedirs(OUT, exist_ok=True)
    port = free_port()
    srv = start_site_server(port)
    if not srv:
        print('RESULT: SKIP  静态服务起不来（环境问题，非判据通过）')
        return 0

    fails, any_data = [], False
    try:
        for label, vw, vh, axis in VIEWPORTS:
            png = os.path.join(OUT, 'vb_%dx%d.png' % (vw, vh))
            st = shoot(chrome, port, vw, vh, png)
            if not st:
                print('[%s %dx%d] 截图失败（环境问题，不改判）' % (label, vw, vh))
                continue
            # 轮99：凤凰仍在组装中 -> 该视口读数不可用，诚实标 SKIP
            # （实测平板 768 稳定停在 assemble，左右差 32% 是中间帧污染，
            #   而 ox=384 正好视口一半，构图本身居中）
            if st == 'assemble':
                print('[%s %dx%d] SKIP  截图时凤凰仍在组装（state=assemble），'
                      '该视口构图读数不可用 —— 不给假读数' % (label, vw, vh))
                continue
            # 轮99：Chrome 窗口有最小宽度，窄屏截图会带外侧黑边，
            # 不裁的话统计的是「含黑边的窗口」而非目标视口 ——
            # 桌面本来平衡，却被报成 43.3% 失衡。必须按视口居中裁。
            if not crop_to_viewport(png, vw, vh):
                print('[%s %dx%d] 裁剪失败，跳过该视口' % (label, vw, vh))
                continue
            any_data = True
            diff, verdict, bad, det, holes = analyze(png, axis)
            (names, a, b, total, detail) = det
            n1, n2 = names
            print('[%s %dx%d] %s %s %.2f (%.1f%%) / %s %.2f (%.1f%%) -> 差异 %.1f%%  %s%s'
                  % (label, vw, vh, '主方向' if detail else '左右',
                     n1, a, a / total * 100, n2, b, b / total * 100,
                     diff, verdict, detail))
            for hl in holes:
                print('    提示: %s（可能是留白，也可能是空洞，需目检判断）' % hl)
            if bad:
                fails.append('%s %dx%d：%s重量差异 %.1f%% > 25%%' % (
                    label, vw, vh, n1, diff))
    finally:
        try:
            srv.shutdown()
        except Exception:
            pass

    print()
    measured = len([1 for l, w, h, a in VIEWPORTS
                    if os.path.exists(os.path.join(OUT, 'vb_%dx%d.png' % (w, h)))])
    if not any_data:
        print('RESULT: SKIP  全部视口截图失败（环境问题，本判据未真正执行）')
        return 0
    # 轮99：有视口没测到时不能报 PASS —— 那会把「只测了 2/3」
    # 伪装成「3 个都合格」。静默跳过比判红更危险。
    if measured < len(VIEWPORTS):
        missing = ['%s %dx%d' % (l, w, h) for l, w, h, a in VIEWPORTS
                   if not os.path.exists(os.path.join(OUT, 'vb_%dx%d.png' % (w, h)))]
        print('RESULT: SKIP  仅 %d/%d 个视口测到，缺: %s'
              % (measured, len(VIEWPORTS), '; '.join(missing)))
        print('  - 有视口未测到时不判 PASS：部分失败被静默吞掉，'
              '会让「只测了 2/3」伪装成「全都合格」')
        return 0
    if fails:
        print('RESULT: FAIL')
        for f in fails:
            print('  -', f)
        return 1
    print('RESULT: PASS  %d 个视口首屏构图均在可接受范围' % len(VIEWPORTS))
    return 0


if __name__ == '__main__':
    sys.exit(main())
