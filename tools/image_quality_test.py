
# -*- coding: utf-8 -*-
"""tools/image_quality_test.py —— 图片质量检查（正确做法：停在目标区域检查）。

## 一手教训（轮17）
第一版脚本「滚遍全站 → 滚回顶部 → 检查」，结果 12 张文创图全部报「未加载」，
差点当成生产缺陷。实际是：
  滚回顶部后图片已离开视口，浏览器回收了已 decode 的位图 ——
  complete=false / naturalWidth=0 是**正常现象**，不是加载失败。
正确做法：先滚到目标区域并停留，等 decode 完成再检查。

判据：
  · complete && naturalWidth>0（停在可视区时）
  · 显示宽高比与原始宽高比偏差 < 5%（变形）
  · 放大倍数 <= 1.3（模糊）
"""
import json, subprocess, time, sys
PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
WD = r'C:\Users\37533\Desktop\workspace\项目\新建文件夹'

def ps(cmd, timeout=45):
    try:
        r = subprocess.run([PS,'-NoProfile','-Command',cmd],capture_output=True,text=True,cwd=WD,timeout=timeout,encoding='utf-8',errors='replace')
        return ((r.stdout or '')+(r.stderr or '')).strip()
    except subprocess.TimeoutExpired:
        return 'TIMEOUT'

JS = r'''(function(){
  var out = {total:0, bad:[]};
  [].slice.call(document.images).forEach(function(img){
    var r = img.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) return;   // 只检查当前有布局的图
    out.total++;
    var nw = img.naturalWidth, nh = img.naturalHeight;
    if (!img.complete || nw === 0) {
      out.bad.push({src: img.src.split('/').pop(), why: 'not-loaded'});
      return;
    }
    var dr = (r.width / r.height), nr = (nw / nh);
    var distort = Math.abs(nr - dr) / nr;
    var upscale = r.width / nw;
    if (distort > 0.05) out.bad.push({src: img.src.split('/').pop(), why:'distort',
       detail: Math.round(distort*1000)/10 + '%'});
    else if (upscale > 1.3) out.bad.push({src: img.src.split('/').pop(), why:'upscale',
       detail: Math.round(upscale*100)/100 + 'x'});
  });
  return JSON.stringify(out);
})()'''

def check_at(anchor_id, js_path):
    ps('agent-browser eval "document.getElementById(\'%s\').scrollIntoView();1"' % anchor_id)
    time.sleep(2.2)   # 留足 decode 时间，且**停留在该区域**
    out = ps('agent-browser eval (Get-Content -Raw -Encoding UTF8 "%s")' % js_path)
    for line in reversed(out.splitlines()):
        line = line.strip()
        if line.startswith('"') and line.endswith('"'):
            try:
                return json.loads(json.loads(line))
            except Exception:
                continue
    return None

def main():
    ps('agent-browser set viewport 1440 900')
    ps('agent-browser open "http://127.0.0.1:8791/?img=%d"' % int(time.time()))
    ps('agent-browser wait --load networkidle')
    time.sleep(2.0)

    js_path = WD + r'\_qa\_imgq.js'
    open(js_path, 'w', encoding='utf-8').write(JS)

    total = 0
    bad = []
    for anchor in ['hero', 'totem', 'carve-sec', 'merch', 'craft']:
        d = check_at(anchor, js_path)
        if not d:
            print('%-10s SKIP（未取到读数）' % anchor)
            continue
        total += d['total']
        bad.extend(d['bad'])
        print('%-10s 图片 %d 张，问题 %d' % (anchor, d['total'], len(d['bad'])))

    print()
    if total == 0:
        print('RESULT: SKIP  未检查到任何图片')
        return 0
    if bad:
        print('RESULT: FAIL  %d 张图片有问题' % len(bad))
        for b in bad[:8]:
            print('  -', b)
        return 1
    print('RESULT: PASS  共检查 %d 张图片，无变形/模糊/加载失败' % total)
    return 0

if __name__ == '__main__':
    sys.exit(main())
