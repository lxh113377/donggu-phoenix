/* sw.js — 轻量化离线兜底（零依赖手写，不引入 workbox 等构建期工具）
 *
 * 为什么需要它：站点此前只靠响应头 cache-control: max-age=600 兜底，
 * 断网超过 10 分钟再进就白屏 —— 而「现场网络不可控」是本项目的核心前提。
 *
 * 缓存策略（分层，避免首访就强拉整站）：
 *   0) 文创 12 张实物图属重资产（合计约 450KB），一律走「访问后缓存」，
 *      绝不进 PRECACHE —— 现场首访的瓶颈是 4G，不是第二次访问；
 *   1) 关键路径（HTML/CSS/JS/图腾 SVG/manifest）安装期预缓存，约 265KB；
 *   2) 照片与文创图等重资产走「访问后缓存」，看过才存，第二次进入即全离线；
 *   3) 导航请求 network-first、失败回落缓存的 index.html（现场断网仍可开）；
 *   4) 其余静态资源 cache-first，命中即返回，未命中回源并写入缓存。
 *
 * 子路径安全：本站部署在 https://<host>/donggu-phoenix/ 这类子路径下，
 * 因此所有清单路径都相对 sw.js 自身位置解析，不写死绝对路径。
 */
'use strict';

/* 版本由 PRECACHE 内容参与计算：改清单即换缓存名，避免旧缓存赖着不走。
 * 手工 bump 也允许（改文案不动文件清单时）。 */
/* v4：新增「版本对账守卫」—— index.html 内联脚本会把 CSS 的 --build 与自身 BUILD 常量对账，
 * 不等则清 SW 与 caches 后重载一次，解决「新 HTML + 旧缓存 CSS」渲染成无样式文本的问题。
 * 本次 index.html / main.css 都变了，缓存名随之换。
 * 注意：SW 的 VERSION 只管缓存名；跨版本对账的唯一锚点是 CSS --build ⇄ HTML BUILD。 */
/* v6：「一木成像」成品改为像素级复刻位图（assets/img/statue-cut.webp +
 * assets/data/statue-profile.js 入 PRECACHE），画布高度上限提升。清单与内容都变了。 */
var VERSION = 'v6';

/* 关键路径：离线也必须能完整渲染首屏与三段 AR */
var PRECACHE = [
  'index.html',
  'manifest.webmanifest',
  'assets/css/main.css',
  'assets/fonts/zcool-display.woff2',
  'assets/fonts/cinzel.woff2',
  'assets/data/culture.js',
  'assets/data/ar-data.js',
  'assets/data/statue-profile.js',
  'assets/img/statue-cut.webp',
  'assets/js/phoenix.js',
  'assets/js/wood-to-statue.js',
  'assets/js/ar-scenes.js',
  'assets/js/ar.js',
  'assets/js/wood-demo.js',
  'assets/js/main.js',
  'assets/img/phoenix-totem.svg',
  'assets/img/phoenix-mark.svg',
  'assets/img/phoenix-particle.svg',
  'assets/img/qr.png'
];

/* 重资产：不预拉，首次访问后留存（文创 12 张实物图靠这里的 cacheThenStore 兜） */
var LAZY_CACHE = 'assets';

var BASE = new URL(self.scopeURL || './', self.location.href);

function urlOf(p) { return new URL(p, BASE).href; }

function cacheName(kind) { return 'donggu-' + kind + '-' + VERSION; }

self.addEventListener('install', function (event) {
  event.waitUntil(
    caches.open(cacheName('core'))
      .then(function (cache) {
        // 逐项 add 而非一次性 addAll：单个文件 404 不应让整次安装失败
        return Promise.all(PRECACHE.map(function (p) {
          return cache.add(urlOf(p)).catch(function (e) {
            console.warn('[sw] precache 失败:', p, e && e.name);
            return null;
          });
        }));
      })
      .then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener('activate', function (event) {
  event.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.filter(function (k) {
        return k.indexOf('donggu-') === 0 && k.indexOf(VERSION) < 0;
      }).map(function (k) { return caches.delete(k); }));
    }).then(function () { return self.clients.claim(); })
  );
});

self.addEventListener('fetch', function (event) {
  var req = event.request;
  if (req.method !== 'GET') { return; }

  var u;
  try { u = new URL(req.url); } catch (e) { return; }
  // 只接管同源请求：本站零外部请求，跨源一律放行不缓存
  if (u.origin !== BASE.origin) { return; }
  // 绝不缓存 sw.js 自身，否则新版本永远拉不下来
  if (u.pathname === new URL('sw.js', BASE).pathname) { return; }

  var mode = req.mode;
  var dest = req.destination;

  if (mode === 'navigate' || dest === 'document') {
    event.respondWith(networkFirst(req));
    return;
  }
  if (dest === 'image' || dest === 'font' || /\.(webp|jpe?g|png|ico)$/i.test(u.pathname)) {
    event.respondWith(cacheThenStore(req));
    return;
  }
  event.respondWith(cacheFirst(req));
});

function networkFirst(req) {
  return fetch(req).then(function (res) {
    var copy = res.clone();
    caches.open(cacheName('core')).then(function (c) { c.put(req, copy); }).catch(function () {});
    return res;
  }).catch(function () {
    return caches.match(req).then(function (hit) {
      return hit || caches.match(urlOf('index.html')).then(function (idx) {
        return idx || new Response('离线且无缓存', { status: 503, headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
      });
    });
  });
}

function cacheFirst(req) {
  return caches.match(req).then(function (hit) {
    return hit || fetch(req).then(function (res) {
      var copy = res.clone();
      caches.open(cacheName('core')).then(function (c) { c.put(req, copy); }).catch(function () {});
      return res;
    });
  });
}

function cacheThenStore(req) {
  return caches.match(req).then(function (hit) {
    if (hit) { return hit; }
    return fetch(req).then(function (res) {
      var copy = res.clone();
      caches.open(cacheName(LAZY_CACHE)).then(function (c) { c.put(req, copy); }).catch(function () {});
      return res;
    });
  });
}