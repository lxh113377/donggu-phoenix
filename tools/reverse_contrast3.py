
# -*- coding: utf-8 -*-
"""正确的反向验证：改 CSS 的同时改 --build 与 BUILD 常量，
让版本对账守卫不触发重载，而是接受新 CSS。
（或者更简单：改完 CSS 后清 sessionStorage + 硬刷新）
"""
import os, re, subprocess, sys, time

WD = r'C:\Users\37533\Desktop\workspace\项目\新建文件夹'
CSS = os.path.join(WD, 'site/assets/css/main.css')
PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'

def ps(cmd, timeout=60):
    r = subprocess.run([PS,'-NoProfile','-Command',cmd],capture_output=True,text=True,cwd=WD,timeout=timeout,encoding='utf-8',errors='replace')
    return ((r.stdout or '')+(r.stderr or '')).strip()

orig = open(CSS, encoding='utf-8', newline='').read()
try:
    # 1) 改 --fg-dim 为接近背景色
    broken = re.sub(r'--fg-dim:\s*[^;}]+', '--fg-dim:#12100E', orig)
    # 2) 同时清空 sessionStorage（让守卫不因防循环而放弃）
    open(CSS, 'w', encoding='utf-8', newline='').write(broken)

    ps('$j = Get-Content -Raw -Encoding UTF8 "_qa/clear_sw.js"; agent-browser eval $j')
    time.sleep(0.8)
    # 用全新 session：先访问 about:blank 清 sessionStorage 再进
    ps('agent-browser open "about:blank"')
    time.sleep(0.4)
    ps('agent-browser open "http://127.0.0.1:8791/"')
    ps('agent-browser wait --load networkidle')
    time.sleep(3.0)   # 给对账守卫重载留时间
    ps('agent-browser wait --load networkidle')
    time.sleep(1.5)

    out = ps('agent-browser eval "JSON.stringify({fgDim:getComputedStyle(document.documentElement).getPropertyValue(\'--fg-dim\').trim()})"')
    print('破坏后 fgDim =', out[-120:])

    r = subprocess.run([sys.executable, 'tools/contrast_audit.py'], cwd=WD,
                       capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=200)
    o = (r.stdout or '') + (r.stderr or '')
    print('工具退出码:', r.returncode)
    for l in o.splitlines():
        if 'RESULT' in l or '不达标' in l or l.strip().startswith('- '):
            print('  ', l.strip()[:110])
finally:
    open(CSS, 'w', encoding='utf-8', newline='').write(orig)
    ps('git checkout -- site/assets/css/main.css')
    print()
    print('还原:', ps('git status --porcelain site/assets/css/main.css') or '干净')
