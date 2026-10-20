
# -*- coding: utf-8 -*-
"""核实集章触发条件：是 seek 不触发，还是整个机制有缺陷？"""
import json, subprocess, time
PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
WD = r'C:\Users\37533\Desktop\workspace\项目\新建文件夹'

def ps(cmd, timeout=50):
    try:
        r = subprocess.run([PS,'-NoProfile','-Command',cmd],capture_output=True,text=True,cwd=WD,timeout=timeout,encoding='utf-8',errors='replace')
        return ((r.stdout or '')+(r.stderr or '')).strip()
    except subprocess.TimeoutExpired:
        return 'TIMEOUT'

# 干净重开 AR
ps('agent-browser close')  # 不带 --all：并行端共用 daemon，--all 会杀掉对方会话; time.sleep(2)
ps('agent-browser set viewport 1440 900')
ps('agent-browser open "about:blank"'); time.sleep(0.4)
ps('agent-browser open "http://127.0.0.1:8791/"')
ps('agent-browser wait --load networkidle'); time.sleep(2.2)
ps('agent-browser eval "if(window.__ar) window.__ar.open(\'phoenix\'); 1"')
time.sleep(2.0)

# phoenix 只有 36 秒，用 play + seek 到接近结尾，然后让它自然播完
ps('agent-browser eval "if(window.__ar){window.__ar.seek(34); window.__ar.play();} 1"')
time.sleep(4.0)

o = ps('agent-browser eval "JSON.stringify({t:(window.__ar&&window.__ar.stats)?Math.round(window.__ar.stats().t*10)/10:null, playing:(window.__ar&&window.__ar.stats)?window.__ar.stats().playing:null, stamps:(window.__ar&&window.__ar.stats)?window.__ar.stats().stamps:[], got:document.querySelectorAll(\'.stamp.got\').length})"')
print('phoenix 播到结尾后:', o[-300:])
