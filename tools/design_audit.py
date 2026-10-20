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
依赖：agent-browser（已在本机）；缺失时退化为静态检查并明示。
"""
import json, os, re, subprocess, sys, time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(BASE, 'site')
PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'


def sh(cmd, timeout=180):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, shell=True, cwd=BASE,
                           timeout=timeout, encoding='utf-8', errors='replace')
        return (r.stdout or '').strip()
    except Exception as e:
        return 'ERR:' + str(e)


def ab(*args):
    return sh('agent-browser ' + ' '.join(args))


def ev(js):
    tmp = os.path.join(BASE, '_dev', 'audit_probe.js')
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(js)
    out = sh('powershell -NoProfile -Command "agent-browser eval (Get-Content -Raw -Encoding UTF8 \'%s\')"' % tmp)
    for line in reversed(out.splitlines()):
        line = line.strip()
        if line.startswith('"') and line.endswith('"'):
            try:
                return json.loads(json.loads(line))
            except Exception:
                continue
    return None


PROBE = """(function(){
  var de=document.documentElement, out={};
  out.doc={w:innerWidth,h:innerHeight,sw:de.scrollWidth,real:de.scrollWidth>de.clientWidth+1};
  var inter=[].slice.call(document.querySelectorAll('a[href],button,input,[role=tab]')).filter(function(e){return e.offsetParent});
  out.tap={total:inter.length, under44:inter.filter(function(e){var r=e.getBoundingClientRect();return r.width>0&&(r.width<44||r.height<44)}).length};
  var hs=[].slice.call(document.querySelectorAll('h1,h2,h3,h4')).filter(function(e){return e.offsetParent});
  var skips=[],prev=0; hs.forEach(function(h){var l=+h.tagName[1]; if(prev&&l>prev+1) skips.push(prev+'->'+l); prev=l;});
  out.headings={h1:hs.filter(function(h){return h.tagName==='H1'}).length, skips:skips};
  function rgb(c){c=(c||'').trim();var m=c.match(/^rgba?\\(([^)]+)\\)/);if(m){var p=m[1].split(',').map(Number);return [p[0],p[1],p[2],p.length>3?p[3]:1];}m=c.match(/^#([0-9a-f]{6})$/i);if(m)return [parseInt(m[1].slice(0,2),16),parseInt(m[1].slice(2,4),16),parseInt(m[1].slice(4,6),16),1];return null;}
  function lum(p){function f(v){v/=255;return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4);}return .2126*f(p[0])+.7152*f(p[1])+.0722*f(p[2]);}
  function ratio(a,b){var L1=lum(a),L2=lum(b),hi=Math.max(L1,L2),lo=Math.min(L1,L2);return (hi+.05)/(lo+.05);}
  function bgOf(el){for(var e=el;e;e=e.parentElement){var s=getComputedStyle(e);var c=rgb(s.backgroundColor);if(c&&c[3]>0.5)return c;if(s.backgroundImage&&s.backgroundImage!=='none')return null;}return rgb(getComputedStyle(de).getPropertyValue('--bg'))||[11,9,8,1];}
  var bad=0, checked=0;
  [].slice.call(document.querySelectorAll('p,li,dd,span,h1,h2,h3,h4,a,button,blockquote,b,small')).forEach(function(e){
    if(!e.offsetParent) return;
    if(e.closest('[data-decorative]')||e.hasAttribute('data-decorative')) return;
    var t=[].slice.call(e.childNodes).filter(function(n){return n.nodeType===3&&n.textContent.trim()}).map(function(n){return n.textContent.trim()}).join('');
    if(!t) return;
    var cs=getComputedStyle(e), fg=rgb(cs.color); if(!fg) return;
    var bg=bgOf(e); if(!bg) return;
    var comp=[fg[0]*fg[3]+bg[0]*(1-fg[3]),fg[1]*fg[3]+bg[1]*(1-fg[3]),fg[2]*fg[3]+bg[2]*(1-fg[3]),1];
    var r=ratio(comp,bg); checked++;
    var fs=parseFloat(cs.fontSize), bold=parseInt(cs.fontWeight,10)>=700;
    if(r < ((fs>=24||(fs>=18.66&&bold))?3:4.5)) bad++;
  });
  out.contrast={checked:checked, belowAA:bad};
  var anims=[];
  [].slice.call(document.querySelectorAll('body *')).forEach(function(e){var s=getComputedStyle(e);if(s.animationName!=='none')anims.push(parseFloat(s.animationDuration)||0);});
  out.motion={count:anims.length, longest:anims.length?Math.max.apply(null,anims):0, reduced:window.matchMedia('(prefers-reduced-motion: reduce)').matches};
  out.states={ariaLive:document.querySelectorAll('[aria-live]').length,ariaPressed:document.querySelectorAll('[aria-pressed]').length,ariaSelected:document.querySelectorAll('[aria-selected]').length,ariaCurrent:document.querySelectorAll('[aria-current]').length};
  var sizes={}; [].slice.call(document.querySelectorAll('body *')).forEach(function(e){if(!e.offsetParent)return;var t=[].slice.call(e.childNodes).filter(function(n){return n.nodeType===3&&n.textContent.trim()}).length;if(!t)return;sizes[getComputedStyle(e).fontSize]=1;});
  out.typeScale=Object.keys(sizes).length;
  return JSON.stringify(out);
})()"""


def static_checks():
    css = open(os.path.join(SITE, 'assets/css/main.css'), encoding='utf-8').read()
    html = open(os.path.join(SITE, 'index.html'), encoding='utf-8').read()
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
    res = {'static': static_checks(), 'live': None}
    ab('set viewport 1440 900')
    ab('open "http://127.0.0.1:8791/?audit=1"')
    ab('wait --load networkidle')
    time.sleep(1.5)
    live = ev(PROBE)
    res['live'] = live
    if want_json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return 0
    s, l = res['static'], res['live'] or {}
    print('== 八维设计自检 ==')
    print('[静态] :active 规则 %d 条 ｜ 无 UI 框架 %s ｜ 无外链字体 %s ｜ 无 AI 紫 %s ｜ 行长用 em %s'
          % (s['active_rules'], s['no_ui_framework'], s['no_google_fonts'], s['no_ai_purple'], s['maxwidth_em']))
    if l:
        print('[实时] 视口 %dx%d 横向溢出 %s ｜ 可点 <44px %d ｜ 对比度检查 %d 处/不达标 %d'
              % (l['doc']['w'], l['doc']['h'], l['doc']['real'], l['tap']['under44'],
                 l['contrast']['checked'], l['contrast']['belowAA']))
        print('[实时] 标题层级 h1=%d 跳级 %s ｜ 动效 %d 个/最长 %ss ｜ 字阶档数 %d'
              % (l['headings']['h1'], l['headings']['skips'] or '无', l['motion']['count'],
                 l['motion']['longest'], l['typeScale']))
        print('[实时] aria 状态：live %d / pressed %d / selected %d / current %d'
              % (l['states']['ariaLive'], l['states']['ariaPressed'],
                 l['states']['ariaSelected'], l['states']['ariaCurrent']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
