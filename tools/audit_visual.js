/* tools/audit_visual.js — 设计审计探针（浏览器侧）
 * 用法：agent-browser eval (Get-Content -Raw tools/audit_visual.js)
 * 输出 JSON：字体/字阶/对比度/层级/节奏/溢出/触控/资源/动效/导航
 */

(() => {
  const out = {};
  const css = getComputedStyle(document.documentElement);
  const rgb = (c) => {
    c = (c || '').trim();
    let m = c.match(/^#([0-9a-f]{6})$/i);
    if (m) return [parseInt(m[1].slice(0,2),16),parseInt(m[1].slice(2,4),16),parseInt(m[1].slice(4,6),16),1];
    m = c.match(/^rgba?\(([^)]+)\)/);
    if (m) { const p = m[1].split(',').map(Number); return [p[0],p[1],p[2],p.length>3?p[3]:1]; }
    return null;
  };
  const lum = (p) => { const f = v => { v/=255; return v<=0.03928? v/12.92 : Math.pow((v+0.055)/1.055,2.4); }; return 0.2126*f(p[0])+0.7152*f(p[1])+0.0722*f(p[2]); };
  const ratio = (a,b) => { const L1=lum(a), L2=lum(b), hi=Math.max(L1,L2), lo=Math.min(L1,L2); return (hi+0.05)/(lo+0.05); };
  const over = (fg, bg) => [fg[0]*fg[3]+bg[0]*(1-fg[3]), fg[1]*fg[3]+bg[1]*(1-fg[3]), fg[2]*fg[3]+bg[2]*(1-fg[3]), 1];
  const hasBgImage = (el) => { for (let e = el; e && e !== document.documentElement; e = e.parentElement) { const s = getComputedStyle(e); if (s.backgroundImage && s.backgroundImage !== 'none') return true; if (s.backgroundColor && s.backgroundColor !== 'rgba(0, 0, 0, 0)' && s.backgroundColor !== 'transparent') return false; } return false; };
  const bgOf = (el) => {
    for (let e = el; e; e = e.parentElement) {
      const s = getComputedStyle(e);
      const c = rgb(s.backgroundColor);
      if (c && c[3] > 0.5) return c;
      if (s.backgroundImage && s.backgroundImage !== 'none') return null;
    }
    return rgb(css.getPropertyValue('--bg')) || [11,9,8,1];
  };
  // 1) fonts
  const pick = (sel) => { const e = document.querySelector(sel); if (!e) return null; const s = getComputedStyle(e); return { sel, ff: s.fontFamily.split(',')[0].trim(), fs: s.fontSize, lh: s.lineHeight, ls: s.letterSpacing }; };
  out.fonts = ['h1','.hero h1 em','.sec-head h2','.sec-head h2 small','.hero-tag','body','.hero-lead','.culture-card h3','.craft-card blockquote','.merch-item h3','.nav a','.ar-copy h2','.carve-cap h3','.foot-copy .url'].map(pick).filter(Boolean);
  out.loadedFonts = [...document.fonts].map(f => f.family + ' ' + f.weight + ' ' + f.status).slice(0,20);
  // 2) type scale
  const sizes = {};
  document.querySelectorAll('body *').forEach(e => {
    if (!e.offsetParent && e.tagName !== 'BODY') return;
    const t = [...e.childNodes].filter(n => n.nodeType === 3 && n.textContent.trim()).map(n=>n.textContent.trim()).join('');
    if (!t) return;
    const s = getComputedStyle(e);
    sizes[s.fontSize] = (sizes[s.fontSize] || 0) + 1;
  });
  out.typeScale = Object.entries(sizes).map(([k,v])=>({size:parseFloat(k), count:v})).sort((a,b)=>a.size-b.size);
  // 3) contrast offenders
  const offenders = [];
  document.querySelectorAll('body *').forEach(e => {
    if (!e.offsetParent) return;
    const txt = [...e.childNodes].filter(n => n.nodeType === 3).map(n=>n.textContent.trim()).join('');
    if (!txt) return;
    const s = getComputedStyle(e);
    const fg = rgb(s.color); if (!fg) return;
    const bg = bgOf(e); if (!bg) return;
    const r = ratio(over(fg,bg), bg);
    const fs = parseFloat(s.fontSize); const bold = parseInt(s.fontWeight,10) >= 700;
    const large = fs >= 24 || (fs >= 18.66 && bold);
    const need = large ? 3.0 : 4.5;
    if (r < need) offenders.push({ t: txt.slice(0,18), sel: e.tagName.toLowerCase() + '.' + (e.className && e.className.baseVal === undefined ? String(e.className).split(' ')[0] : ''), fs, ratio: +r.toFixed(2), need });
  });
  out.contrastOffenders = offenders.slice(0, 40);
  out.contrastCount = offenders.length;
  // 4) headings hierarchy
  out.headings = [...document.querySelectorAll('h1,h2,h3,h4')].filter(e=>e.offsetParent).map(e=>({tag:e.tagName.toLowerCase(), t:e.textContent.trim().slice(0,20), fs:getComputedStyle(e).fontSize, color:getComputedStyle(e).color, ls:getComputedStyle(e).letterSpacing}));
  // 5) section rhythm
  out.sections = [...document.querySelectorAll('main > section')].filter(e=>e.offsetParent).map(e=>{ const s = getComputedStyle(e); return { id: e.id, pt: s.paddingTop, pb: s.paddingBottom, h: Math.round(e.getBoundingClientRect().height), mt: s.marginTop }; });
  // 6) overflow / undersized targets
  out.doc = { sw: document.documentElement.scrollWidth, iw: innerWidth, sh: document.body.scrollHeight, nodes: document.querySelectorAll('*').length };
  out.overflowEls = [...document.querySelectorAll('body *')].filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && (r.right > innerWidth + 1 || r.left < -1); }).slice(0,12).map(e => (e.tagName + '.' + String(e.className).split(' ')[0]).slice(0,40) + ' w=' + Math.round(e.getBoundingClientRect().width));
  out.smallTargets = [...document.querySelectorAll('button, a[href], input, [role="tab"]')].filter(e=>e.offsetParent).map(e=>{const r=e.getBoundingClientRect();return {t:(e.textContent||'').trim().slice(0,12)||e.id||String(e.className), w:Math.round(r.width), h:Math.round(r.height)}}).filter(x=>x.w<44||x.h<44);
  // 7) assets
  out.resources = performance.getEntriesByType('resource').map(r=>({n:r.name.split('/').pop(), type:r.initiatorType, kb:Math.round((r.transferSize||0)/1024), ms:Math.round(r.duration)})).filter(r=>r.kb>0).sort((a,b)=>b.kb-a.kb).slice(0,10);
  out.paint = (()=>{ const p = performance.getEntriesByType('paint'); return p.map(x=>({n:x.name, ms:Math.round(x.startTime)})); })();
  out.images = [...document.images].filter(i=>i.offsetParent).map(i=>({src:i.currentSrc.split('/').pop(), nw:i.naturalWidth, dw:Math.round(i.getBoundingClientRect().width), loading:i.loading, lazy:i.getAttribute('loading')})).slice(0,20);
  // 8) motion inventory
  const anim = { transitions: 0, animations: 0 };
  document.querySelectorAll('body *').forEach(e => { const s = getComputedStyle(e); if (s.transitionDuration !== '0s') anim.transitions++; if (s.animationName !== 'none') anim.animations++; });
  out.motion = anim;
  out.scrollCue = { hasScrollMargin: (()=>{ const e=document.querySelector('#ar-gallery'); return e? getComputedStyle(e).scrollMarginTop : 'none'; })() };
  out.nav = { visibleLinks: [...document.querySelectorAll('.nav a')].filter(a=>a.offsetParent).length, activeClass: document.querySelectorAll('.nav a.on').length, mobileBtn: !!document.querySelector('.nav-toggle, .nav-burger, [aria-label*="菜单"]') };
  return JSON.stringify(out);
})()
