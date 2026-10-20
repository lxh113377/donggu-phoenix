# -*- coding: utf-8 -*-
"""tools/browser_health.py —— agent-browser 环境静态自检。

轮13 我把 daemon 报错判成「环境故障」，真实根因是我执行了
  Remove-Item -Recurse $env:USERPROFILE\.agent-browser
而那个目录**不只是配置，还装着 Chrome 本体**（browsers/chrome-xxx）。
删掉后报 Chrome not found；我当时归因成软件缺陷，白绕了一轮。

本工具只做**静态**检查（不打开页面，避免自身超时误导判断）：
  进程残留 / Chrome 本体存在 / 安装版本信息。
是否真能开页面，仍由真实使用来暴露；但至少能立刻区分
「程序本体没了」和「进程冲突」这两类完全不同的故障。
"""
import os
import subprocess
import sys

PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME = os.path.expanduser('~')


def ps(cmd, timeout=30):
    try:
        r = subprocess.run([PS, '-NoProfile', '-Command', cmd], capture_output=True, text=True,
                           cwd=BASE, timeout=timeout, encoding='utf-8', errors='replace')
        return ((r.stdout or '') + (r.stderr or '')).strip()
    except subprocess.TimeoutExpired:
        return 'TIMEOUT'


def main():
    do_fix = '--fix' in sys.argv
    fails = []
    print('=== agent-browser 环境静态检查 ===')

    # 1) 残留进程
    out = ps('Get-Process | Where-Object { $_.ProcessName -match "agent-browser" } | Measure-Object | Select-Object -ExpandProperty Count')
    n = int(out) if out.isdigit() else 0
    print('[进程] 残留 agent-browser 进程: %d' % n)
    if n > 3:
        fails.append(('procs', '进程偏多(%d)，可能有僵尸；可 taskkill /F /IM agent-browser-win32-x64.exe' % n))

    # 2) Chrome 本体
    root = os.path.join(HOME, '.agent-browser', 'browsers')
    exe = None
    if os.path.isdir(root):
        for d in sorted(os.listdir(root)):
            if d.startswith('chrome'):
                for sub in ('chrome-win64', ''):
                    cand = os.path.join(root, d, sub, 'chrome.exe') if sub else os.path.join(root, d, 'chrome.exe')
                    if os.path.exists(cand):
                        exe = cand
                        break
            if exe:
                break
    print('[Chrome] 安装根目录: %s (%s)' % (root, '存在' if os.path.isdir(root) else '不存在'))
    print('[Chrome] 可执行文件: %s' % (exe or '缺失'))
    if not exe:
        fails.append(('chrome_missing', 'Chrome 本体缺失 → 执行 agent-browser install（约200MB，需数分钟）'))

    # 3) 版本
    ver = ps('agent-browser --version 2>&1')
    if 'agent-browser' in ver:
        print('[版本] %s' % ver.splitlines()[-1].strip()[:60])

    print()
    if not fails:
        print('RESULT: PASS  环境静态检查通过（Chrome 本体在、进程数正常）')
        return 0
    print('RESULT: FAIL  %d 个问题' % len(fails))
    for code, action in fails:
        print('  - [%s] %s' % (code, action))
    if do_fix and any(c == 'chrome_missing' for c, _ in fails):
        print()
        print('执行 agent-browser install ...')
        subprocess.run([PS, '-NoProfile', '-Command', 'agent-browser install'], cwd=BASE, timeout=900)
    return 1


if __name__ == '__main__':
    sys.exit(main())