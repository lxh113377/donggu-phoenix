# -*- coding: utf-8 -*-
"""轮6 收尾回归：门禁 / 六档视口 / 全锚点 reveal / 文创交互。"""
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

# 0) 门禁
r = subprocess.run([PS, '-NoProfile', '-Command', 'python tools/verify_site.py'],
                   capture_output=True, text=True, cwd=WD, encoding='utf-8', errors='replace')
lines = r.stdout.splitlines()
print('[门禁] rc=%d PASS=%d FAIL=%d | %s' % (r.returncode,
      sum(1 for l in lines if l.startswith('[PASS]')),
      sum(1 for l in lines if l.startswith('[FAIL]')),
      [l for l in lines if 'RESULT' in l or '首屏' in l or '部署体积' in l]))

# 1) 六档视口
open('_qa/_vp.js', 'w', encoding='utf-8').write(
    "(function(){var de=document.documentElement;"
    "var els=[].slice.call(document.querySelectorAll('button,a[href],input')).filter(function(e){return e.offsetParent});"
    "var worst=null;els.forEach(function(e){var r=e.getBoundingClientRect();if(r.width<8||r.height<8)return;"
    "var m=Math.min(r.width,r.height);if(!worst||m<worst.m)worst={m:Math.round(m),t:(e.textContent||e.id||'').trim().slice(0,10)}});"
    "return JSON.stringify({w:innerWidth,sw:de.scrollWidth,real:de.scrollWidth>de.clientWidth+1,minTap:worst,"
    "build:getComputedStyle(de).getPropertyValue('--build').trim()})})()")

for w, h in [(360,780),(390,844),(768,1024),(1024,768),(1440,900),(1920,1080)]:
    ps('agent-browser set viewport %d %d' % (w, h))
    ps('agent-browser open "http://127.0.0.1:8791/?rv=%d"' % w)
    ps('agent-browser wait --load networkidle')
    time.sleep(1.3)
    d = ev('_qa/_vp.js')
    print('  %dx%d: real=%s minTap=%s build=%s' % (w, h, d.get('real'), (d.get('minTap') or {}).get('m'), d.get('build')))

# 2) 交互：文创筛选 + 加载
ps('agent-browser set viewport 1440 900')
ps('agent-browser open "http://127.0.0.1:8791/?ri=1"')
ps('agent-browser wait --load networkidle')
time.sleep(1.4)
open('_qa/_it.js', 'w', encoding='utf-8').write("""(async function(){
  function sleep(ms){return new Promise(function(r){setTimeout(r,ms)})}
  var out={};
  document.getElementById('merch-grid').scrollIntoView({block:'start'});
  await sleep(1800);
  out.all={n:document.querySelectorAll('.merch-item').length,
           loaded:[].slice.call(document.querySelectorAll('.merch-shot img')).filter(function(i){return i.complete&&i.naturalWidth>0}).length,
           ph:document.querySelectorAll('.merch-shot.placeholder').length};
  var btns=[].slice.call(document.querySelectorAll('#merch-tabs button'));
  for (var i=1;i<btns.length;i++){
    btns[i].click(); await sleep(700);
    out[btns[i].textContent]={n:document.querySelectorAll('.merch-item').length,
      loaded:[].slice.call(document.querySelectorAll('.merch-shot img')).filter(function(i){return i.complete&&i.naturalWidth>0}).length};
  }
  btns[0].click(); await sleep(600);
  out.back={n:document.querySelectorAll('.merch-item').length};
  out.errors=window.__errs||null;
  return JSON.stringify(out);
})()""")
print('[交互]', json.dumps(ev('_qa/_it.js'), ensure_ascii=False))
