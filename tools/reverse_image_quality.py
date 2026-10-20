
# -*- coding: utf-8 -*-
"""反向验证 image_quality_test：人为把图片拉变形，判据应能识别。

做法：滚到 merch 后，用 JS 强行改一张图的宽高比（模拟真实变形缺陷），
再用同一判据检查，确认能读出 distort。
"""
import json, subprocess, time
PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
WD = r'C:\Users\37533\Desktop\workspace\项目\新建文件夹'

def ps(cmd, timeout=45):
    try:
        r = subprocess.run([PS,'-NoProfile','-Command',cmd],capture_output=True,text=True,cwd=WD,timeout=timeout,encoding='utf-8',errors='replace')
        return ((r.stdout or '')+(r.stderr or '')).strip()
    except subprocess.TimeoutExpired:
        return 'TIMEOUT'

ps('agent-browser open "http://127.0.0.1:8791/?dist=%d"' % int(time.time()))
ps('agent-browser wait --load networkidle')
time.sleep(2.0)
ps('agent-browser eval "document.getElementById(\'merch\').scrollIntoView();1"')
time.sleep(2.2)

# 破坏：把第一张商品图强制拉成 2:1（明显变形）
ps('agent-browser eval "var i=document.querySelector(\'.merch-item .merch-shot img\');i.style.maxHeight=\'none\';i.style.width=\'200px\';i.style.height=\'80px\';1"')
time.sleep(0.6)

JS = ("JSON.stringify((function(){var bad=[];"
      "[].slice.call(document.images).forEach(function(img){"
      "var r=img.getBoundingClientRect();if(r.width<=0||r.height<=0)return;"
      "var nw=img.naturalWidth,nh=img.naturalHeight;if(!img.complete||nw===0)return;"
      "var nr=nw/nh,dr=r.width/r.height;var d=Math.abs(nr-dr)/nr;"
      "if(d>0.05)bad.push({src:img.src.split('/').pop(),distort:Math.round(d*1000)/10});});"
      "return {badCount:bad.length,bad:bad};})())")
open(WD + r'\_qa\_dist.js', 'w', encoding='utf-8').write(JS)
out = ps('agent-browser eval (Get-Content -Raw -Encoding UTF8 "%s")' % (WD + r'\_qa\_dist.js'))
print('破坏后检查结果:', out[-300:])
print()
print('badCount>0 表示判据能识别变形。')
