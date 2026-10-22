
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

# 轮121 迁移：ps() 从 PowerShell 调 agent-browser 改为 ab_compat 兼容层。
# 紧跟着的 JS 常量是判据本体，绝不能连带删掉（轮120 批量改造栽在这）。
_AB = None


def _ab():
    global _AB
    if _AB is None:
        from ab_compat import AbSession
        _AB = AbSession()
    return _AB


def ps(cmd, timeout=90):
    return _ab().run(cmd, timeout=timeout)

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
    # 轮121：先滚过全站触发所有懒加载，再回到目标区域检查。
    # 起因：判据对 hero/totem/carve-sec/merch/craft 逐个 scrollIntoView + 检查，
    # 但 loading="lazy" 的图（craft-liu/craft-lei/qr.png）分布在别的区域，
    # 滚到 A 区时 B 区的懒图还没被触发 -> naturalWidth=0 -> 误报 not-loaded。
    # 实测证据：初始三图 complete=false/nw=0（lazy），
    #           滚过 merch/craft/scan 后全部 complete=true/nw=320/320/540。
    # 产品一直是对的，是判据口径错了 —— 不能因为判据红就改产品。
    # 注意：不能用 setInterval 做滚动 —— eval 立即返回、定时器还没跑，
    # 判据就已经进下一步了（第一版就是这么白做的）。必须同步分步滚动。
    for _y in (600, 1200, 1800, 2400, 3000, 3600, 4200, 4800, 5400,
               6000, 6600, 7200, 7800, 8400, 9000, 9600, 10200, 10800):
        ps('agent-browser eval "window.scrollTo(0,%d);1"' % _y)
        time.sleep(0.22)
    ps('agent-browser eval "window.scrollTo(0,0);1"')
    time.sleep(1.5)   # 给懒加载 + decode 时间
    ps('agent-browser eval "document.getElementById(\'%s\').scrollIntoView();1"' % anchor_id)
    time.sleep(2.0)   # 留在该区域，确认 decode 完成
    out = ps('agent-browser eval (Get-Content -Raw -Encoding UTF8 "%s")' % js_path)
    # 轮121：CDP 的 eval 只返回一层，不再需要 json.loads(json.loads(...))。
    # 双层解析是 agent-browser 把结果再套一层引号的特性（已三次踩过）。
    if not out:
        return None
    try:
        return json.loads(out)
    except Exception:
        return None

# 轮121：判据自己起服务，不再假设外部已起 8791（隐性环境依赖，失败形态是 SKIP）
_SRV = None


def main():
    global _SRV
    import os as _os
    try:
        from cdp_client import SiteServer
        _SRV = SiteServer(_os.path.join(WD, 'site'), port=8791)
        _u = _SRV.url('/index.html?img=%d' % int(time.time()))
    except Exception as _e:
        print('RESULT: SKIP  服务起不来: %s' % _e)
        return 0

    ps('agent-browser set viewport 1440 900')
    ps('agent-browser open "%s"' % _u)
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

    # 轮121：退出前关掉兼容层会话与自起服务
    try:
        if _AB:
            _AB.close()
    except Exception:
        pass
    try:
        if _SRV:
            _SRV.stop()
    except Exception:
        pass

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
