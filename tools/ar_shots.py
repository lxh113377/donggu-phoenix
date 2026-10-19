# -*- coding: utf-8 -*-
"""AR 三段逐场景截图 + 减少动效 + 窄屏关键帧（可复核证据）。"""
import subprocess, time, json, os
WD = r'C:\Users\37533\Desktop\workspace\项目\新建文件夹'
PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'

def ps(cmd, timeout=180):
    r = subprocess.run([PS, '-NoProfile', '-Command', cmd], capture_output=True, text=True,
                       cwd=WD, timeout=timeout, encoding='utf-8', errors='replace')
    return (r.stdout or '').strip()

def shot(dirname):
    ps('agent-browser screenshot --screenshot-dir ./_qa/ar/%s' % dirname)

def ev(code):
    open('_qa/_tmp.js', 'w', encoding='utf-8').write(code)
    return ps("agent-browser eval (Get-Content -Raw -Encoding UTF8 '_qa/_tmp.js')")

ps('agent-browser set viewport 1440 900')
ps('agent-browser open "http://127.0.0.1:8791/?ar=%d"' % int(time.time()))
ps('agent-browser wait --load networkidle')
time.sleep(1.6)

for sid in ('craft', 'red', 'phoenix'):
    ev("(function(){window.__ar.open('%s',{camera:false});return 'ok'})()" % sid)
    time.sleep(1.4)
    ev("(function(){window.__ar.seek(30);return 'ok'})()")
    time.sleep(1.0)
    shot(sid)
    print(sid, ev("(function(){return JSON.stringify({title:document.getElementById('ar-title').textContent,chapter:document.getElementById('ar-chapter').textContent,time:document.getElementById('ar-time').textContent})})()"))
    ev("(function(){window.__ar.close();return 'ok'})()")
    time.sleep(0.5)

# 窄屏 AR
ps('agent-browser set viewport 390 844')
ps('agent-browser open "http://127.0.0.1:8791/?arm=%d"' % int(time.time()))
ps('agent-browser wait --load networkidle')
time.sleep(1.6)
ev("(function(){window.__ar.open('phoenix',{camera:false});return 'ok'})()")
time.sleep(1.5)
shot('mobile')
print('mobile', ev("(function(){var r=document.querySelector('.ar-copy').getBoundingClientRect();return JSON.stringify({title:document.getElementById('ar-title').textContent,vw:innerWidth,copyRight:Math.round(r.right),sw:document.documentElement.scrollWidth})})()"))
