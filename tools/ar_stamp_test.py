
# -*- coding: utf-8 -*-
"""验证：完整播放一段后是否能落章。"""
import json, subprocess, time
PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
WD = r'C:\Users\37533\Desktop\workspace\项目\新建文件夹'

def ps(cmd, timeout=50):
    try:
        r = subprocess.run([PS,'-NoProfile','-Command',cmd],capture_output=True,text=True,cwd=WD,timeout=timeout,encoding='utf-8',errors='replace')
        return ((r.stdout or '')+(r.stderr or '')).strip()
    except subprocess.TimeoutExpired:
        return 'TIMEOUT'

# 检查 API
o = ps('agent-browser eval "JSON.stringify({keys:Object.keys(window.__ar||{})})"')
print('AR API keys:', o[-250:])

# 直接推进时间到段末，看是否落章
ps('agent-browser eval "var b=document.querySelector(\'.ar-dots button[data-scene=\\\'craft\\\']\'); if(b) b.click(); 1"')
time.sleep(1.2)
# 找 seek/完成接口
o2 = ps('agent-browser eval "JSON.stringify({hasSeek:typeof (window.__ar&&window.__ar.seek), hasComplete:typeof (window.__ar&&window.__ar.complete), hasPlay:typeof (window.__ar&&window.__ar.play)})"')
print('可用的控制方法:', o2[-250:])

# 若有 seek 则跳到段末
ps('agent-browser eval "if(window.__ar && window.__ar.seek) window.__ar.seek(70); 1"')
time.sleep(1.5)
o3 = ps('agent-browser eval "JSON.stringify({t:(window.__ar&&window.__ar.stats)?Math.round(window.__ar.stats().t*10)/10:null, stamps:(window.__ar&&window.__ar.stats)?window.__ar.stats().stamps:[], got:document.querySelectorAll(\'.stamp.got\').length})"')
print('推进后:', o3[-250:])
