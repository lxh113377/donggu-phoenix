
# -*- coding: utf-8 -*-
"""直接验证：改 CSS 后，浏览器里 --fg-dim 的计算值是否变了。"""
import os, re, subprocess, sys, time

WD = r'C:\Users\37533\Desktop\workspace\项目\新建文件夹'
CSS = os.path.join(WD, 'site/assets/css/main.css')
PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'

def ps(cmd, timeout=60):
    r = subprocess.run([PS,'-NoProfile','-Command',cmd],capture_output=True,text=True,cwd=WD,timeout=timeout,encoding='utf-8',errors='replace')
    return ((r.stdout or '')+(r.stderr or '')).strip()

orig = open(CSS, encoding='utf-8', newline='').read()
try:
    broken = re.sub(r'--fg-dim:\s*[^;}]+', '--fg-dim:#12100E', orig)
    open(CSS, 'w', encoding='utf-8', newline='').write(broken)
    ps('$j = Get-Content -Raw -Encoding UTF8 "_qa/clear_sw.js"; agent-browser eval $j')
    time.sleep(0.8)
    ps('agent-browser open "http://127.0.0.1:8791/?chk=%d"' % int(time.time()))
    ps('agent-browser wait --load networkidle')
    time.sleep(2.0)
    out = ps('agent-browser eval "JSON.stringify({fgDim:getComputedStyle(document.documentElement).getPropertyValue(\'--fg-dim\').trim(), sampleColor:getComputedStyle(document.querySelector(\'.merch-item p\')||document.body).color})"')
    print('破坏后浏览器读数:', out[-300:])
finally:
    open(CSS, 'w', encoding='utf-8', newline='').write(orig)
    ps('git checkout -- site/assets/css/main.css')
    print('已还原')
