// functions/api/admin/overview.js —— 后台总览聚合（GET /api/admin/overview，需 X-Admin-Key）
// 比公开 /api/stats 更细：30 天序列、今日逐时、事件构成、来源、地理、语言、屏幕档。
export async function onRequestGet(context) {
  var env = context.env;
  var headers = { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' };
  if (!env.DB) {
    return new Response(JSON.stringify({ ok: false, error: 'db_unavailable' }), { status: 200, headers: headers });
  }

  try {
    var r = await env.DB.batch([
      // 累计与今日总量
      env.DB.prepare(
        "SELECT COUNT(*) AS n, COUNT(DISTINCT vid) AS u FROM visits WHERE event = 'pageview'"
      ),
      env.DB.prepare(
        "SELECT COUNT(*) AS n, COUNT(DISTINCT vid) AS u FROM visits WHERE event = 'pageview' AND day = date('now')"
      ),
      // 30 天日序列（含空日由前端补零）
      env.DB.prepare(
        "SELECT day, COUNT(*) AS n, COUNT(DISTINCT vid) AS u FROM visits" +
        " WHERE event = 'pageview' AND day >= date('now', '-29 days') GROUP BY day ORDER BY day"
      ),
      // 今日逐时（UTC 时，前端标注）
      env.DB.prepare(
        "SELECT strftime('%H', ts) AS h, COUNT(*) AS n, COUNT(DISTINCT vid) AS u FROM visits" +
        " WHERE event = 'pageview' AND day = date('now') GROUP BY h ORDER BY h"
      ),
      // 事件构成
      env.DB.prepare(
        'SELECT event, COUNT(*) AS n FROM visits GROUP BY event ORDER BY n DESC'
      ),
      // 场景热度
      env.DB.prepare(
        "SELECT scene, COUNT(*) AS n, COUNT(DISTINCT vid) AS u FROM visits WHERE event = 'ar_scene' AND scene IS NOT NULL GROUP BY scene ORDER BY n DESC"
      ),
      // 热门路径
      env.DB.prepare(
        "SELECT path, COUNT(*) AS n FROM visits WHERE event = 'pageview' AND path IS NOT NULL GROUP BY path ORDER BY n DESC LIMIT 10"
      ),
      // 来源（referrer 原值聚合；空 = 直接访问）
      env.DB.prepare(
        "SELECT CASE WHEN referrer IS NULL OR referrer = '' THEN '(直接访问)' ELSE referrer END AS src, COUNT(*) AS n" +
        " FROM visits WHERE event = 'pageview' GROUP BY src ORDER BY n DESC LIMIT 10"
      ),
      // 国家 / 城市分布
      env.DB.prepare(
        "SELECT CASE WHEN country IS NULL OR country = '' THEN '(未知)' ELSE country END AS c, COUNT(*) AS n, COUNT(DISTINCT vid) AS u FROM visits WHERE event = 'pageview' GROUP BY c ORDER BY n DESC LIMIT 10"
      ),
      env.DB.prepare(
        "SELECT CASE WHEN city IS NULL OR city = '' THEN '(未知)' ELSE city END AS c, COUNT(*) AS n FROM visits WHERE event = 'pageview' AND city IS NOT NULL AND city != '' GROUP BY c ORDER BY n DESC LIMIT 10"
      ),
      // 语言与屏幕档
      env.DB.prepare(
        "SELECT CASE WHEN lang IS NULL OR lang = '' THEN '(未知)' ELSE lang END AS l, COUNT(*) AS n FROM visits WHERE event = 'pageview' GROUP BY l ORDER BY n DESC LIMIT 10"
      ),
      env.DB.prepare(
        "SELECT CASE WHEN screen IS NULL OR screen = '' THEN '(未知)' ELSE screen END AS s, COUNT(*) AS n FROM visits WHERE event = 'pageview' GROUP BY s ORDER BY n DESC LIMIT 10"
      )
    ]);
  } catch (e) {
    return new Response(JSON.stringify({ ok: false, error: 'db_read_failed' }), { status: 200, headers: headers });
  }

  var totals = r[0].results[0] || { n: 0, u: 0 };
  var today = r[1].results[0] || { n: 0, u: 0 };
  var body = {
    ok: true,
    total: totals.n,
    uniques: totals.u,
    today: today.n,
    todayUniques: today.u,
    days: r[2].results,
    hours: r[3].results,
    events: r[4].results,
    scenes: r[5].results,
    paths: r[6].results,
    referrers: r[7].results,
    countries: r[8].results,
    cities: r[9].results,
    langs: r[10].results,
    screens: r[11].results
  };
  return new Response(JSON.stringify(body), { status: 200, headers: headers });
}
