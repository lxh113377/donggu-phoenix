# -*- coding: utf-8 -*-
'''反向验证 defer_regression_test：把某个脚本顺序打乱，应判红。

思路：把 main.js 移到 phoenix.js 之前（破坏依赖），
main.js 依赖 window.Phoenix，会失败。
用 safe_mutation 沙箱改，服务读真实目录 —— 所以这次要改真实文件再还原。
'''
import os, re, subprocess, sys, time

WD = r'C:\Users\37533\Desktop\workspace\项目\新建文件夹'
HTML = os.path.join(WD, 'site/index.html')
PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'

def ps(cmd, timeout=60):
    r = subprocess.run([PS,'-NoProfile','-Command',cmd],capture_output=True,text=True,cwd=WD,timeout=timeout,encoding='utf-8',errors='replace')
    return ((r.stdout or '')+(r.stderr or ''))

st = ps('git status --porcelain site/index.html').strip()
if st:
    print('工作区不干净，中止:', st[:80])
    sys.exit(1)

orig = open(HTML, encoding='utf-8', newline='').read()
try:
    # 破坏：把 main.js 移到最前面（phoenix.js 之前）
    main_tag = '<script src="assets/js/main.js" defer></script>'
    if main_tag not in orig:
        print('未找到 main.js 标签')
        sys.exit(1)
    broken = orig.replace(main_tag, '', 1)
    # 插到第一个 script 之前
    first = broken.find('<script src="assets/data/culture.js"')
    broken = broken[:first] + main_tag + chr(10) + broken[first:]
    open(HTML, 'w', encoding='utf-8', newline='').write(broken)
    print('已打乱: main.js 移到最前')
    time.sleep(0.5)
    r = subprocess.run([sys.executable, 'tools/defer_regression_test.py'], cwd=WD,
                       capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=180)
    out = (r.stdout or '') + (r.stderr or '')
    print('退出码:', r.returncode)
    for l in out.splitlines():
        if 'PASS]' in l or 'FAIL]' in l or 'RESULT' in l or l.strip().startswith('- '):
            print('  ', l.strip()[:90])
finally:
    open(HTML, 'w', encoding='utf-8', newline='').write(orig)
    print()
    print('已还原:', ps('git status --porcelain site/index.html').strip() or '干净')