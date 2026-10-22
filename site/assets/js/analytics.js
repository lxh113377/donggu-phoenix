/* analytics.js —— 匿名访问统计上报 + 页脚访问计数
 *
 * 上报侧的边界与承诺（未改动）：
 *   1. 只在具备后端的部署面上报：*.pages.dev 与本地开发域名。
 *      GitHub Pages 版没有 Functions，探测到非 pages.dev 域名时上报整段休眠，
 *      一个请求都不发 —— 两端共用同一份代码，无需分叉构建。
 *   2. 只上报匿名统计字段：事件名、路径、场景号、随机访客号、语言、屏幕档。
 *      不采集可输入内容、不做跨站跟踪；地理与 UA 由边缘按请求头另行记录。
 *   3. 上报失败（断网、后端异常、本地纯静态服务器返回 404）全部静默，
 *      统计是增益不是依赖，绝不影响页面任何功能。
 *   4. 访客号存 localStorage 的 dg-vid 键，随机生成、可随时清除、不设过期。
 *
 * 2026-10-22 改动（老大指定）：页脚计数不再读 /api/stats，改读静态演示样本
 *   assets/data/footer-stats.js。原因：演示现场一旦 D1 被清空或读不到，
 *   刷新一次页脚与后台的访问量就归零 —— 在最关键的场合把数字清零。
 *   页脚因此不再受域名闸约束：两个部署面（含 file:// 双击）都显示同一组数字，
 *   并明写「演示样本」，不冒充真实访问量。
 *   真实统计链路（POST /api/track、GET /api/stats、后台接口、D1）一行未动。 */
(function () {
  'use strict';

  var ENDPOINT = '/api/track';

  var host = location.hostname;
  var hostOk = host === 'localhost' || host === '127.0.0.1' ||
    (host.length > 10 && host.slice(-10) === '.pages.dev');
  if (!hostOk) { return; }

  /* ---------- 随机访客号 ---------- */
  var vid = '';
  try {
    vid = localStorage.getItem('dg-vid') || '';
    if (!/^[0-9a-f]{16}$/.test(vid)) {
      var bytes = new Uint8Array(8);
      (window.crypto || window.msCrypto).getRandomValues(bytes);
      vid = Array.prototype.map.call(bytes, function (b) {
        return ('0' + b.toString(16)).slice(-2);
      }).join('');
      localStorage.setItem('dg-vid', vid);
    }
  } catch (e) { vid = ''; }

  /* ---------- 上报 ---------- */
  function send(event, extra) {
    var data = {
      event: event,
      path: location.pathname,
      vid: vid,
      lang: (navigator.language || '').slice(0, 16),
      screen: ((screen && screen.width) ? (screen.width + 'x' + screen.height).slice(0, 16) : ''),
      referrer: (document.referrer || '').slice(0, 256)
    };
    if (extra) {
      for (var k in extra) {
        if (Object.prototype.hasOwnProperty.call(extra, k)) { data[k] = extra[k]; }
      }
    }
    var body = JSON.stringify(data);
    try {
      if (navigator.sendBeacon) {
        navigator.sendBeacon(ENDPOINT, new Blob([body], { type: 'application/json' }));
        return;
      }
    } catch (e) { /* 降级到 fetch */ }
    try {
      fetch(ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: body,
        keepalive: true
      }).catch(function () {});
    } catch (e) {}
  }

  /* ---------- 事件面 ----------
   * pageview：进页即报一次；
   * ar_scene：ar.js 通过 hash 开场景（#ar=craft、red、phoenix），直连码与页内入口同路；
   * summon：页首轻触图腾唤凤，是本站唯一的主动互动入口。 */
  send('pageview');

  var SCENE_RE = /^#ar=([a-z]+)$/;
  function reportScene() {
    var m = SCENE_RE.exec(location.hash || '');
    if (m) { send('ar_scene', { scene: m[1] }); }
  }
  reportScene();
  window.addEventListener('hashchange', reportScene);

  document.addEventListener('click', function (ev) {
    var t = ev.target;
    while (t && t !== document.body) {
      if (t.id === 'cta-summon' || t.id === 'totem-hit') { send('summon'); return; }
      t = t.parentNode;
    }
  }, false);
})();

/* ---------- 页脚访问计数（静态演示样本）----------
 * 必须是**独立的第二段**：上面那段在非 pages.dev 域名会 return，
 * 页脚计数若写在它后面，GitHub Pages 面（二维码指向的主入口）就永远不显示 ——
 * 而这次改动的目的恰恰是让两面都稳定显示同一组数字。
 * 数据文件没加载上（被删、路径改、忘了生成）时保持 hidden：
 * 宁可少一行字，也不显示「0 位访客」—— 那正是本次改动要消灭的形态。 */
(function () {
  'use strict';

  function renderStats() {
    var el = document.getElementById('visit-stats');
    if (!el) { return; }
    var d = (typeof DG_FOOTER_STATS !== 'undefined') ? DG_FOOTER_STATS : null;
    if (!d || !d.window || !d.pv || !d.uniques) { return; }
    var n = function (v) { return (v || 0).toLocaleString('zh-CN'); };
    el.textContent = '演示样本 · 统计至 ' + d.window.end + ' 共 ' +
      n(d.uniques) + ' 位访客 · ' + n(d.pv) + ' 次浏览';
    el.hidden = false;
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', renderStats);
  } else {
    renderStats();
  }
})();
