// tools/offline_live.mjs —— 线上真实环境的「断网仍可用」验证驱动（CDP 直连）
//
// 为什么单独一个驱动（不复用 preflight_device.mjs）
//   断网验证的关键是**同一个浏览器实例、同一个 profile 走完 联网预热 -> 断网重载 -> 读数**，
//   中间不能重启 chrome：SW 的 CacheStorage 落在 user-data-dir 里，
//   而 preflight 的启动器每次调用都新建并删除 profile（防缓存污染），会把预热成果清掉。
//
// 测的是验收判据 2 的真实版本：docs/对标分析报告.md §9.3 那次离线复验是 2026-10-20 做的，
// 之后站点从 35 个文件长到 56 个、字体换成自托管 220KB、后台与自检页都新增，
// 「断网还能开」这个承诺已经很久没在**线上**复验过了。
//
// 用法: node tools/offline_live.mjs <cdpPort> <url>
// 输出: 以 __OL_JSON__ 开头的一行 JSON
const port = process.argv[2];
const url = process.argv[3];
const base = 'http://127.0.0.1:' + port;
const out = { url: url, phases: {} };

function finish(extra) {
  if (extra) Object.assign(out, extra);
  console.log('__OL_JSON__' + JSON.stringify(out));
  process.exit(0);
}

const ver = await (await fetch(base + '/json/version')).json().catch(e => finish({ ok: false, error: 'CDP 不可达: ' + e }));
const ws = new WebSocket(ver.webSocketDebuggerUrl);
let id = 0; const pending = new Map();
ws.addEventListener('message', ev => {
  const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); m.error ? p.rej(new Error(JSON.stringify(m.error))) : p.res(m.result); }
});
await new Promise(r => ws.addEventListener('open', r, { once: true }));
function send(method, params, sessionId) {
  return new Promise((res, rej) => {
    const mid = ++id; pending.set(mid, { res, rej });
    ws.send(JSON.stringify(sessionId ? { id: mid, method, params, sessionId } : { id: mid, method, params }));
  });
}
const sleep = ms => new Promise(r => setTimeout(r, ms));

const t = await send('Target.createTarget', { url: 'about:blank' });
const a = await send('Target.attachToTarget', { targetId: t.targetId, flatten: true });
const sid = a.sessionId;
await send('Page.enable', {}, sid);
await send('Runtime.enable', {}, sid);
await send('Network.enable', {}, sid);
await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 3, mobile: true }, sid);
await send('Emulation.setUserAgentOverride', {
  userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.49(0x18003137) NetType/WIFI Language/zh_CN',
  platform: 'iPhone'
}, sid);

async function evalJS(expr) {
  const ev = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true, timeout: 60000 }, sid);
  if (ev.exceptionDetails) return { __err: String((ev.exceptionDetails.exception || {}).description || ev.exceptionDetails.text).slice(0, 200) };
  return ev.result && ev.result.value;
}

// 一次完整读数（联网与断网共用同一把尺子，口径必须一致才可比）
const PROBE_LINES = [
  '(async function(){',
  '  var sleep = function(ms){ return new Promise(function(r){ setTimeout(r, ms); }); };',
  '  var o = {};',
  '  function paint(n){ var p = performance.getEntriesByType("paint") || [];',
  '    for (var i=0;i<p.length;i++){ if (p[i].name===n) return Math.round(p[i].startTime); } return null; }',
  '  o.fcp = paint("first-contentful-paint");',
  '  var nav = performance.getEntriesByType("navigation")[0] || {};',
  '  o.loadType = nav.type || null;',
  '  var x = Number(nav.transferSize||0); var rr = performance.getEntriesByType("resource") || [];',
  '  for (var q=0;q<rr.length;q++){ x += Number(rr[q].transferSize||0); }',
  '  o.transferKB = Math.round(x/1024);',
  '  o.ready = !!(window.__site && window.__site.ready);',
  '  o.state = window.__site ? __site.state() : null;',
  '  o.particles = window.__site ? __site.count() : 0;',
  '  o.fps = window.__site ? __site.fps() : 0;',
  '  o.sections = document.querySelectorAll("section").length;',
  '  o.merch = document.querySelectorAll(".merch-item").length;',
  '  o.culture = document.querySelectorAll(".culture-card").length;',
  '  o.arCards = document.querySelectorAll(".ar-card").length;',
  '  o.errors = (window.__pfErrors || []).slice(0,5);',
  '  if (window.__ar) {',
  '    try {',
  '      __ar.open("red", { camera:false }); await sleep(1500);',
  '      var s1 = __ar.stats(); var cv = document.querySelector("#ar-stage"); var sig = null;',
  '      if (cv) { var c = cv.getContext("2d"); var w = cv.width, h = cv.height;',
  '        var st = Math.max(3, Math.floor(Math.min(w,h)/16)); var sum = 0, n = 0;',
  '        for (var y=Math.floor(st/2); y<h; y+=st){ for (var xx=Math.floor(st/2); xx<w; xx+=st){',
  '          var d = c.getImageData(xx,y,1,1).data; sum += (d[0]+d[1]+d[2])/3; n++; } }',
  '        sig = Number(sum.toFixed(3)); }',
  '      await sleep(900); var s2 = __ar.stats();',
  '      o.ar = { scene:s2.scene, mode:s2.mode, playing:s2.playing, t1:s1.t, t2:s2.t,',
  '               moved:(s2.t > s1.t + 0.3), sig:sig, fps:s2.fps };',
  '      __ar.close();',
  '    } catch(e){ o.ar = { err:String(e && e.message || e) }; }',
  '  }',
  '  return JSON.stringify(o);',
  '})()'
];
const PROBE = PROBE_LINES.join('\n');
// 错误采集预注入
await send('Page.addScriptToEvaluateOnNewDocument', { source: [
  '(function(){window.__pfErrors=[];',
  'window.addEventListener("error",function(e){window.__pfErrors.push(String(e.message||"error"));},true);',
  'window.addEventListener("unhandledrejection",function(e){var r=e&&e.reason;window.__pfErrors.push("rejection: "+String((r&&r.message)||r));});',
  '})();'
].join('\n') }, sid);

// ---- 阶段 1：联网预热（让 SW 装好并填满 PRECACHE）----
await send('Page.navigate', { url: url + (url.indexOf('?') >= 0 ? '&' : '?') + 'warm=' + Date.now() }, sid);
await sleep(9000);
out.phases.warm = JSON.parse(await evalJS(PROBE) || '{}');
// SW 注册与缓存计数。用模板字符串承载（上一版把多行塞进单引号字符串，
// node 直接 SyntaxError；手数括号拼字符串也不可靠 —— 表达式先抽出来单独 node --check 过）
const SW_QUERY = `  (function(){
    return new Promise(function(res){
      if (!navigator.serviceWorker) { res({ api: false }); return; }
      navigator.serviceWorker.getRegistrations().then(function(rs){
        var r = rs && rs[0];
        if (!r) { res({ api: true, count: rs ? rs.length : 0 }); return; }
        return caches.keys().then(function(ks){
          var tot = 0;
          return Promise.all(ks.map(function(k){
            return caches.open(k).then(function(c){
              return c.keys().then(function(l){ tot += l.length; });
            });
          })).then(function(){
            res({ api: true, count: rs.length, scope: r.scope, active: !!r.active,
                  caches: ks.length, entries: tot });
          });
        });
      }).catch(function(e){ res({ api: true, err: String((e && e.message) || e) }); });
    });
  })()`;
out.sw = await evalJS(SW_QUERY);

// SW 首次接管常需再重载一次（controller 为 null 时缓存还没被真正命中）
const ctrl = await evalJS('JSON.stringify({ctrl:!!navigator.serviceWorker.controller})');
if (ctrl && !JSON.parse(ctrl).ctrl) {
  await send('Page.navigate', { url: url + (url.indexOf('?') >= 0 ? '&' : '?') + 'warm2=' + Date.now() }, sid);
  await sleep(7000);
  out.phases.warm2 = JSON.parse(await evalJS(PROBE) || '{}');
  out.swSecondLook = await evalJS('JSON.stringify({ctrl:!!navigator.serviceWorker.controller})');
}

// ---- 阶段 2：断网（CDP offline，不是拔线，但浏览器侧等价）----
await send('Network.emulateNetworkConditions', { offline: true, latency: 0, downloadThroughput: 0, uploadThroughput: 0 }, sid);
await sleep(600);
await send('Page.navigate', { url: url + (url.indexOf('?') >= 0 ? '&' : '?') + 'off=' + Date.now() }, sid);
await sleep(8000);
out.phases.offline = JSON.parse(await evalJS(PROBE) || '{}');

// ---- 阶段 3：恢复网络（确认不是单向门，回线能自愈）----
await send('Network.emulateNetworkConditions', { offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1 }, sid);
await sleep(500);
out.recovered = await evalJS('JSON.stringify({online:navigator.onLine})');

try { await send('Target.closeTarget', { targetId: t.targetId }); } catch (e) {}
ws.close();
finish({ ok: true });
