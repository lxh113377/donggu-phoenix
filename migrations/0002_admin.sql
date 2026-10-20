-- 0002_admin.sql —— 后台鉴权失败记录表（2026-10-20）
-- 用途：后台接口的暴力尝试限流。同一 IP 在窗口期内的失败次数超限后拒绝服务。
-- 成功登录不清理失败记录（自然过期即可，避免额外写放大）。
CREATE TABLE IF NOT EXISTS auth_fails (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  ip TEXT
);
CREATE INDEX IF NOT EXISTS idx_auth_fails_ip_ts ON auth_fails(ip, ts);
