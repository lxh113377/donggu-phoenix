
# -*- coding: utf-8 -*-
"""验证 AR 三段可切换 + 集章逻辑。"""
import json, subprocess, time
PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
WD = r'C:\Users\37533\Desktop\workspace\项目\新建文件夹'

def ps(cmd, timeout=50):
    try:
        r = subprocess.run([PS,'-NoProfile','-Command',cmd],capture_output=True,text=True,cwd=WD,timeout=timeout,encoding='utf-8',errors='replace')
        return ((r.stdout or '')+(r.stderr or '')).strip()
    except subprocess.TimeoutExpired:
        return 'TIMEOUT'

# 已在 AR 内，检查场景切换按钮
out = ps('agent-browser eval "JSON.stringify([].slice.call(document.querySelectorAll(\'.ar-dots button\')).map(function(b){return {scene:b.getAttribute(\'data-scene\'), sel:b.getAttribute(\'aria-selected\')}}))"')
print('场景切换按钮:', out[-300:])

# 逐个切换
for sid in ['red', 'phoenix', 'craft']:
    ps('agent-browser eval "var b=document.querySelector(\'.ar-dots button[data-scene=\\\'%s\\\']\'); if(b) b.click(); 1"' % sid)
    time.sleep(1.6)
    o = ps('agent-browser eval "JSON.stringify({scene:(window.__ar&&window.__ar.stats)?window.__ar.stats().scene:null, t:(window.__ar&&window.__ar.stats)?Math.round(window.__ar.stats().t*10)/10:null})"')
    print('切换 %-8s ->' % sid, o[-130:])

# 集章机制
o2 = ps('agent-browser eval "JSON.stringify({stamps:(window.__ar&&window.__ar.stats)?window.__ar.stats().stamps:[], stampEls:document.querySelectorAll(\'.stamp\').length, gotEls:document.querySelectorAll(\'.stamp.got\').length})"')
print()
print('集章状态:', o2[-250:])
