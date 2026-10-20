# -*- coding: utf-8 -*-
"""检查所有 .reveal 高块在「跳转进入」场景下是否可见（回归这一 bug 的影响面）。"""
import json, subprocess, time
PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
WD = r'C:\Users\37533\Desktop\workspace\项目\新建文件夹'

def ps(cmd, timeout=180):
    r = subprocess.run([PS, '-NoProfile', '-Command', cmd], capture_output=True, text=True,
                       cwd=WD, timeout=timeout, encoding='utf-8', errors='replace')
    return (r.stdout or '').strip()

def ev(path):
    out = ps("agent-browser eval (Get-Content -Raw -Encoding UTF8 '%s')" % path)
    for line in reversed(out.splitlines()):
        line = line.strip()
        if line.startswith('"') and line.endswith('"'):
            try: return json.loads(json.loads(line))
            except Exception: continue
    return out

# 直接跳到每个段落锚点（模拟导航跳转），再看该段内 reveal 是否都 in
open('_qa/_p1.js', 'w', encoding='utf-8').write(
    "(function(){var bad=[];document.querySelectorAll('.reveal').forEach(function(e){"
    "var r=e.getBoundingClientRect();var st=getComputedStyle(e);"
    "if(r.top<innerHeight*0.95&&r.bottom>-10&&parseFloat(st.opacity)<0.9){"
    "bad.push((e.id||e.className).slice(0,30)+':'+st.opacity)}});return JSON.stringify(bad)})()")

for anchor in ['#totem', '#carve-sec', '#ar-gallery', '#culture', '#craft', '#merch', '#road', '#scan']:
    ps('agent-browser open "http://127.0.0.1:8791/?a=%s"' % anchor.replace('#', ''))
    ps('agent-browser wait --load networkidle')
    time.sleep(1.2)
    ps('agent-browser eval "location.hash=\'%s\'; 1"' % anchor)
    time.sleep(1.6)
    print(anchor, '->', ev('_qa/_p1.js'))
