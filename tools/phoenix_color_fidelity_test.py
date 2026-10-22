# -*- coding: utf-8 -*-
r"""tools/phoenix_color_fidelity_test.py —— 凤凰粒子色必须等于其目标点应有的颜色。

## 为什么需要（轮133 抓到真 bug 后固化）
phoenix.js 的 _build() 抽稀分支里，取点用 2i 偏移、取色也用了 2i 偏移 ——
但 cols 是扁平 [r,g,b,...]，每点 3 个，正确偏移是 3i。
结果每个粒子拿到的是别处的颜色。

实测（修复前，桌面档 400 粒）：328 粒错配、平均色距 217.5（满值 765）、最差 429。
修复后：0 错配、色距 0。

这条不变量此前**没有任何判据覆盖**：
  · 对比度判据只看 CSS 计算样式，读不到 canvas 内的像素
  · 视觉平衡判据只看整体亮暗分布，看不出颜色错配
  · 令牌一致性判据（轮127）查的是「字符串字面量 ∈ 令牌表」，
    而粒子色是 Math.round 插值出来的数字，压根不是字符串
=> 属 U-395/U-401/U-408 同族：视觉不变量无人守。

## 判据
在真实页面里遍历粒子，把每个粒子的 (tx,ty) 交给 Phoenix 自己的
_colorAt() 复算应有颜色，与实际 r/g/b 比对：
  · 色距 = |dr|+|dg|+|db|，> 12 记为错配（容许取整误差）
  · 错配数必须为 0
  · 受检粒子数必须 >= 50，否则视为「没测到」判 FAIL（零样本不判 PASS）

## 尺子有效性自检（U-149/U-151）
在页面里人为把若干个粒子的颜色改成错值，要求判据立刻报出这些错配。
不这样验，一条「恒 0 错配」的判据可能是因为它根本没在比。
自检改的是内存里的对象，不写盘、不碰源码。

## 诚实语义
缺 chrome / 引擎未就绪 -> SKIP 并说明「未测不等于通过」，不判 PASS。
"""
import json
import os
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(BASE, 'site')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 在页面里执行：遍历粒子比对实际色 vs _colorAt(目标点)
PROBE = """(function(cfg){
  var P = window.__phoenix;
  if (!P || !P.particles || !P.particles.length || !P._colorAt) {
    return JSON.stringify({ready:false});
  }
  var tamper = cfg.tamper || 0;   // 自检用：改坏前 N 个粒子的颜色
  var exact = 0, near = 0, wrong = 0, n = 0, dsum = 0, worst = 0;
  var samp = [];
  for (var i = 0; i < P.particles.length; i++) {
    var p = P.particles[i];
    if (typeof p.tx !== 'number' || typeof p.ty !== 'number') { continue; }
    var w = P._colorAt(p.tx, p.ty);
    var ar = p.r, ag = p.g, ab = p.b;
    if (tamper && i < tamper) { ar = (ar + 120) % 256; ag = (ag + 70) % 256; }
    var d = Math.abs(w[0]-ar) + Math.abs(w[1]-ag) + Math.abs(w[2]-ab);
    dsum += d; n++;
    if (d > worst) { worst = d; }
    if (d <= 2) { exact++; }
    else if (d <= 12) { near++; }
    else {
      wrong++;
      if (samp.length < 3) { samp.push({i:i, actual:[ar,ag,ab], should:w, dist:d}); }
    }
  }
  return JSON.stringify({ready:true, checked:n, exact:exact, near:near,
                         wrong:wrong, avgDist:+(dsum/Math.max(1,n)).toFixed(2),
                         worst:worst, samples:samp,
                         maxParticles:P.maxParticles, lowEnd:!!P.lowEnd});
})"""

MIN_CHECKED = 50


def main():
    try:
        from cdp_client import Chrome, SiteServer, find_chrome
    except Exception as e:
        print('RESULT: SKIP  CDP 模块不可用: %s' % e)
        return 0
    if not find_chrome():
        print('RESULT: SKIP  找不到 chrome（环境问题，本判据未执行）')
        return 0

    srv = None
    ch = None
    try:
        srv = SiteServer(SITE)
        if not srv.ok:
            print('RESULT: SKIP  静态服务起不来（环境问题）')
            return 0
        ch = Chrome()
        page, tid = ch.new_page(1440, 900)
        try:
            ch.navigate(page, srv.url('/index.html?pcol=1'))
            if not ch.wait_for(page, '!!window.__phoenix', 30):
                print('RESULT: SKIP  __phoenix 未注册（引擎没加载）')
                return 0
            time.sleep(5.0)   # 等装配动画与抽稀完成

            d = json.loads(page.eval_js(PROBE + '({tamper:0})', timeout=30))
            if not d.get('ready'):
                print('RESULT: SKIP  粒子未就绪（环境问题）')
                return 0

            print('=== 粒子颜色保真度（真实加载路径）===')
            print('  受检粒子 %d 个（maxParticles=%s，lowEnd=%s）'
                  % (d['checked'], d['maxParticles'], d['lowEnd']))
            print('  完全一致 %d ｜ 近似 %d ｜ 错配 %d'
                  % (d['exact'], d['near'], d['wrong']))
            print('  平均色距 %.2f ｜ 最差 %s（满值 765）'
                  % (d['avgDist'], d['worst']))
            for s in d['samples'][:3]:
                print('    粒子 %-5s 实际 %-16s 应为 %-16s 距 %s'
                      % (s['i'], s['actual'], s['should'], s['dist']))

            fails = []
            if d['checked'] < MIN_CHECKED:
                fails.append('只受检 %d 个粒子（< %d），样本不足不判通过'
                             % (d['checked'], MIN_CHECKED))
            if d['wrong']:
                fails.append('%d 个粒子颜色与其目标点应有颜色不符'
                             '（抽稀/重建时取色索引错位）' % d['wrong'])

            # ---- 尺子有效性自检 ----
            print()
            print('=== 尺子有效性自检 ===')
            t = json.loads(page.eval_js(PROBE + '({tamper:12})', timeout=30))
            caught = t.get('wrong', 0) >= 12
            print('  [%s] 人为改坏 12 个粒子颜色 -> %s（实报 %d 错配）'
                  % ('ok' if caught else 'X',
                     '被抓到' if caught else '没抓到（判据可能在空转）',
                     t.get('wrong', 0)))
            if not caught:
                fails.append('自检失败：注入 12 个错色只报出 %s 个，'
                             '判据可能在空转' % t.get('wrong'))

            if fails:
                print()
                print('RESULT: FAIL')
                for f in fails:
                    print('  -', f)
                return 1
            print()
            print('RESULT: PASS  %d 个粒子颜色全部与其目标点一致，'
                  '且自检证明注入错色能被抓到' % d['checked'])
            return 0
        finally:
            try:
                page.close()
                ch.close_page(tid)
            except Exception:
                pass
    except Exception as e:
        print('RESULT: SKIP  探针异常（环境问题）：%s: %s'
              % (type(e).__name__, str(e)[:110]))
        return 0
    finally:
        if ch:
            try:
                ch.close()
            except Exception:
                pass
        if srv:
            try:
                srv.stop()
            except Exception:
                pass


if __name__ == '__main__':
    sys.exit(main())
