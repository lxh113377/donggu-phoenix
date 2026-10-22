# -*- coding: utf-8 -*-
import json, subprocess, time
PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
WD = r'C:\Users\37533\Desktop\workspace\项目\新建文件夹'
def ps(cmd, timeout=180):
    r = subprocess.run([PS,'-NoProfile','-Command',cmd],capture_output=True,text=True,cwd=WD,timeout=timeout,encoding='utf-8',errors='replace')
    return (r.stdout or '').strip()

ps('agent-browser open "http://127.0.0.1:8791/?lazy=1"')
ps('agent-browser wait --load networkidle')
time.sleep(2)
print('1) 首屏:', ps('agent-browser eval "JSON.stringify({req:performance.getEntriesByType(\'resource\').filter(function(r){return r.name.indexOf(\'statue-cut\')>=0}).length})"'))

# 推到 0.7（进入揭示区）
ps('agent-browser eval "document.getElementById(\'carve-sec\').scrollIntoView();1"')
time.sleep(0.8)
ps('agent-browser eval "window.__carve.set(0.7); window.__carve.play(false); 1"')
time.sleep(2.2)
print('2) 推到 0.7 后:', ps('agent-browser eval "JSON.stringify({req:performance.getEntriesByType(\'resource\').filter(function(r){return r.name.indexOf(\'statue-cut\')>=0}).map(function(r){return Math.round(r.startTime)}), ready:(window.__carve&&window.__carve.stats)?window.__carve.stats():null, imgReady: (function(){try{return !!document.querySelector(\'canvas\')}catch(e){return null}})()})"'))
ps('agent-browser screenshot "./_qa/r3/lazy-reveal.png"')
