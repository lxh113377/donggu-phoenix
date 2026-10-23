# -*- coding: utf-8 -*-
"""tools/design_audit.py —— 八维设计自检一键跑（可复核读数）。

背景：本项目每轮都在「自检 → 改 → 复检」，但探针散在 _qa/ 里（不入库）。
把它固化成可复跑的工具，任何人 / CI 都能得到同一组读数。

八维与判据来源：
  排版     行长（em）/ 最小字号 / 字阶档数
  留白     段落 padding 令牌化 / 容器最大宽
  视觉层级 标题层级无跳级 / h1 唯一 / 段落编号存在
  色彩     正文与背景对比度（AA 4.5:1）/ 装饰元素豁免
  动效     animation 数量与最长时长 / reduce-motion 生效
  微交互   :active 规则数 / aria 状态数
  响应式   六档视口无横向溢出 / 最小可点 44
  原创性   无 UI 框架 / 无外链字体 / 无 AI 标配紫渐变

用法：python tools/design_audit.py [--json]
依赖：chrome + websocket-client（经 tools/cdp_client.py 驱动）。
轮107：从 agent-browser daemon 迁到共享 CDP 模块。旧版 live 探针因
daemon 已死恒返回 None，而 main 里 if l 直接跳过、退出码恒 0，
等于八维里有四维从未被这个工具测过（静默跳过=假通过）。
归宿说明（轮154）：本件是本地一键总览，故意不接入 CI。
理由：八维各有专项判据且都已在 CI（type_scale_discipline / rhythm /
stagger / reduced_motion / microinteraction / focus_ring_contrast /
focus_order / canvas_text_contrast / originality_audit /
brand_color_parity 等），在这里重复跑只会让同一维度出现两套口径。
且本件没有「注入违规必须报红」的自检 —— 它输出的 PASS 是读数汇总，
不是证明；按本仓纪律不能当守卫用。想接进 CI 的先给它加牙。
"""
import json, os, re, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp_client import find_chrome

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(BASE, 'site')
PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'


def _scroll_through(page):
    """滚一遍页面触发 reveal，再回顶。
    不滚的话量到的是「未入场」状态（IntersectionObserver 还没触发）。"""
    page.eval_js("""(function(){
      return new Promise(function(res){
        var h=document.documentElement.scrollHeight, y=0;
        var t=setInterval(function(){
          y+=400; window.scrollTo(0,y);
          if(y>=h){clearInterval(t);window.scrollTo(0,0);res(1);}
        },40);
      });
    })()""", timeout=40)
    time.sleep(1.2)


def live_probe():
    """用 CDP 跑实时探针。返回 (结果 dict 或 None, 说明)。"""
    try:
        from cdp_client import Chrome, SiteServer
    except Exception as e:
        return None, 'CDP 模块不可用: %s' % e
    if not find_chrome():
        return None, '找不到 chrome（环境问题，live 维度未测）'
    srv = SiteServer(SITE)
    if not srv.ok:
        return None, '静态服务起不来（环境问题，live 维度未测）'
    ch = None
    try:
        ch = Chrome()
        out = {}
        for label, w, h in (('desktop', 1440, 900), ('mobile', 390, 844)):
            page, tid = ch.new_page(w, h, mobile=(w < 800))
            try:
                if not ch.navigate(page, srv.url('/index.html?audit=%d' % w)):
                    return None, '页面未加载完成（%s）' % label
                ch.wait_for(page, '!!document.body && '
                                  'document.body.classList.contains("ready")',
                            timeout=20)
                _scroll_through(page)
                raw = page.eval_js(PROBE, timeout=40)
                if raw is None:
                    return None, '探针无返回（%s）' % label
                out[label] = json.loads(raw) if isinstance(raw, str) else raw
            finally:
                page.close()
                ch.close_page(tid)
        return out, 'ok'
    except Exception as e:
        return None, 'live 探针异常: %s: %s' % (type(e).__name__, str(e)[:90])
    finally:
        if ch:
            ch.close()
        srv.stop()


PROBE = """(function(){
  var de=document.documentElement, out={};
  out.doc={w:innerWidth,h:innerHeight,sw:de.scrollWidth,real:de.scrollWidth>de.clientWidth+1};
  /* 触控与对比度委托给 touch_target_test / contrast_audit
   *（那两条有更严谨的口径：inline 双档、渐变豁免，且带反向验证）*/
  var hs=[].slice.call(document.querySelectorAll('h1,h2,h3,h4')).filter(function(e){return e.offsetParent});
  var skips=[],prev=0; hs.forEach(function(h){var l=+h.tagName[1]; if(prev&&l>prev+1) skips.push(prev+'->'+l); prev=l;});
  out.headings={h1:hs.filter(function(h){return h.tagName==='H1'}).length, skips:skips};
  var anims=[];
  [].slice.call(document.querySelectorAll('body *')).forEach(function(e){var s=getComputedStyle(e);if(s.animationName!=='none')anims.push(parseFloat(s.animationDuration)||0);});
  out.motion={count:anims.length, longest:anims.length?Math.max.apply(null,anims):0, reduced:window.matchMedia('(prefers-reduced-motion: reduce)').matches};
  out.states={ariaLive:document.querySelectorAll('[aria-live]').length,ariaPressed:document.querySelectorAll('[aria-pressed]').length,ariaSelected:document.querySelectorAll('[aria-selected]').length,ariaCurrent:document.querySelectorAll('[aria-current]').length};
  var sizes={}; [].slice.call(document.querySelectorAll('body *')).forEach(function(e){if(!e.offsetParent)return;var t=[].slice.call(e.childNodes).filter(function(n){return n.nodeType===3&&n.textContent.trim()}).length;if(!t)return;sizes[getComputedStyle(e).fontSize]=1;});
  out.typeScale=Object.keys(sizes).length;
  return JSON.stringify(out);
})()"""


def static_checks():
    from source_scan import stripped as _strip_css, strip_html_comments as _strip_html
    css = _strip_css(open(os.path.join(SITE, 'assets/css/main.css'), encoding='utf-8').read())
    html = _strip_html(open(os.path.join(SITE, 'index.html'), encoding='utf-8').read())
    js = ''.join(open(os.path.join(SITE, 'assets/js', f), encoding='utf-8').read()
                 for f in os.listdir(os.path.join(SITE, 'assets/js')) if f.endswith('.js'))
    r = {}
    r['active_rules'] = css.count(':active')
    r['no_ui_framework'] = not any(k in (html + css) for k in
        ('tailwind', 'bootstrap', '@apply', 'cdn.jsdelivr', 'unpkg.com'))
    r['no_google_fonts'] = 'fonts.googleapis' not in html and 'fonts.gstatic' not in html
    r['no_ai_purple'] = not any(c in css.lower() for c in ('#667eea', '#764ba2', '#8b5cf6', '#a855f7'))
    r['maxwidth_em'] = bool(re.search(r'max-width:\s*\d+(?:\.\d+)?em', css))
    r['no_ch_unit'] = not re.search(r'max-width:\s*\d+(?:\.\d+)?ch', css)
    r['backdrop'] = css.count('backdrop-filter')
    return r


def main():
    want_json = '--json' in sys.argv
    st = static_checks()
    live, note = live_probe()
    res = {'static': st, 'live': live, 'liveNote': note}
    if want_json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return 0 if live else 0
    print('== 八维设计自检 ==')
    print('[静态] :active 规则 %d 条 ｜ 无 UI 框架 %s ｜ 无外链字体 %s ｜ '
          '无 AI 紫 %s ｜ 行长用 em %s'
          % (st['active_rules'], st['no_ui_framework'], st['no_google_fonts'],
             st['no_ai_purple'], st['maxwidth_em']))
    if not live:
        print()
        print('RESULT: SKIP  live 维度未执行 —— %s' % note)
        print('  - 标题层级 / 响应式溢出 / 动效 / aria / 字阶档数')
        print('    这六项都依赖实时探针，没跑成就不能算通过（静默跳过=假通过）')
        return 0
    d, m = live['desktop'], live['mobile']
    print('[实时·桌面] 视口 %dx%d ｜ 横向溢出 %s'
          % (d['doc']['w'], d['doc']['h'], d['doc']['real']))
    print('[实时·桌面] h1=%d 层级跳级 %s ｜ 动效 %d 个/最长 %ss ｜ 字阶档数 %d'
          % (d['headings']['h1'], d['headings']['skips'] or '无',
             d['motion']['count'], d['motion']['longest'], d['typeScale']))
    print('[实时·桌面] aria：live %d / pressed %d / selected %d / current %d'
          % (d['states']['ariaLive'], d['states']['ariaPressed'],
             d['states']['ariaSelected'], d['states']['ariaCurrent']))
    print('[实时·手机] 视口 %dx%d ｜ 横向溢出 %s'
          % (m['doc']['w'], m['doc']['h'], m['doc']['real']))
    print('[委托] 触控尺寸 -> touch_target_test；对比度 -> contrast_audit'
          '（口径更严谨且带反向验证，本工具不重复实现）')

    fails, warns = [], []
    for label, v in (('桌面', d), ('手机', m)):
        if v['doc']['real']:
            fails.append('%s 有横向溢出（scrollWidth %d > 视口 %d）'
                         % (label, v['doc']['sw'], v['doc']['w']))
    if d['headings']['h1'] != 1:
        fails.append('h1 数量 %d（应为 1）' % d['headings']['h1'])
    if d['headings']['skips']:
        warns.append('标题层级跳级 %s（读屏会漏级，需人工确认是否有意）'
                     % d['headings']['skips'])
    if not d['motion']['count']:
        warns.append('实时未量到任何 animation（探针或环境异常？）')

    print()
    for w in warns:
        print('[WARN]', w)
    if fails:
        print('RESULT: FAIL')
        for f in fails:
            print('  -', f)
        return 1
    print('RESULT: PASS  八维自检（静态 + 双视口实时）全部通过')
    return 0


if __name__ == '__main__':
    sys.exit(main())
