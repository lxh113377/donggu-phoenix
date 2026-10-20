# -*- coding: utf-8 -*-
import json, subprocess, time
PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
WD = r'C:\Users\37533\Desktop\workspace\项目\新建文件夹'
def ps(cmd, timeout=180):
    r = subprocess.run([PS,'-NoProfile','-Command',cmd],capture_output=True,text=True,cwd=WD,timeout=timeout,encoding='utf-8',errors='replace')
    return (r.stdout or '').strip()
def ev(path):
    out = ps("agent-browser eval (Get-Content -Raw -Encoding UTF8 '%s')" % path)
    for line in reversed(out.splitlines()):
        line=line.strip()
        if line.startswith('"') and line.endswith('"'):
            try: return json.loads(json.loads(line))
            except Exception: continue
    return out

open('_qa/_zoom.js','w',encoding='utf-8').write(
  "(function(){var de=document.documentElement;"
  "var hidden=[].slice.call(document.querySelectorAll('h1,h2,h3,p,li,dd,button,a')).filter(function(e){"
  "  if(!e.offsetParent) return false; var s=getComputedStyle(e);"
  "  var r=e.getBoundingClientRect();"
  "  return (r.right>innerWidth+2||r.left<-2) && s.position!=='fixed';}).length;"
  "return JSON.stringify({w:innerWidth,sw:de.scrollWidth,real:de.scrollWidth>de.clientWidth+1,"
  "offscreen: hidden, rootFont:getComputedStyle(de).fontSize})})()")

# 200% 缩放：视口等效 720x450
for w,h,label in [(720,450,'200% 缩放等效视口'),(1280,720,'125% 缩放等效视口')]:
    ps('agent-browser set viewport %d %d' % (w,h))
    ps('agent-browser open "http://127.0.0.1:8791/?zoom=%d"' % w)
    ps('agent-browser wait --load networkidle')
    time.sleep(1.3)
    print(label, ev('_qa/_zoom.js'))
