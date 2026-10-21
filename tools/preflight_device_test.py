# -*- coding: utf-8 -*-
"""tools/preflight_device_test.py —— 真机前哨判据（U-01 的自动化面）。

## 为什么需要它
验收判据里有三条只能在手机上验：①扫码 3 秒内出首屏 ②旁白中文发声 ③AR 三场景可看。
但本机**没有真机**（实测：Get-PnpDevice -Class WPD 无 OK 状态设备、未装 adb、
Windows 无 iOS 自动化通道），真人持机不可自动化的部分压到「一次点击」（见 site/_device_probe.html）。

本判据把**能自动化的部分**全部自动化，用 CDP 在模拟移动端下实测：
  · UA 三档：微信 iOS / 微信 Android / iPhone Safari（Emulation.setUserAgentOverride）
  · 视口三档：390x844 / 360x800，DPR 3，mobile=true（真 CSS 视口，非 --window-size 伪影）
  · 网络：CDP 4G 限速（170ms RTT / 4Mbps 下行）
  · CPU：4x 降频（对标中端机）
  · 读数：FCP/LCP/CLS/LongTask、console+JS 错误、横向溢出、AR 三场景实际推进与画面变化、
          摄像头不可用时的展柜模式降级、旁白可用性与状态自洽

## 诚实边界（写进结论，不藏）
模拟 ≠ 真机。本轮只能**证伪**（模拟都不达标 ⇒ 真机必然不达标），不能**证实**。
WebKit（Safari）与 XWEB（微信）内核差异、真实 CPU/内存/自动播放策略仍需真机自证。

## 双向自检（尺子先自证，再量产品）
  · _qa/preflight_selftest_good.html  -> 三档判据都必须判「无违规」
  · _qa/preflight_selftest_bad.html   -> JS 错误 / 横向溢出 / 阻塞 3.2s 致 FCP 超预算，必须**全部报出**
任一方向不符即 FAIL（尺子哑了，读数不可信）。

## 用法
  python tools/preflight_device_test.py            # 三档 profile 全跑
  python tools/preflight_device_test.py --fast     # 只跑第一档（微信 iOS）
  python tools/preflight_device_test.py --selftest # 只跑尺子自检
"""
import argparse
import functools
import http.server
import json
import os
import random
import re
import shutil
import socket
import socketserver
import subprocess
import sys
import tempfile
import threading
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRIVER = os.path.join(BASE, 'tools', 'preflight_device.mjs')

# 测试用主机名：**故意**不在 analytics.js 的上报白名单（localhost/127.0.0.1/*.pages.dev）里，
# 这样本地跑的就是「GitHub Pages 静态主链」那一面的真实语义 —— 扫码落到的那一面。
# 代价：本机跑不出「有后端那一面」的效果，那面由已上线的 pages.dev + 后台判据覆盖。
TEST_HOST = 'donggu.local'
# --no-proxy-server 是硬需求：实测不加它，Chrome 会走系统代理，别名解析变 502/5s（_qa/dbg_host.py 实测）
CHROME_ARGS = ['--host-resolver-rules=MAP %s 127.0.0.1' % TEST_HOST, '--no-proxy-server']

FCP_BUDGET_MS = 3000      # 验收判据 1：扫码 3 秒内出首屏
LCP_BUDGET_MS = 4000
OVERFLOW_TOL = 1          # 与 multi_viewport_test 同口径
# fps 下限按证据定，不按感觉定（_qa/dbg_gpu.py 实测，wechat-ios 档）：
#   CPU 1x: craft/red/phoenix = 53/60/60 fps ；CPU 4x: 14/21/19 fps（GPU 开关无差别 ⇒ 瓶颈在 CPU，不在光栅）
#   4x 降频是**保守代理**（本机桌面核心 ≈ 中端手机 2~4 倍单核），真实中端机大概率在 25~40 fps。
#   故此处只把「冻结线」定为红：低于 10 fps 判 FAIL；「画面在动」由另两条独立证据保证
#   （进度轴推进 + 两次采样画面签名必须不同），不靠 fps 一个数撑全部结论。
MIN_FPS = 10
MIN_T2_DELTA = 0.4        # 1.3s 采样窗口内进度轴至少推进 0.4s
R_COMMON = dict(latency=170, down=500000, up=500000)   # 4G 中位：170ms RTT / 4Mbps

PROFILES = [
    dict(name='wechat-ios', ua=('Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 '
                                '(KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.49(0x18003137) '
                                'NetType/WIFI Language/zh_CN'),
         platform='iPhone', width=390, height=844, dpr=3, cpu=4, heavy=True),
    dict(name='iphone-safari', ua=('Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 '
                                   '(KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1'),
         platform='iPhone', width=390, height=844, dpr=3, cpu=4, heavy=False),
    dict(name='wechat-android', ua=('Mozilla/5.0 (Linux; Android 13; PGT-AN10 Build/HUAWEIPGT-AN10; wv) '
                                    'AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/122.0.0.0 '
                                    'Mobile Safari/537.36 XWEB/1260089 MMWEBSDK/20240801 '
                                    'MicroMessenger/8.0.50(0x2800323C) NetType/WIFI Language/zh_CN'),
         platform='Linux armv8l', width=360, height=800, dpr=3, cpu=4, heavy=False),
]


def find_chrome():
    root = os.path.join(os.path.expanduser('~'), '.agent-browser', 'browsers')
    if os.path.isdir(root):
        for d in sorted(os.listdir(root), reverse=True):
            exe = os.path.join(root, d, 'chrome.exe')
            if os.path.exists(exe):
                return exe
    for p in (r'C:\Program Files\Google\Chrome\Application\chrome.exe',
              r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'):
        if os.path.exists(p):
            return p
    return None


class _Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def start_server():
    handler = functools.partial(_Handler, directory=BASE)
    # 必须多线程：站点首屏 15 个资源并发取，单线程服务器会把「带宽」误算成「排队」
    # （_qa/dbg_bw2.py 实测：单线程下第三个档位直接把连接 reset 掉）
    class _Srv(socketserver.ThreadingTCPServer):
        daemon_threads = True
        allow_reuse_address = True
    httpd = _Srv(('127.0.0.1', 0), handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(0.3)
    return httpd, port


def launch_chrome(chrome, extra_args=None):
    """启一个独立 chrome（独立 user-data-dir，避免 SW cache 污染下一档读数）。"""
    udd = os.path.join(tempfile.gettempdir(), 'chr_pf_%d' % random.randint(0, 10 ** 6))
    os.makedirs(udd, exist_ok=True)
    args = [chrome, '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
            '--disable-extensions', '--disable-background-networking', '--mute-audio',
            '--remote-debugging-port=0', '--user-data-dir=' + udd, 'about:blank']
    if extra_args:
        args[1:1] = extra_args
    proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    port_file = os.path.join(udd, 'DevToolsActivePort')
    for _ in range(80):
        if os.path.exists(port_file):
            break
        if proc.poll() is not None:
            return proc, None, udd
        time.sleep(0.25)
    if not os.path.exists(port_file):
        return proc, None, udd
    try:
        port = int(open(port_file, encoding='utf-8').read().splitlines()[0].strip())
    except Exception:
        port = None
    return proc, port, udd


def stop_chrome(proc, udd):
    try:
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except Exception:
                proc.kill()
    finally:
        shutil.rmtree(udd, ignore_errors=True)


def run_driver(port, cfg):
    exe = shutil.which('node') or shutil.which('node.exe')
    if not exe:
        return None
    args = [exe, DRIVER, json.dumps(cfg)]
    try:
        r = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=240)
    except subprocess.TimeoutExpired:
        return {'ok': False, 'error': 'driver 超时 240s（chrome/CDP 无响应）'}
    out = r.stdout or ''
    m = re.search(r'__PF_JSON__(.*)', out)
    if not m:
        return {'ok': False, 'error': 'driver 无 JSON 输出；stderr=' + (r.stderr or '')[-300:]}
    try:
        return json.loads(m.group(1))
    except Exception as e:
        return {'ok': False, 'error': 'JSON 解析失败 %s: %s' % (e, m.group(1)[:200])}


def probe_once(chrome, url, prof, heavy=None, timeout_tag=''):
    """跑一档：启 chrome -> 驱动 -> 停 chrome。"""
    proc, port, udd = launch_chrome(chrome, CHROME_ARGS)
    try:
        if not port:
            return {'ok': False, 'error': 'chrome 未开出 DevTools 端口（进程启动失败）'}
        cfg = dict(port=port, url=url, ua=prof['ua'], platform=prof['platform'],
                   width=prof['width'], height=prof['height'], dpr=prof['dpr'],
                   throttle=dict(R_COMMON), cpu=prof['cpu'],
                   heavy=(prof['heavy'] if heavy is None else heavy), settleMs=2500)
        return run_driver(port, cfg)
    finally:
        stop_chrome(proc, udd)


def violations(data):
    """把一档读数映射成违规清单（纯函数，便于反向验证）。"""
    v = []
    if not data or not data.get('ok'):
        return ['无读数：%s' % ((data or {}).get('error', 'unknown'))]
    if not data.get('loadedEvent'):
        v.append('load 事件未触发（页面未完成加载）')
    if not data.get('pfInstalled'):
        # 预注入采集器没装上 -> 错误/LCP/CLS 全不算数（未取证 ≠ 通过，U-221 教训）
        v.append('错误采集器未装载（__pf 缺失）：错误与 LCP 读数不可信')
    errs = (data.get('inPageErrors') or []) + (data.get('consoleErrors') or []) + (data.get('logErrors') or [])
    if errs:
        v.append('运行期错误 %d 条：%s' % (len(errs), ' | '.join(errs[:3])))
    t = data.get('timing') or {}
    if not t.get('fcp'):
        v.append('FCP 取不到（首屏无内容绘制）')
    elif t['fcp'] > FCP_BUDGET_MS:
        v.append('FCP %dms > 预算 %dms' % (t['fcp'], FCP_BUDGET_MS))
    if t.get('lcp') and t['lcp'] > LCP_BUDGET_MS:
        v.append('LCP %dms > 预算 %dms' % (t['lcp'], LCP_BUDGET_MS))
    ov = (data.get('overflow') or {}).get('delta', 0)
    if ov > OVERFLOW_TOL:
        v.append('横向溢出 %dpx' % ov)
    if (data.get('api') or {}).get('reqs'):
        # 静态面（本判据用的 TEST_HOST 不在 analytics 白名单内）不该发任何 /api 请求
        v.append('静态面发出 %d 个 /api 请求（analytics 域名白名单失效，验收判据 1 红线）'
                 % data['api']['reqs'])
    c = data.get('counts') or {}
    if (c.get('merch') or 0) < 8:
        v.append('文创件数 %s < 8（验收判据 2）' % c.get('merch'))
    if (c.get('arCards') or 0) != 3:
        v.append('AR 场景卡片 %s != 3' % c.get('arCards'))
    if (c.get('culture') or 0) < 3:
        v.append('畲族文化区块 %s < 3' % c.get('culture'))
    ph = data.get('phoenix') or {}
    if not ph.get('ready') or ph.get('state') in (None, 'none'):
        v.append('凤凰粒子引擎未就绪（state=%s）' % ph.get('state'))
    elif not ph.get('count'):
        v.append('凤凰粒子数为 0')
    elif not ph.get('fps'):
        v.append('凤凰动画 fps=0（首屏未播放）')
    return v


def ar_violations(data):
    """heavy 档的 AR / 旁白 / 降级违规（独立函数：这几条只在真·重档生效）。"""
    v = []
    ar = data.get('ar') or {}
    scenes = ar.get('scenes') or []
    if len(scenes) != 3:
        v.append('AR 三场景只取到 %d 个' % len(scenes))
    for s in scenes:
        tag = s.get('id')
        if s.get('mode') != 'gallery':
            v.append('%s：mode=%s（camera:false 应为 gallery）' % (tag, s.get('mode')))
        if not s.get('playing'):
            v.append('%s：未在播放' % tag)
        if not (s.get('t2', 0) > s.get('t1', 0) + MIN_T2_DELTA):
            v.append('%s：进度未推进（t1=%s t2=%s）' % (tag, s.get('t1'), s.get('t2')))
        if (s.get('fps') or 0) < MIN_FPS:
            v.append('%s：fps=%s < %d' % (tag, s.get('fps'), MIN_FPS))
        d1, d2 = s.get('draw1') or {}, s.get('draw2') or {}
        if (d1.get('colors') or 0) < 3:
            v.append('%s：画布采样仅 %s 种颜色（画面无内容）' % (tag, d1.get('colors')))
        if d1.get('sig') is not None and d1.get('sig') == d2.get('sig'):
            v.append('%s：两次采样画面完全相同（动画未在画）' % tag)
        ui = s.get('ui') or {}
        if not (ui.get('title') or '').strip():
            v.append('%s：场景标题为空' % tag)
        if not (ui.get('chapter') or '').strip():
            v.append('%s：章节标题为空' % tag)
        if (ui.get('bodyLen') or 0) < 20:
            v.append('%s：章节正文长度 %s < 20' % (tag, ui.get('bodyLen')))
    cam = ar.get('camera') or {}
    if cam.get('mode') != 'gallery':
        v.append('无摄像头时未降级到展柜模式（mode=%s，验收判据 8）' % cam.get('mode'))
    nr = ar.get('narration') or {}
    pre = nr.get('pre') or {}
    if pre.get('disabled'):
        if '不可用' not in (pre.get('text') or ''):
            v.append('旁白不可用时按钮文案未明示（%r）' % pre.get('text'))
    else:
        on = nr.get('on') or {}
        if on and str(on.get('pressed')) != 'true':
            v.append('旁白开启后 aria-pressed=%r 未同步' % on.get('pressed'))
        post = nr.get('post') or {}
        if post and str(post.get('pressed')) != 'false':
            v.append('旁白关闭后 aria-pressed=%r 未复位' % post.get('pressed'))
    return v


def fmt(data):
    t = (data or {}).get('timing') or {}
    e = (data or {}).get('env') or {}
    return 'FCP %sms / LCP %sms / DCL %sms / CLS %s / 传输 %sKB / %s 请求 / %dx%d@%s' % (
        t.get('fcp'), t.get('lcp'), t.get('dcl'), t.get('cls'), t.get('transferKB'),
        t.get('reqs'), e.get('vw'), e.get('vh'), e.get('dpr'))


SELFTEST_BAD = '''<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>bad-fixture</title>
<style>body{margin:0}.blow{width:2000px;height:40px;background:#333}</style></head><body>
<div class="blow">横向溢出 2000px 的元素</div>
<div id="ink">首屏内容</div>
<script>
// ① 阻塞主线程 3.2s：FCP 必然 > 3000ms 预算
var t0 = performance.now(); while (performance.now() - t0 < 3200) {}
// ② 未捕获错误：错误采集器必须抓到
setTimeout(function(){ throw new Error('selftest-intentional-error'); }, 60);
</script></body></html>'''

SELFTEST_GOOD = '''<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>good-fixture</title>
<style>body{margin:0}#ink{width:100%;height:40px;background:#eee}</style></head><body>
<div id="ink">首屏内容</div>
</body></html>'''


def write(path, content):
    full = os.path.join(BASE, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, 'w', encoding='utf-8').write(content)


def selftest(chrome, port):
    """双向自检：坏的必须全报，好的必须无违规。返回 (bad, good_viol, bad_viol) 供打印。"""
    write('_qa/preflight_selftest_bad.html', SELFTEST_BAD)
    write('_qa/preflight_selftest_good.html', SELFTEST_GOOD)
    prof = dict(PROFILES[0])
    good = probe_once(chrome, 'http://%s:%d/_qa/preflight_selftest_good.html?st=1' % (TEST_HOST, port), prof, heavy=False)
    bad = probe_once(chrome, 'http://%s:%d/_qa/preflight_selftest_bad.html?st=1' % (TEST_HOST, port), prof, heavy=False)
    gv = violations(good) if good and good.get('ok') else ['good 夹具无读数：%s' % ((good or {}).get('error'))]
    # 夹具页面没有站点结构，站点专属判据（文创/AR 卡片/粒子）不适用：只留「错误 + 溢出 + FCP」三条
    keep = ('运行期错误', '横向溢出', 'FCP', '首屏无内容绘制')
    bv = [x for x in violations(bad) if any(k in x for k in keep)]
    gv2 = [x for x in gv if any(k in x for k in keep)]
    return good, bad, gv2, bv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fast', action='store_true', help='只跑微信 iOS 一档')
    ap.add_argument('--selftest', action='store_true', help='只跑尺子自检')
    args = ap.parse_args()

    chrome = find_chrome()
    if not chrome:
        print('RESULT: SKIP  找不到 chrome.exe（真机前哨需要本地 chrome 做模拟面）')
        return 0
    if not os.path.exists(DRIVER):
        print('RESULT: FAIL  驱动缺失 tools/preflight_device.mjs')
        return 1

    httpd, port = start_server()
    try:
        print('chrome: %s  同源服务: 127.0.0.1:%d' % (os.path.basename(os.path.dirname(chrome)), port))

        print('[自检] 尺子双向验证（好夹具必须绿、坏夹具必须红）…')
        good, bad, gv, bv = selftest(chrome, port)
        if not (good and good.get('ok')) or not (bad and bad.get('ok')):
            print('RESULT: SKIP  自检无读数（good=%s bad=%s）' % (
                (good or {}).get('error'), (bad or {}).get('error')))
            return 0
        print('  好夹具 FCP %sms 违规 %d 条；坏夹具 FCP %sms 违规 %d 条' % (
            (good.get('timing') or {}).get('fcp'), len(gv),
            (bad.get('timing') or {}).get('fcp'), len(bv)))
        if gv:
            print('RESULT: FAIL  自检不通过（尺子误报，读数不可信）：' + ' | '.join(gv))
            return 1
        need = ['错误', '溢出', 'FCP']
        if not all(any(k in x for x in bv) for k in need):
            print('RESULT: FAIL  自检不通过（尺子漏报，读数不可信）：只报出 %r' % bv)
            return 1
        print('[PASS] 自检：坏夹具的错误/溢出/FCP 三条全部报出，好夹具零违规')
        if args.selftest:
            print('RESULT: PASS  尺子自检通过（--selftest 模式，未量产品）')
            return 0

        profs = PROFILES[:1] if args.fast else PROFILES
        fails, skips, rows = [], [], []
        for p in profs:
            url = 'http://%s:%d/site/index.html?pf=%s_%d' % (
                TEST_HOST, port, p['name'], random.randint(1000, 9999))
            print()
            print('--- profile: %s (%dx%d dpr%d cpu%dx%s) ---' % (
                p['name'], p['width'], p['height'], p['dpr'], p['cpu'], ' + AR深检' if p['heavy'] else ''))
            data = probe_once(chrome, url, p)
            if not data or not data.get('ok'):
                skips.append('%s：无读数（%s）' % (p['name'], (data or {}).get('error')))
                print('  [SKIP] 无读数：%s' % (data or {}).get('error'))
                continue
            rows.append((p['name'], data))
            print('  读数：' + fmt(data))
            v = violations(data)
            if p['heavy']:
                v += ar_violations(data)
            for x in v:
                print('  [FAIL] ' + x)
            if v:
                fails.append('%s：%d 条违规' % (p['name'], len(v)))
            else:
                print('  [PASS] 首屏预算 / 无错误 / 无溢出 / 区块计数 / 凤凰动画%s' % (
                    ' / AR 三场景 / 摄像头降级 / 旁白' if p['heavy'] else ''))
            if p['heavy']:
                for s in ((data.get('ar') or {}).get('scenes') or []):
                    print('  [INFO] %s：%s fps（4x 降频代理值）/ 进度 %.1f→%.1fs / 画面签名 %s→%s' % (
                        s.get('id'), s.get('fps'), s.get('t1') or 0, s.get('t2') or 0,
                        (s.get('draw1') or {}).get('sig'), (s.get('draw2') or {}).get('sig')))

        print()
        if fails:
            print('RESULT: FAIL  真机前哨（模拟面）%d/%d 档违规' % (len(fails), len(profs)))
            for f in fails:
                print('  -', f)
            return 1
        if skips and not rows:
            print('RESULT: SKIP  全部档位无读数（未取证 ≠ 通过）')
            for s in skips:
                print('  !', s)
            return 0
        if skips:
            print('RESULT: FAIL  部分档位无读数（未取证 ≠ 通过）')
            for s in skips:
                print('  !', s)
            return 1
        print('RESULT: PASS  %d 档模拟移动端全部达标（FCP 预算 %dms / 4G 限速 170ms·4Mbps / CPU 4x）'
              % (len(rows), FCP_BUDGET_MS))
        print('诚实边界：模拟只能证伪不能证实；WebKit/XWEB 内核差异与真机自动播放策略仍需真机一次点击自证。')
        return 0
    finally:
        httpd.shutdown()
        httpd.server_close()


if __name__ == '__main__':
    sys.path.insert(0, BASE)
    from tools.gate_stamp import record
    _t0 = time.time()
    _rc = main()
    record(__file__, {0: 'PASS', 1: 'FAIL'}.get(_rc, 'SKIP'), time.time() - _t0)
    sys.exit(_rc)
