// functions/api/stats.js —— 访问统计聚合端点（GET /api/stats）
// 输出：累计浏览、累计访客、今日浏览、今日访客、近 14 天序列、场景热度、热门路径。
// 只读聚合、no-store：页脚计数每次都拿新鲜值，不进任何缓存。
export async function onRequestGet(context) {
  var env = context.env;
  var headers = {
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store'
  };
  if (!env.DB) {
    return new Response(JSON.stringify({ ok: false, error: 'db_unavailable' }), { status: 200, headers: headers });
  }

  function fallback() {
    return new Response(JSON.stringify({ ok: false, error: 'db_read_failed' }), { status: 200, headers: headers });
  }

  try {
    var results = await env.DB.batch([
      env.DB.prepare(
        "SELECT COUNT(*) AS n, COUNT(DISTINCT vid) AS u FROM visits WHERE event = 'pageview'"
      ),
      env.DB.prepare(
        "SELECT COUNT(*) AS n, COUNT(DISTINCT vid) AS u FROM visits WHERE event = 'pageview' AND day = date('now')"
      ),
      env.DB.prepare(
        "SELECT day, COUNT(*) AS n, COUNT(DISTINCT vid) AS u FROM visits" +
        " WHERE event = 'pageview' AND day >= date('now', '-13 days') GROUP BY day ORDER BY day"
      ),
      env.DB.prepare(
        "SELECT scene, COUNT(*) AS n FROM visits WHERE event = 'ar_scene' AND scene IS NOT NULL" +
        " GROUP BY scene ORDER BY n DESC LIMIT 6"
      ),
      env.DB.prepare(
        "SELECT path, COUNT(*) AS n FROM visits WHERE event = 'pageview' AND path IS NOT NULL" +
        " GROUP BY path ORDER BY n DESC LIMIT 6"
      )
    ]);
  } catch (e) {
    return fallback();
  }

  var totals = results[0].results[0] || { n: 0, u: 0 };
  var todayRow = results[1].results[0] || { n: 0, u: 0 };
  var body = {
    ok: true,
    total: totals.n,
    uniques: totals.u,
    today: todayRow.n,
    todayUniques: todayRow.u,
    days: (results[2].results || []).map(function (r) { return { day: r.day, n: r.n, u: r.u }; }),
    scenes: (results[3].results || []).map(function (r) { return { scene: r.scene, n: r.n }; }),
    paths: (results[4].results || []).map(function (r) { return { path: r.path, n: r.n }; })
  };
  return new Response(JSON.stringify(body), { status: 200, headers: headers });
}
