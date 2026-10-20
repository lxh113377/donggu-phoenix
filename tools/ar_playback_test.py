
# -*- coding: utf-8 -*-
"""验证 AR 三段实际可播放（核心功能，之前只验证过入口存在）。"""
import json, subprocess, time
PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
WD = r'C:\Users\37533\Desktop\workspace\项目\新建文件夹'

def ps(cmd, timeout=50):
    try:
        r = subprocess.run([PS,'-NoProfile','-Command',cmd],capture_output=True,text=True,cwd=WD,timeout=timeout,encoding='utf-8',errors='replace')
        return ((r.stdout or '')+(r.stderr or '')).strip()
    except subprocess.TimeoutExpired:
        return 'TIMEOUT'

ps('agent-browser close')  # 不带 --all：并行端共用 daemon，--all 会杀掉对方会话; time.sleep(2)
ps('agent-browser set viewport 1440 900')
ps('agent-browser open "about:blank"'); time.sleep(0.4)
ps('agent-browser open "http://127.0.0.1:8791/"')
ps('agent-browser wait --load networkidle'); time.sleep(2.5)

# 1) 检查 AR 全局对象
out = ps('agent-browser eval "JSON.stringify({arApi:typeof window.__ar, arData:!!window.AR_DATA, scenes:(window.AR_DATA&&window.AR_DATA.scenes||[]).length})"')
print('1) AR 全局:', out[-200:])

# 2) 打开 AR
ps('agent-browser eval "var g=document.querySelector(\'.ar-card .go\'); if(g) g.click(); 1"')
time.sleep(2.5)
out2 = ps('agent-browser eval "JSON.stringify({dialog:!!document.querySelector(\'[role=dialog]\'), open:!!(window.__ar && window.__ar.stats && window.__ar.stats.open), scene:(window.__ar&&window.__ar.stats)?window.__ar.stats().scene:null, t:(window.__ar&&window.__ar.stats)?Math.round(window.__ar.stats().t*10)/10:null})"')
print('2) 打开后:', out2[-300:])

# 3) 等一会看是否在播放
time.sleep(3)
out3 = ps('agent-browser eval "JSON.stringify({scene:(window.__ar&&window.__ar.stats)?window.__ar.stats().scene:null, t:(window.__ar&&window.__ar.stats)?Math.round(window.__ar.stats().t*10)/10:null, playing:(window.__ar&&window.__ar.stats)?window.__ar.stats().playing:null, stamps:(window.__ar&&window.__ar.stats)?window.__ar.stats().stamps:null})"')
print('3) 3 秒后:', out3[-300:])
