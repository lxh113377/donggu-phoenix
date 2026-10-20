// functions/api/admin/_middleware.js —— 后台接口统一鉴权 + 失败限流
// 适用于 /api/admin/* 下全部端点：请求头 X-Admin-Key 与 Pages secret ADMIN_KEY 比对。
// 限流：同一 IP 15 分钟内鉴权失败超过 20 次 → 429（防暴力枚举）。
// ADMIN_KEY 未配置时返回 503（提示运维去配置，而不是假装拒绝）。
var FAIL_LIMIT = 20;

function json(body, status) {
  return new Response(JSON.stringify(body), {
    status: status || 200,
    headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' }
  });
}

export async function onRequest(context) {
  var request = context.request, env = context.env;

  if (!env.ADMIN_KEY) { return json({ ok: false, error: 'admin_key_not_configured' }, 503); }

  var ip = request.headers.get('cf-connecting-ip') || 'unknown';

  // 先查限流（表缺失时跳过，不因限流表故障把后台整个锁死）
  try {
    var row = await env.DB.prepare(
      "SELECT COUNT(*) AS n FROM auth_fails WHERE ip = ? AND ts > datetime('now', '-15 minutes')"
    ).bind(ip).first();
    if (row && row.n > FAIL_LIMIT) { return json({ ok: false, error: 'rate_limited' }, 429); }
  } catch (e) { /* 限流表异常：放行走密钥校验 */ }

  var key = request.headers.get('x-admin-key') || '';
  if (!key || key !== env.ADMIN_KEY) {
    try {
      await env.DB.prepare('INSERT INTO auth_fails (ip) VALUES (?)').bind(ip).run();
    } catch (e) {}
    return json({ ok: false, error: 'auth_failed' }, 401);
  }

  return context.next();
}
