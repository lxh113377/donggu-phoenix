# -*- coding: utf-8 -*-
import json, subprocess, time
WD = r'C:\Users\37533\Desktop\workspace\项目\新建文件夹'

def sh(cmd, timeout=180):
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=WD, shell=True, timeout=timeout,
                       encoding='utf-8', errors='replace')
    return (r.stdout or '').strip()

def last_json(out):
    for line in reversed(out.splitlines()):
        line = line.strip()
        if line.startswith('"') and line.endswith('"'):
            try: return json.loads(json.loads(line))
            except Exception: continue
    return None

CLEAR = "(async()=>{const rs=await navigator.serviceWorker.getRegistrations();for(const r of rs){await r.unregister()}const ks=await caches.keys();for(const k of ks){await caches.delete(k)}return 1})()"
CLEAR_PS = 'powershell -NoProfile -Command "agent-browser eval \"' + CLEAR.replace('"','\\"') + '\""'

stamp = int(time.time())
for w, h in [(360,780),(390,844),(768,1024),(1024,768),(1440,900),(1920,1080)]:
    sh('agent-browser set viewport %d %d' % (w, h))
    sh('agent-browser open http://127.0.0.1:8791/?vp=%d' % w)
    sh('agent-browser wait --load networkidle')
    out = sh('powershell -NoProfile -Command "agent-browser eval (Get-Content -Raw -Encoding UTF8 \'_qa/clear_sw.js\')"')
    sh('agent-browser open "http://127.0.0.1:8791/?vp=%d&t=%d"' % (w, stamp))
    sh('agent-browser wait --load networkidle')
    time.sleep(1.5)
    out = sh('powershell -NoProfile -Command "agent-browser eval (Get-Content -Raw -Encoding UTF8 \'_qa/probe_viewport.js\')"')
    d = last_json(out)
    if not d:
        print(w, h, 'FAIL', out[-160:]); continue
    print("%dx%d: iw=%s sw=%s docH=%s toggle=%s minTap=%s overflow=%s h1=%s" % (
        w, h, d['w'], d['sw'], d['docH'], d['toggle'], d['minTap'],
        'OK' if not d['overflow'] else d['overflow'], d['h1']))
