# -*- coding: utf-8 -*-
import json, subprocess, time
PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
WD = r'C:\Users\37533\Desktop\workspace\项目\新建文件夹'
def ps(cmd, timeout=180):
    r = subprocess.run([PS,'-NoProfile','-Command',cmd],capture_output=True,text=True,cwd=WD,timeout=timeout,encoding='utf-8',errors='replace')
    return (r.stdout or '').strip()

# 打开首页（首屏），检查 statue-cut 是否已被请求
ps('agent-browser open "http://127.0.0.1:8791/?t1=1"')
ps('agent-browser wait --load networkidle')
time.sleep(2.5)
out = ps('agent-browser eval "JSON.stringify({statueReq: performance.getEntriesByType(\'resource\').filter(function(r){return r.name.indexOf(\'statue-cut\')>=0}).map(function(r){return Math.round(r.startTime)})})"')
print('首屏(未滚动):', out)

# 滚到雕刻台
ps('agent-browser eval "document.getElementById(\'carve-sec\').scrollIntoView();1"')
time.sleep(1.5)
out2 = ps('agent-browser eval "JSON.stringify({statueReq: performance.getEntriesByType(\'resource\').filter(function(r){return r.name.indexOf(\'statue-cut\')>=0}).map(function(r){return Math.round(r.startTime)}), carveP:(window.__carve&&window.__carve.stats())?window.__carve.stats().p:null})"')
print('滚到雕刻台后:', out2)
