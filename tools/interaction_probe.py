# -*- coding: utf-8 -*-
"""交互实测（agent-browser eval 直接用 PowerShell 传文件内容，不再套一层 powershell -Command）"""
import json, subprocess, time
WD = r'C:\Users\37533\Desktop\workspace\项目\新建文件夹'
PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'

def ps(cmd, timeout=180):
    r = subprocess.run([PS, '-NoProfile', '-Command', cmd], capture_output=True, text=True,
                       cwd=WD, timeout=timeout, encoding='utf-8', errors='replace')
    return (r.stdout or '').strip()

def ev(name):
    out = ps("agent-browser eval (Get-Content -Raw -Encoding UTF8 '%s')" % name)
    for line in reversed(out.splitlines()):
        line = line.strip()
        if line.startswith('"') and line.endswith('"'):
            try: return json.loads(json.loads(line))
            except Exception: continue
    return out or None

def write(name, code):
    open('_qa/' + name, 'w', encoding='utf-8').write(code)

ps('agent-browser set viewport 1440 900')
ps('agent-browser open "http://127.0.0.1:8791/?it=%d"' % int(time.time()))
ps('agent-browser wait --load networkidle')
time.sleep(1.6)

write('i2.js', """(function(){
  var s = document.getElementById('carve-slider');
  s.value = '600'; s.dispatchEvent(new Event('input', {bubbles:true}));
  return JSON.stringify({value: s.value, pct: document.getElementById('carve-pct').textContent,
    cap: document.getElementById('carve-cap-title').textContent,
    stats: window.__carve && window.__carve.stats ? window.__carve.stats() : null});
})()""")
print('carve =>', ev('i2.js'))

write('i3.js', """(function(){
  var btns=[].slice.call(document.querySelectorAll('#merch-tabs button'));
  var target=btns.filter(function(b){return b.textContent.indexOf('高客单')>=0})[0];
  target.click();
  return JSON.stringify({tab: target.textContent, count: document.querySelectorAll('.merch-item').length,
    feature: document.querySelectorAll('.merch-item.is-feature').length,
    selected: target.getAttribute('aria-selected')});
})()""")
print('merchFilter =>', ev('i3.js'))

write('i4.js', """(function(){
  document.querySelectorAll('#merch-tabs button')[0].click();
  var a=document.querySelector('.road-item a[data-ar]');
  if (a) a.click();
  return JSON.stringify({hasLink: !!a, arOpen: document.getElementById('ar').classList.contains('on')});
})()""")
print('roadClick =>', ev('i4.js'))
time.sleep(1.0)
write('i5.js', "(function(){return JSON.stringify({arOpen: document.getElementById('ar').classList.contains('on'), badge: document.getElementById('ar-badge').textContent, title: document.getElementById('ar-title').textContent, scene: window.__ar && window.__ar.state ? window.__ar.state() : null})})()")
print('arState =>', ev('i5.js'))
ps('agent-browser screenshot --screenshot-dir ./_qa/interact/ar')
write('i6.js', "(function(){document.getElementById('ar-close').click(); return JSON.stringify({open: document.getElementById('ar').classList.contains('on')})})()")
print('arClose =>', ev('i6.js'))

write('i7.js', """(function(){
  var f=[].slice.call(document.querySelectorAll('a[href],button,input,[tabindex]:not([tabindex="-1"])')).filter(function(e){return e.offsetParent});
  var noName=f.filter(function(e){return !(e.textContent||'').trim() && !e.getAttribute('aria-label') && !e.getAttribute('title')});
  var small=f.filter(function(e){var r=e.getBoundingClientRect(); return Math.min(r.width,r.height)<24 && r.width>0;});
  return JSON.stringify({focusables:f.length, unnamed:noName.length, small:small.map(function(e){return (e.textContent||e.id||'').trim().slice(0,12)})});
})()""")
print('a11y =>', ev('i7.js'))

write('i8.js', "(function(){return JSON.stringify({errs: window.__errs || null, phoenix: window.__phoenix && window.__phoenix.state, fps: window.__phoenix && window.__phoenix.fps})})()")
print('state =>', ev('i8.js'))
