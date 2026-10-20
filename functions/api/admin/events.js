// functions/api/admin/events.js —— 后台访问明细（GET /api/admin/events，需 X-Admin-Key）
// 参数：limit（1-200，默认 50）、offset（默认 0）、event / scene（可选过滤）。
// 返回按 id 倒序的原始事件 + 命中总数（供前端分页与导出）。
export async function onRequestGet(context) {
  var env = context.env, url = new URL(context.request.url);
  var headers = { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' };
  if (!env.DB) {
    return new Response(JSON.stringify({ ok: false, error: 'db_unavailable' }), { status: 200, headers: headers });
  }

  var limit = Math.min(Math.max(parseInt(url.searchParams.get('limit') || '50', 10) || 50, 1), 200);
  var offset = Math.max(parseInt(url.searchParams.get('offset') || '0', 10) || 0, 0);
  var event = (url.searchParams.get('event') || '').slice(0, 32);
  var scene = (url.searchParams.get('scene') || '').slice(0, 32);

  var where = [], binds = [];
  if (event) { where.push('event = ?'); binds.push(event); }
  if (scene) { where.push('scene = ?'); binds.push(scene); }
  var whereSql = where.length ? ' WHERE ' + where.join(' AND ') : '';

  var listSql = 'SELECT id, ts, day, event, path, scene, vid, referrer, ua, lang, screen, country, city, tz FROM visits' +
    whereSql + ' ORDER BY id DESC LIMIT ? OFFSET ?';

  try {
    var countStmt = env.DB.prepare('SELECT COUNT(*) AS n FROM visits' + whereSql);
    var countRow = binds.length ? await countStmt.bind(...binds).first() : await countStmt.first();
    var rows = await env.DB.prepare(listSql).bind(...binds.concat([limit, offset])).all();
  } catch (e) {
    return new Response(JSON.stringify({ ok: false, error: 'db_read_failed' }), { status: 200, headers: headers });
  }

  return new Response(JSON.stringify({
    ok: true,
    total: countRow ? countRow.n : 0,
    limit: limit,
    offset: offset,
    rows: rows.results || []
  }), { status: 200, headers: headers });
}
