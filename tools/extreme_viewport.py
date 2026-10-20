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
        line = line.strip()
        if line.startswith('"') and line.endswith('"'):
            try: return json.loads(json.loads(line))
            except Exception: continue
    return out

open('_qa/_ext.js','w',encoding='utf-8').write(
  "(function(){var de=document.documentElement;"
  "var inter=[].slice.call(document.querySelectorAll('a[href],button,input,[role=tab]')).filter(function(e){return e.offsetParent});"
  "var small=inter.filter(function(e){var r=e.getBoundingClientRect();return r.width>0&&(r.width<44||r.height<44)}).length;"
  "var clipped=[].slice.call(document.querySelectorAll('h1,h2,h3,p,li,span,dd')).filter(function(e){"
  "  var r=e.getBoundingClientRect(); if(r.width<=0) return false;"
  "  return e.scrollWidth>e.clientWidth+2 && getComputedStyle(e).overflow!=='visible';}).length;"
  "return JSON.stringify({w:innerWidth,h:innerHeight,sw:de.scrollWidth,cw:de.clientWidth,"
  "real:de.scrollWidth>de.clientWidth+1,minTapUnder44:small,clippedText:clipped,fontH1:getComputedStyle(document.querySelector('h1')).fontSize})})()")

for w,h,label in [(320,568,'320x568'),(430,932,'430x932'),(768,1024,'768x1024'),(1440,900,'1440x900'),(844,390,'844x390 横屏')]:
    ps('agent-browser set viewport %d %d' % (w,h))
    ps('agent-browser open "http://127.0.0.1:8791/?ext=%d"' % w)
    ps('agent-browser wait --load networkidle')
    time.sleep(1.3)
    d = ev('_qa/_ext.js')
    print('%-14s real=%s sw=%s iw=%s under44=%s clipped=%s h1=%s' % (
        label, d.get('real'), d.get('sw'), d.get('w'), d.get('minTapUnder44'), d.get('clippedText'), d.get('fontH1')))
