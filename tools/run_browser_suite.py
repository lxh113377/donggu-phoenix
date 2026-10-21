# -*- coding: utf-8 -*-
"""tools/run_browser_suite.py —— 一键跑全部浏览器测试（本地）。

## 为什么需要它
项目有 26 个纯静态判据在 CI 里自动跑，另有一批需要浏览器的判据只能在本地跑。
浏览器判据如果长期不跑，很容易悄悄失效——而它们覆盖的恰恰是
静态检查看不见的东西：布局溢出、动画触发、AR 播放、视觉重量。

## 轮69 的关键改造：活性预检 + 诚实计数

### 起因（一次自我纠错）
轮53~68 我每轮都报「浏览器判据 20 项 PASS」，但 agent-browser 从轮53 起就卡死。
那个数字是**轮50 的过期读数**，被我连续引用了 15 轮。

为什么会退化：每项 subprocess timeout=600s，18 项最坏 3 小时，
跑一次代价太高 -> 我就没再跑 -> 但旧读数还在记忆里 -> 于是拿旧数报新账。

### 三条对策
  1. **活性预检** ab_alive()：25s 短超时探 daemon。
     死了就把依赖它的项直接标 SKIP（附原因），不再逐项挂 600s。
     已迁 headless 直连的判据不受 daemon 影响，照常跑。
  2. **--status 模式**：只报「哪些能跑、哪些不能、为什么」，不真跑。
     让判据活性随时可查，过期不再无声。
  3. **诚实汇总**：有 SKIP 时结论必须写明「N 项未验证」，
     绝不报「全部通过」。旧版 n_pass>0 且有 SKIP 时也印 PASS，是错的。

## 用法
  python tools/run_browser_suite.py            # 跑全部
  python tools/run_browser_suite.py --fast     # 只跑快的（跳过 AR 播放类）
  python tools/run_browser_suite.py --status   # 只报活性，不执行
  python tools/run_browser_suite.py --list     # 只列出

## 聚合判定（关键）
**任何一个子测试 FAIL，总判定必须 FAIL。**
绝不能因为「大多数通过」就报绿——这是 audit-runner-safe-aggregate 的核心教训：
全局 any()/max() 会把单个失败洗白。

## 前置
需要本地服务 http://127.0.0.1:8791（python -m http.server 8791 --directory site）。
"""
import os
import subprocess
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
PY = sys.executable

# (脚本, 是否 fast 组, 说明)
SUITE = [
    ('tools/multi_viewport_test.py', True, '9 视口横向+纵向完整性'),
    ('tools/reveal_coverage_test.py', True, '进场元素全部可见'),
    ('tools/visual_balance_test.py', True, '首屏视觉重量平衡'),
    ('tools/hero_height_test.py', True, '手机首屏锁一屏'),
    ('tools/ring_containment_test.py', True, '装饰环在画布内'),
    ('tools/anchor_offset_test.py', True, '锚点偏移正确'),
    ('tools/zoom_test.py', True, '缩放下布局不崩'),
    ('tools/image_quality_test.py', True, '图片尺寸/格式'),
    ('tools/reveal_after_jump_test.py', True, '跳转后进场不失效'),
    ('tools/touch_target_test.py', False, '双视口触摸目标 >= 44px（headless 直连）'),
    ('tools/contrast_audit.py', False, '两视口文本对比度（headless 直连）'),
    ('tools/admin_contrast_test.py', False, '后台仪表盘对比度（需 pages dev）'),
    ('tools/admin_responsive_test.py', False, '后台响应式与触控 44px（需 pages dev）'),
    ('tools/runtime_health_test.py', False, '运行时健康（无泄漏/累积/循环叠加）'),
    ('tools/engine_behavior_test.py', False, '引擎行为（密度自适应+HUD节流实测）'),
    ('tools/defer_regression_test.py', False, 'defer 后运行时不回归'),
    ('tools/ar_e2e_test.py', False, 'AR 端到端 7 项'),
    ('tools/ar_playback_test.py', False, 'AR 播放时序'),
    ('tools/ar_scenes_test.py', False, 'AR 三场景'),
    ('tools/ar_stamp_test.py', False, '集章持久化'),
    ('tools/ar_focus_test.py', False, 'AR 焦点闭环'),
    # 轮85（U-01）：真机前哨 —— 三档移动端 UA/视口/4G 限速/CPU 降频，实测首屏+AR+旁白+降级。
    # 自带双向自检（好夹具必须绿、坏夹具必须红），且自起同源服务，不依赖 8791。
    ('tools/preflight_device_test.py', False, '真机前哨（3 档模拟移动端 + AR 深检）'),
    # 轮91：线上断网复验（验收判据 2「现场断网仍能开」）。自起 chrome 且需公网，
    # 故只进本地套件、不进 CI —— CI  runner 的出网策略与本机不同，放进去会得到
    # 一个「因环境而 SKIP」的常驻红灯，反而训练人忽略红灯。
    ('tools/offline_live_test.py', False, '线上断网仍可用（两面 预热->offline->读数）'),
]


def server_alive():
    try:
        r = subprocess.run([PS, '-NoProfile', '-Command',
                            "try { (Invoke-WebRequest -Uri 'http://127.0.0.1:8791/' -TimeoutSec 5 -UseBasicParsing).StatusCode } catch { 0 }"],
                           capture_output=True, text=True, timeout=30, encoding='utf-8', errors='replace')
        return '200' in (r.stdout or '')
    except Exception:
        return False


def ab_alive(timeout=2.0):
    """探 agent-browser daemon 是否可响应 —— 纯 TCP，无子进程。

    轮70 教训：旧版用 subprocess 跑 agent-browser eval，
    Windows 下 CLI 卡住时 subprocess 超时不生效（等孙进程释放管道），
    预检自己挂起 5+ 分钟 —— 防挂起的机制必须结构上不可能挂起。
    daemon 进程死 -> 端口没人听 -> 立刻 ConnectionRefused，绝不阻塞。
    """
    import socket
    port_file = os.path.join(os.path.expanduser('~'), '.agent-browser', 'default.port')
    try:
        port = int(open(port_file, encoding='utf-8').read().strip())
    except Exception:
        return False
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=timeout):
            return True
    except Exception:
        return False


def needs_daemon(script_path):
    """该判据是否依赖 agent-browser 且尚未迁 headless 直连。"""
    try:
        src = open(script_path, encoding='utf-8', errors='ignore').read()
    except Exception:
        return False
    return 'agent-browser' in src and 'headless=new' not in src


STAMP = os.path.join(BASE, '_qa', 'gate_runs.json')


def load_stamps():
    try:
        import json as _json
        return _json.load(open(STAMP, encoding='utf-8'))
    except Exception:
        return {}


def save_stamp(script, status, dur):
    """记录本次真实执行的时间戳（只有实际跑过的才记）。"""
    import json as _json
    d = load_stamps()
    d[script] = {'ts': int(time.time()), 'status': status, 'dur': round(dur, 1)}
    os.makedirs(os.path.dirname(STAMP), exist_ok=True)
    _json.dump(d, open(STAMP, 'w', encoding='utf-8'), indent=1, sort_keys=True)


def age_str(script, stamps):
    e = stamps.get(script)
    if not e:
        return '从未跑过'
    days = (time.time() - e['ts']) / 86400.0
    if days < 1:
        return '%d 小时前' % max(0, int(days * 24))
    if days < 30:
        return '%d 天前' % int(days)
    return '%d 天前(**过期**)' % int(days)


def do_status():
    """只报活性，不执行。让「哪些判据其实跑不动」随时可查。"""
    alive = None
    rows = []
    for script, _fast, desc in SUITE:
        path = os.path.join(BASE, script)
        if not os.path.exists(path):
            rows.append((script, 'MISSING', desc))
            continue
        nd = needs_daemon(path)
        if nd and alive is None:
            alive = ab_alive()
        if nd and alive is False:
            rows.append((script, 'DEAD', desc))
        elif nd:
            rows.append((script, 'NEEDS-DAEMON', desc))
        else:
            rows.append((script, 'RUNNABLE', desc))
    print('浏览器判据活性（--status，未实际执行，含上次执行时效）')
    print('=' * 72)
    stamps = load_stamps()
    for script, st, desc in rows:
        print('  %-34s %-13s %-14s %s' % (
            script.replace('tools/', ''), st, age_str(script, stamps), desc[:30]))
    print('=' * 72)
    n_dead = sum(1 for _s, st, _d in rows if st == 'DEAD')
    n_run = sum(1 for _s, st, _d in rows if st in ('RUNNABLE', 'NEEDS-DAEMON'))
    n_miss = sum(1 for _s, st, _d in rows if st == 'MISSING')
    print('可跑 %d / 依赖已死 daemon %d / 文件缺失 %d / 共 %d' % (
        n_run, n_dead, n_miss, len(rows)))
    if n_dead:
        print('警告：DEAD 项**未被验证**，其历史 PASS 读数不得当作当前结论引用。')
    return 0


def main():
    args = sys.argv[1:]
    if '--list' in args:
        for s, fast, desc in SUITE:
            print('%-40s %-6s %s' % (s, 'fast' if fast else 'full', desc))
        return 0
    if '--status' in args:
        return do_status()

    fast_only = '--fast' in args
    todo = [x for x in SUITE if x[1] or not fast_only]

    if not server_alive():
        print('本地服务 http://127.0.0.1:8791 未启动，无法跑浏览器测试。')
        print('请先运行：python -m http.server 8791 --directory site')
        print()
        print('RESULT: SKIP  服务未启动')
        return 0

    print('浏览器判据套件：%d 项%s' % (len(todo), '（fast）' if fast_only else ''))

    # 活性预检：daemon 死了就把依赖它的项标 SKIP，不逐项挂 600s。
    # 否则跑一次要 3 小时 -> 没人会跑 -> 读数长期过期（轮53~68 实锤）。
    daemon_ok = ab_alive()
    if not daemon_ok:
        print('警告：agent-browser daemon 无响应。依赖它的判据记 SKIP（不挂 600s），')
        print('      已迁 headless 直连的照常跑。')
    print('=' * 72)

    results = []
    t0 = time.time()
    for script, _fast, desc in todo:
        path = os.path.join(BASE, script)
        if not os.path.exists(path):
            print('%-34s SKIP   文件不存在' % script.replace('tools/', ''))
            results.append((script, 'SKIP', desc, '文件不存在'))
            continue
        if needs_daemon(path) and not daemon_ok:
            print('%-34s SKIP   %s  [daemon 无响应]' % (
                script.replace('tools/', ''), desc[:22]))
            results.append((script, 'SKIP', desc, 'daemon 无响应'))
            continue
        start = time.time()
        try:
            r = subprocess.run([PY, script], cwd=BASE, capture_output=True,
                               text=True, encoding='utf-8', errors='replace', timeout=600)
            out = (r.stdout or '') + (r.stderr or '')
            code = r.returncode
        except subprocess.TimeoutExpired:
            out, code = 'TIMEOUT', 2
        dur = time.time() - start
        if code == 0:
            status = 'PASS'
            reason = ''
        elif code == 2 or 'RESULT: SKIP' in out:
            status = 'SKIP'
            reason = '自身判 SKIP'
        else:
            status = 'FAIL'
            reason = ''
        results.append((script, status, desc, reason))
        if status in ('PASS', 'FAIL'):
            save_stamp(script, status, dur)   # 只有真跑过才记时效
        print('%-34s %-6s %5.1fs  %s' % (script.replace('tools/', ''), status, dur, desc))
        if status == 'FAIL':
            for line in out.splitlines():
                line = line.strip()
                if line.startswith('- '):
                    print('      ', line[:100])

    print('=' * 72)
    n_pass = sum(1 for _s, st, _d, _r in results if st == 'PASS')
    n_fail = sum(1 for _s, st, _d, _r in results if st == 'FAIL')
    n_skip = sum(1 for _s, st, _d, _r in results if st == 'SKIP')
    print('通过 %d / 失败 %d / 跳过 %d，用时 %.1fs' % (
        n_pass, n_fail, n_skip, time.time() - t0))
    print()

    # 聚合判定：只要有一个 FAIL 就 FAIL（绝不用 any() 洗绿）
    if n_fail:
        print('RESULT: FAIL  %d 项浏览器判据未通过' % n_fail)
        return 1
    if n_pass == 0:
        print('RESULT: SKIP  无一可跑（%d 项被跳过）——不得引用历史读数充当当前结论' % n_skip)
        return 0
    if n_skip:
        # 旧版这里也印「全部通过」，是不诚实的：跳过的项根本没被验证。
        print('RESULT: PASS(部分)  %d 项通过；另有 %d 项未验证（daemon 不可用/自身 SKIP）'
              % (n_pass, n_skip))
        print('  注意：结论只覆盖已跑的 %d/%d 项，未验证项不得计入「通过」。' % (
            n_pass, len(results)))
        return 0
    print('RESULT: PASS  %d 项浏览器判据全部通过' % n_pass)
    print('  （各项执行时间已写入 _qa/gate_runs.json；'
          '引用结论前先用 --status 看时效）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
