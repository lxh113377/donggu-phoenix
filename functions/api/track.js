// functions/api/track.js —— 访问数据写入端点（POST /api/track）
// 设计约束：
//   1. 只收匿名统计字段，白名单 + 长度截断，未知字段一律丢弃；
//   2. 地理与 UA 取自请求头（Cloudflare 边缘注入），前端不传也不可信；
//   3. 任何异常都以 200 + ok:false 降级，绝不让访客侧看到 5xx；
//   4. 同源校验：带 Origin 且不同源的浏览器请求直接拒（挡浏览器侧跨站刷量）。
const MAX_EVENTS = 20;
var FIELDS = { event: 32, path: 128, scene: 32, vid: 40, referrer: 256, lang: 16, screen: 16 };

function clean(v, max) {
  if (typeof v !== 'string') { return null; }
  v = v.trim();
  if (!v) { return null; }
  return v.slice(0, max);
}

function json(body, status) {
  return new Response(JSON.stringify(body), {
    status: status || 200,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Cache-Control': 'no-store'
    }
  });
}

function sameOrigin(request) {
  var origin = request.headers.get('origin');
  if (!origin) { return true; }
  try {
    return new URL(origin).origin === new URL(request.url).origin;
  } catch (e) {
    return false;
  }
}

export async function onRequestPost(context) {
  var request = context.request, env = context.env;
  if (!env.DB) { return json({ ok: false, error: 'db_unavailable' }); }
  if (!sameOrigin(request)) { return json({ ok: false, error: 'cross_origin_blocked' }); }

  var payload = null;
  try { payload = await request.json(); } catch (e) { payload = null; }

  var list = [];
  if (Array.isArray(payload && payload.events)) {
    list = payload.events.slice(0, MAX_EVENTS);
  } else if (payload && typeof payload === 'object') {
    list = [payload];
  }

  var cf = request.cf || {};
  var ua = clean(request.headers.get('user-agent'), 256);
  var refHdr = clean(request.headers.get('referer'), 256);
  var geo = {
    country: clean(cf.country, 8),
    city: clean(cf.city, 64),
    tz: clean(cf.timezone, 64)
  };

  var stmts = [];
  for (var i = 0; i < list.length; i++) {
    var raw = list[i];
    if (!raw || typeof raw !== 'object') { continue; }
    var event = clean(raw.event, FIELDS.event) || 'pageview';
    stmts.push(env.DB.prepare(
      'INSERT INTO visits (event, path, scene, vid, referrer, ua, lang, screen, country, city, tz)' +
      ' VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
    ).bind(
      event,
      clean(raw.path, FIELDS.path),
      clean(raw.scene, FIELDS.scene),
      clean(raw.vid, FIELDS.vid),
      clean(raw.referrer, FIELDS.referrer) || refHdr,
      ua,
      clean(raw.lang, FIELDS.lang),
      clean(raw.screen, FIELDS.screen),
      geo.country,
      geo.city,
      geo.tz
    ));
  }

  if (!stmts.length) { return json({ ok: true, stored: 0 }); }
  try {
    await env.DB.batch(stmts);
    return json({ ok: true, stored: stmts.length });
  } catch (e) {
    return json({ ok: false, error: 'db_write_failed' });
  }
}

export async function onRequest() {
  return json({ ok: true, hint: 'POST anonymous visit events to this endpoint' });
}
