-- 0001_init.sql —— 访问数据表初始化（2026-10-20）
-- 隐私边界：只存匿名统计字段（事件、路径、场景、随机访客号、语言、屏幕档、
-- 边缘地理与 UA），不含任何可识别个人身份的信息，不做跨站跟踪。
CREATE TABLE IF NOT EXISTS visits (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  day TEXT NOT NULL DEFAULT (date('now')),
  event TEXT NOT NULL DEFAULT 'pageview',
  path TEXT,
  scene TEXT,
  vid TEXT,
  referrer TEXT,
  ua TEXT,
  lang TEXT,
  screen TEXT,
  country TEXT,
  city TEXT,
  tz TEXT
);
CREATE INDEX IF NOT EXISTS idx_visits_day ON visits(day);
CREATE INDEX IF NOT EXISTS idx_visits_event ON visits(event);
CREATE INDEX IF NOT EXISTS idx_visits_scene ON visits(scene, day);
CREATE INDEX IF NOT EXISTS idx_visits_vid ON visits(vid);
