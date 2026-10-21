// tools/preflight_device.mjs —— 真机前哨：用 CDP 在「模拟移动端」下实测首屏/旁白/AR 三场景。
//
// 为什么需要它（U-01）
//   真机（iPhone Safari / 微信内置）本机不可得：无数据线连接设备、无 adb、Windows 无 iOS 自动化通道。
//   于是把「能自动化的部分」全部自动化，把不可自动化的部分压到「一次点击」：
//     · UA 覆盖 -> 微信 iOS / 微信 Android / iPhone Safari 三种真实 UA
//     · 视口覆盖 -> 390x844 / 360x800（device metrics override，真 CSS 视口，非 --window-size 伪影）
//     · 网络覆盖 -> CDP 4G 限速（170ms RTT / 4Mbps 下行）
//     · CPU 覆盖 -> 4x 降频（对标中端机）
//     · 运行时 -> FCP/LCP/CLS/LongTask、console/JS 错误、横向溢出、AR 三场景推进、旁白可用性、摄像头降级
//
// 诚实边界：这是「模拟」，不是真机。模拟能证伪（模拟下都不达标，真机必然不达标），不能证实。
//   真实 iOS Safari 的 WebKit 内核、微信 XWEB 内核差异仍需真机一次点击自证（见 site/_device_probe.html）。
//
// 用法: node tools/preflight_device.mjs '<configJson>'
//   configJson = { port, url, ua, platform, width, height, dpr, throttle:{latency,down,up}, cpu, heavy, settleMs }
// 输出: 以 __PF_JSON__ 开头的一行 JSON
const cfg = JSON.parse(process.argv[2] || '{}');
const base = 'http://127.0.0.1:' + cfg.port;

function fail(msg) {
  console.log('__PF_JSON__' + JSON.stringify({ ok: false, error: String(msg) }));
  process.exit(0);
}

const ver = await (await fetch(base + '/json/version')).json().catch(e => fail('CDP /json/version 不可达: ' + e));
const ws = new WebSocket(ver.webSocketDebuggerUrl);
let id = 0;
const pending = new Map();
const listeners = new Map();
ws.addEventListener('message', ev => {
  const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) {
    const p = pending.get(m.id); pending.delete(m.id);
    m.error ? p.rej(new Error(JSON.stringify(m.error))) : p.res(m.result);
    return;
  }
  if (m.method && listeners.has(m.method)) listeners.get(m.method).forEach(f => f(m.params, m.sessionId));
});
await new Promise(r => ws.addEventListener('open', r, { once: true }));
function send(method, params, sessionId) {
  return new Promise((res, rej) => {
    const mid = ++id; pending.set(mid, { res, rej });
    ws.send(JSON.stringify(sessionId ? { id: mid, method, params, sessionId } : { id: mid, method, params }));
  });
}
function on(method, fn) {
  if (!listeners.has(method)) listeners.set(method, []);
  listeners.get(method).push(fn);
}
function waitEvent(method, ms) {
  return new Promise(res => {
    let done = false;
    const h = (p) => { if (!done) { done = true; res(p); } };
    on(method, h);
    setTimeout(() => { if (!done) { done = true; res(null); } }, ms);
  });
}

// 预注入：LCP/CLS/LongTask 观测 + 错误钩子（必须在导航前装，否则漏掉早期错误）
const PRELUDE = [
  '(function(){',
  '  window.__pf = { lcp: 0, lcpEl: "", cls: 0, longtasks: 0, errors: [] };',
  '  try { new PerformanceObserver(function(l){ var e=l.getEntries(), last=e[e.length-1];',
  '    if(last){ window.__pf.lcp=Math.round(last.startTime);',
  '      window.__pf.lcpEl = last.element ? (last.element.tagName||"") : (last.url ? ("img:"+String(last.url).slice(-24)) : ""); }',
  '  }).observe({type:"largest-contentful-paint", buffered:true}); } catch(e){}',
  '  try { new PerformanceObserver(function(l){ window.__pf.longtasks = l.getEntries().length; }).observe({type:"longtask", buffered:true}); } catch(e){}',
  '  try { new PerformanceObserver(function(l){ var e=l.getEntries(); for(var i=0;i<e.length;i++){ if(!e[i].hadRecentInput){ window.__pf.cls += e[i].value; } } }).observe({type:"layout-shift", buffered:true}); } catch(e){}',
  '  window.addEventListener("error", function(e){ window.__pf.errors.push(String((e&&e.message)||"error")); }, true);',
  '  window.addEventListener("unhandledrejection", function(e){ var r=e&&e.reason; window.__pf.errors.push("rejection: "+String((r&&r.message)||r)); });',
  '})();'
].join('\n');

// 站点探针：在 settle 之后执行，返回一个 JSON 字符串
const PROBE = [
  '(async function(){',
  '  var sleep = function(ms){ return new Promise(function(r){ setTimeout(r, ms); }); };',
  '  var out = { ok:true, errors:[] };',
  '  function safe(fn, tag){ try { return fn(); } catch(e){ out.errors.push(tag+": "+String(e&&e.message||e)); return null; } }',
  '  var nav = performance.getEntriesByType("navigation")[0] || {};',
  '  var paints = performance.getEntriesByType("paint") || [];',
  '  function paint(n){ for(var i=0;i<paints.length;i++){ if(paints[i].name===n) return Math.round(paints[i].startTime); } return 0; }',
  '  var res = performance.getEntriesByType("resource") || [];',
  '  var transfer = Number(nav.transferSize||0); for (var i=0;i<res.length;i++){ transfer += Number(res[i].transferSize||0); }',
  '  out.env = { ua: navigator.userAgent, platform: navigator.platform, vw: innerWidth, vh: innerHeight, dpr: devicePixelRatio,',
  '              touch: ("ontouchstart" in window) || (navigator.maxTouchPoints>0), langs: (navigator.languages||[]).slice(0,3) };',
  '  var PF = window.__pf || null; out.pfInstalled = !!PF; PF = PF || { lcp: 0, lcpEl: "", cls: 0, longtasks: 0, errors: [] };',
  '  out.timing = { fp: paint("first-paint"), fcp: paint("first-contentful-paint"), lcp: PF.lcp, lcpEl: PF.lcpEl,',
  '                 dcl: Math.round(Number(nav.domContentLoadedEventEnd||0)), load: Math.round(Number(nav.loadEventEnd||0)),',
  '                 transferKB: Math.round(transfer/1024), reqs: res.length + 1, longtasks: PF.longtasks, cls: Number((PF.cls||0).toFixed(4)) };',
  // 静态面（GitHub Pages，扫码落地面）不该出现任何 /api 请求：analytics.js 有域名白名单，',
  // 白名单一旦失效，静态访问者就会看到 404 —— 这正是验收判据 1「无控制台报错」的红线。',
  '  out.api = { reqs: 0 }; for (var ai=0; ai<res.length; ai++){ if (String(res[ai].name).indexOf("/api/") >= 0) out.api.reqs++; }',
  '  out.overflow = { scrollW: document.documentElement.scrollWidth, innerW: innerWidth,',
  '                   delta: document.documentElement.scrollWidth - innerWidth };',
  '  out.counts = { culture: document.querySelectorAll(".culture-card").length, craft: document.querySelectorAll(".craft-card").length,',
  '                 merch: document.querySelectorAll(".merch-item").length, arCards: document.querySelectorAll(".ar-card").length,',
  '                 sections: document.querySelectorAll("main section, body > section").length };',
  '  out.phoenix = safe(function(){ return { state: window.__site && __site.state(), fps: window.__site && __site.fps(), count: window.__site && __site.count(), ready: !!(window.__site && window.__site.ready) }; }, "phoenix");',
  '  out.hero = safe(function(){ var c=document.querySelector(".hero-cta.ai-call")||document.querySelector(".hero-cta");',
  '                    if(!c) return null; var r=c.getBoundingClientRect(); return { text:(c.textContent||"").trim().slice(0,24),',
  '                    visible: r.top < innerHeight && r.bottom > 0, top: Math.round(r.top) }; }, "hero");',
  '  out.narr = safe(function(){ var btn=document.querySelector("#ar-narrate");',
  '                    return { supported: !!(window.speechSynthesis && window.SpeechSynthesisUtterance),',
  '                             btn: btn ? { disabled: !!btn.disabled, text:(btn.textContent||"").trim().slice(0,12), pressed: btn.getAttribute("aria-pressed") } : null,',
  '                             voices: (function(){ try { return (window.speechSynthesis.getVoices()||[]).map(function(v){ return v.lang+"|"+v.name; }).slice(0,4); } catch(e){ return ["VOICES_ERR"]; } })() }; }, "narr");',
  '  if (cfgHeavy) {',
  '    out.ar = { scenes: [], camera: null, narration: null, draw: null };',
  '    var scenes = safe(function(){ return (window.__ar && __ar.scenes) ? __ar.scenes.map(function(s){ return s.id; }) : []; }, "scenes") || [];',
  '    function canvasSig(){',
  '      var cv = document.querySelector("#ar-stage"); if (!cv) return null;',
  '      var ctx = cv.getContext("2d"); if (!ctx) return null;',
  // 灵敏度：第一版 12x12 网格 + Math.round(求和) —— craft 场景「画面明明在动」却被判成静止，',
  // 因为 144 个采样点的亮度和小数变化被四舍五入吃掉了。现改 20x20 网格 + 保留 3 位小数。',
  '      var w = cv.width, h = cv.height, step = Math.max(3, Math.floor(Math.min(w,h)/20));',
  '      var lum = 0, distinct = {}, n = 0;',
  '      for (var y=Math.floor(step/2); y<h; y+=step){ for (var x=Math.floor(step/2); x<w; x+=step){',
  '        var d = ctx.getImageData(x,y,1,1).data; lum += (d[0]+d[1]+d[2])/3; distinct[d[0]+","+d[1]+","+d[2]] = 1; n++; } }',
  '      return { sig: Number(lum.toFixed(3)), colors: Object.keys(distinct).length, samples: n, w: w, h: h };',
  '    }',
  '    for (var si=0; si<scenes.length; si++){',
  '      var sid = scenes[si];',
  '      safe(function(){ __ar.open(sid, { camera:false }); }, "open-"+sid);',
  '      await sleep(1000);',
  '      // fps 必须在不被探针自己干扰的窗口里读：canvasSig 每次要跑上百次 getImageData，',
  '      // 第一版把它夹在 fps 窗口中间 —— 4x 降频下读数被自己压低（尺子自己成了被测对象）。',
  '      var s1 = safe(function(){ return __ar.stats(); }, "stats1-"+sid) || {};',
  '      await sleep(1500);',
  '      var s2 = safe(function(){ return __ar.stats(); }, "stats2-"+sid) || {};',
  '      var d1 = safe(canvasSig, "sig1-"+sid);',
  '      await sleep(400);',
  '      var d2 = safe(canvasSig, "sig2-"+sid);',
  '      var ui = safe(function(){ return { title:(document.querySelector("#ar-title")||{}).textContent||"",',
  '        chapter:(document.querySelector("#ar-chapter")||{}).textContent||"",',
  '        bodyLen:((document.querySelector("#ar-body")||{}).textContent||"").length,',
  '        badge:(document.querySelector("#ar-badge")||{}).textContent||"",',
  '        time:(document.querySelector("#ar-time")||{}).textContent||"" }; }, "ui-"+sid);',
  '      out.ar.scenes.push({ id: sid, mode: s2.mode, playing: s2.playing, t1: s1.t, t2: s2.t, fps: s2.fps,',
  '                           chapterIndex: s2.chapter, draw1: d1, draw2: d2, ui: ui });',
  '      safe(function(){ __ar.close(); }, "close-"+sid);',
  '      await sleep(250);',
  '    }',
  '    // 摄像头路径：不传 camera:false -> headless 无摄像头 -> 必须降级到展柜模式（验收判据 8）',
  '    safe(function(){ __ar.open(scenes[0] || "craft"); }, "camera-open");',
  '    await sleep(1600);',
  '    out.ar.camera = safe(function(){ var s=__ar.stats(); return { mode: s.mode, playing: s.playing, badge:(document.querySelector("#ar-badge")||{}).textContent||"", hint:(document.querySelector("#ar-hint")||{}).textContent||"" }; }, "camera-stats");',
  '    // 旁白：可切换 -> 状态自洽；不可用 -> 按钮 disabled 且文案明示（不崩）',
  '    var narrPre = safe(function(){ var b=document.querySelector("#ar-narrate"); return { disabled:!!b.disabled, text:(b.textContent||"").trim(), pressed:b.getAttribute("aria-pressed") }; }, "narr-pre");',
  '    var narrRes = null;',
  '    if (narrPre && !narrPre.disabled) {',
  '      safe(function(){ __ar.narrate(true); }, "narr-on");',
  '      await sleep(700);',
  '      narrRes = safe(function(){ var s=__ar.stats(); var b=document.querySelector("#ar-narrate");',
  '        return { stats: s.narr, pressed: b.getAttribute("aria-pressed"), on: b.classList.contains("on") }; }, "narr-on-state");',
  '      safe(function(){ __ar.narrate(false); }, "narr-off");',
  '      await sleep(250);',
  '    }',
  '    var narrPost = safe(function(){ var b=document.querySelector("#ar-narrate"); return { pressed:b.getAttribute("aria-pressed"), on:b.classList.contains("on") }; }, "narr-post");',
  '    out.ar.narration = { pre: narrPre, on: narrRes, post: narrPost };',
  '    safe(function(){ __ar.close(); }, "final-close");',
  '  }',
  '  out.inPageErrors = (PF.errors || []).slice(0, 8);',
  '  return JSON.stringify(out);',
  '})()'
].join('\n').replace('cfgHeavy', cfg.heavy ? 'true' : 'false');

const consoleErrors = [];
const logErrors = [];
on('Runtime.consoleAPICalled', p => {
  if (p.type !== 'error') return;
  const txt = (p.args || []).map(a => a.value !== undefined ? String(a.value) : (a.description || a.type)).join(' ').slice(0, 200);
  consoleErrors.push(txt);
});
on('Runtime.exceptionThrown', p => {
  const d = p.exceptionDetails || {};
  consoleErrors.push('[exception] ' + String(d.text || '') + ' ' + String((d.exception && d.exception.description) || '').slice(0, 160));
});
on('Log.entryAdded', p => {
  const e = p.entry || {};
  if (e.level !== 'error') return;
  const txt = String(e.text || '');
  const where = String(e.url || '');
  // 自检抓到的尺子缺陷（2026-10-21）：无 favicon 的页面会被浏览器自动请求 /favicon.ico 并 404，
  // 那不是页面缺陷（页面未引用它）。注意 URL 在 entry.url 而非 entry.text —— 第一版只查 text，
  // 自检第二次仍判红，才定位到这一点。不滤掉就是「尺子误报」，好夹具也会判红。
  if (/favicon\.ico/.test(txt) || /favicon\.ico/.test(where)) return;
  logErrors.push((e.source || '') + ': ' + txt.slice(0, 160) + (where ? ' [' + where.slice(-48) + ']' : ''));
});

const t = await send('Target.createTarget', { url: 'about:blank' });
const a = await send('Target.attachToTarget', { targetId: t.targetId, flatten: true });
const sid = a.sessionId;

await send('Page.enable', {}, sid);
await send('Runtime.enable', {}, sid);
await send('Log.enable', {}, sid);
await send('Network.enable', {}, sid);
const addRes = await send('Page.addScriptToEvaluateOnNewDocument', { source: PRELUDE }, sid);
await send('Emulation.setDeviceMetricsOverride', {
  width: cfg.width, height: cfg.height, deviceScaleFactor: cfg.dpr, mobile: true,
  screenOrientation: { type: 'portraitPrimary', angle: 0 }
}, sid);
await send('Emulation.setUserAgentOverride', { userAgent: cfg.ua, platform: cfg.platform, acceptLanguage: 'zh-CN,zh;q=0.9' }, sid);
await send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 }, sid);
if (cfg.cpu && cfg.cpu > 1) await send('Emulation.setCPUThrottlingRate', { rate: cfg.cpu }, sid);
if (cfg.throttle) {
  await send('Network.emulateNetworkConditions', {
    offline: false, latency: cfg.throttle.latency,
    downloadThroughput: cfg.throttle.down, uploadThroughput: cfg.throttle.up,
    connectionType: 'cellular4g'
  }, sid);
}

const loaded = waitEvent('Page.loadEventFired', 45000);
await send('Page.navigate', { url: cfg.url }, sid);
const loadEvt = await loaded;
const loadedOk = !!loadEvt;

await new Promise(r => setTimeout(r, cfg.settleMs || 2500));

const ev = await send('Runtime.evaluate', { expression: PROBE, awaitPromise: true, returnByValue: true, timeout: 120000 }, sid);
let probe = null;
if (ev && ev.result && typeof ev.result.value === 'string') {
  try { probe = JSON.parse(ev.result.value); } catch (e) { probe = { ok: false, error: 'probe JSON 解析失败: ' + e.message }; }
} else {
  probe = { ok: false, error: '探针无返回值: ' + JSON.stringify(ev && ev.exceptionDetails || ev).slice(0, 300) };
}
if (probe && probe.ok) {
  probe.loadedEvent = loadedOk;
  probe.pfScriptId = addRes && addRes.identifier;
  probe.consoleErrors = consoleErrors.slice(0, 10);
  probe.logErrors = logErrors.slice(0, 10);
}
try { await send('Target.closeTarget', { targetId: t.targetId }); } catch (e) {}
ws.close();
console.log('__PF_JSON__' + JSON.stringify(probe));
process.exit(0);
