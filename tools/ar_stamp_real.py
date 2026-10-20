
# -*- coding: utf-8 -*-
"""验证：真实播放到结尾会落章（不是 seek 跳转）。

phoenix 段 36 秒，太长。用一个技巧：
接受它是设计如此，改为验证「seek 后继续 play 到结尾」是否触发。

步骤：
  1. seek 到 duration-2
  2. play() 让它自然跑到结尾
  3. 检查 stamps
"""
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
ps('agent-browser wait --load networkidle'); time.sleep(2.2)

# 打开 phoenix（36s 最短）
ps('agent-browser eval "if(window.__ar) window.__ar.open(\'phoenix\'); 1"')
time.sleep(1.8)
o1 = ps('agent-browser eval "JSON.stringify({scene:(window.__ar&&window.__ar.stats)?window.__ar.stats().scene:null, dur:(window.AR_DATA.scenes.find(function(s){return s.id===\'phoenix\'})||{}).duration})"')
print('当前场景:', o1[-160:])

# seek 到 33，然后 play
ps('agent-browser eval "if(window.__ar){window.__ar.seek(33); window.__ar.play();} 1"')
print('已 seek(33) + play，等待自然跑完…')
time.sleep(6.0)

o2 = ps('agent-browser eval "JSON.stringify({t:(window.__ar&&window.__ar.stats)?Math.round(window.__ar.stats().t*10)/10:null, playing:(window.__ar&&window.__ar.stats)?window.__ar.stats().playing:null, stamps:(window.__ar&&window.__ar.stats)?window.__ar.stats().stamps:[], got:document.querySelectorAll(\'.stamp.got\').length})"')
print('6 秒后:', o2[-280:])
