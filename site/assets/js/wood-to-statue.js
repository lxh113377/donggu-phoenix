/* wood-to-statue.js — 「一木成像」连续雕刻引擎（Canvas 2D，零依赖、零外部请求）
 * 单一进度 p(0→1) 连续可拖：一段樟木 → 弹线定像 → 斧凿开坯 → 修光 → 上彩 → 贴金 → 开光。
 * 供落地页「一木成像」播放层与 AR 场景一共用同一套几何，保证两处画面完全同源。
 * 工序依据：刘卷《东固传统造像的制作工艺与仪式过程及其文化功能阐释》，《装饰》2015 年第 7 期；
 * 吉安市人民政府《东固传统造像》；井冈山报《樟木深处听刀音》2026-08-10（樟木、开面、雕銮匠、六百年）。
 */
(function (global) {
  'use strict';
  var TAU = Math.PI * 2, SIN = Math.sin, COS = Math.cos;
  function clamp(v, a, b) { return v < a ? a : (v > b ? b : v); }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function ease(t) { t = clamp(t, 0, 1); return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2; }
  function band(p, a, b) { return clamp((p - a) / (b - a), 0, 1); }
  function rnd(i) { var x = SIN(i * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); }
  function rgba(c, a) { return "rgba(" + c[0] + "," + c[1] + "," + c[2] + "," + a + ")"; }
  var GOLD = [212, 162, 76], GOLD_L = [232, 183, 97], RED = [179, 32, 44], VERM = [217, 79, 43];
  var FONT_KAI = "Kaiti SC, KaiTi, STKaiti, Songti SC, serif";
  var FONT_SANS = "system-ui, PingFang SC, Microsoft YaHei, sans-serif";

  /* ---- 竖向布局：u = 0 冠顶 → u = 1 莲座底；半宽以 s 为单位 ---- */
  var TOP = -0.62, SPAN = 1.02, BLOCK = 0.262, N = 88;
  var PROFILE = [
    [0.000, 0.014], [0.010, 0.034], [0.024, 0.056], [0.040, 0.063], [0.058, 0.057],
    [0.078, 0.050], [0.098, 0.041], [0.112, 0.029], [0.126, 0.026], [0.140, 0.049],
    [0.158, 0.104], [0.178, 0.132], [0.205, 0.143], [0.250, 0.152], [0.300, 0.164],
    [0.360, 0.171], [0.420, 0.166], [0.470, 0.155], [0.530, 0.164], [0.600, 0.178],
    [0.670, 0.192], [0.740, 0.210], [0.800, 0.226], [0.845, 0.236], [0.861, 0.196],
    [0.884, 0.244], [0.918, 0.286], [0.952, 0.268], [0.982, 0.226], [1.000, 0.170]
  ];
  function finalHW(u) {
    u = clamp(u, 0, 1);
    var i = 0;
    while (i < PROFILE.length - 2 && PROFILE[i + 1][0] < u) { i++; }
    var a = PROFILE[i], b = PROFILE[i + 1];
    var t = (u - a[0]) / ((b[0] - a[0]) || 1);
    t = clamp(t, 0, 1); t = t * t * (3 - 2 * t);
    return lerp(a[1], b[1], t);
  }
  /* 开坯波前：自上而下，带跳刀抖动 */
  function revealAt(u, pc) {
    var start = u * 0.72 + rnd(Math.round(u * N)) * 0.07;
    return clamp((pc * 1.72 - start) / 0.34, 0, 1);
  }
  function halfWidth(u, pc) {
    var f = finalHW(u);
    if (pc >= 1) { return f; }
    var r = revealAt(u, pc);
    var hw = lerp(BLOCK, f, r);
    var step = 0.020;
    hw += (Math.round(hw / step) * step - hw) * (1 - r) * (0.45 + 0.55 * rnd(Math.round(u * N) * 3.7));
    return hw;
  }
  function waveU(pc) { return clamp((pc * 1.72 - 0.18) / 0.72, 0, 1); }

  function bodyPath(ctx, cx, cy, s, pc) {
    ctx.beginPath();
    var i, u, hw, y;
    for (i = 0; i <= N; i++) {
      u = i / N; hw = halfWidth(u, pc) * s; y = cy + (TOP + u * SPAN) * s;
      if (i === 0) { ctx.moveTo(cx - hw, y); } else { ctx.lineTo(cx - hw, y); }
    }
    for (i = N; i >= 0; i--) {
      u = i / N; hw = halfWidth(u, pc) * s; y = cy + (TOP + u * SPAN) * s;
      ctx.lineTo(cx + hw, y);
    }
    ctx.closePath();
  }
  function autoBox(w, h) {
    if (w >= 900) {
      return { cx: w * 0.68, cy: h * 0.47, s: Math.min(h * 0.72, w * 0.33) };
    }
    var top = Math.min(104, h * 0.13), bottom = h * 0.385;
    return { cx: w * 0.5, cy: top + (bottom - top) * 0.5, s: Math.min(w * 0.88, (bottom - top) * 0.96) };
  }

  /* ---- 木料纹理：竖向纹理 + 顶部年轮 ---- */
  function grain(ctx, cx, cy, s, pc, alpha) {
    ctx.save();
    bodyPath(ctx, cx, cy, s, pc); ctx.clip();
    var top = cy + TOP * s, bot = cy + (TOP + SPAN) * s;
    for (var i = -7; i <= 7; i++) {
      ctx.beginPath();
      var bx = cx + i * s * 0.036;
      for (var y = top; y <= bot; y += 9) {
        var x = bx + SIN((y - top) * 0.021 + i * 1.7) * s * 0.012 + SIN((y - top) * 0.006 + i) * s * 0.006;
        if (y === top) { ctx.moveTo(x, y); } else { ctx.lineTo(x, y); }
      }
      ctx.strokeStyle = "rgba(46,26,12," + (alpha * (0.20 + (i % 3) * 0.05)) + ")";
      ctx.lineWidth = Math.max(0.8, s * 0.0035);
      ctx.stroke();
    }
    ctx.strokeStyle = "rgba(255,228,186," + (alpha * 0.14) + ")";
    ctx.beginPath(); ctx.moveTo(cx - s * 0.2, top); ctx.lineTo(cx - s * 0.2, bot); ctx.stroke();
    ctx.restore();
  }
  function endRings(ctx, cx, cy, s, a, pc) {
    if (a <= 0) { return; }
    /* 盘径 = 当前料口的实际半宽：开坯波前推过头部后，年轮随料口一起消失，不会悬在颈上 */
    var rx = halfWidth(0, pc || 0) * s, ry = rx * 0.72, y = cy + TOP * s;
    if (rx < s * 0.03) { return; }
    ctx.save(); ctx.globalAlpha = a;
    ctx.beginPath(); ctx.ellipse(cx, y, rx, ry, 0, 0, TAU);
    ctx.fillStyle = "#6B4426"; ctx.fill();
    for (var q = 1; q <= 5; q++) {
      ctx.beginPath();
      ctx.ellipse(cx - rx * 0.06, y, rx * q / 5.6, ry * q / 5.6, 0, 0, TAU);
      ctx.strokeStyle = "rgba(30,17,8,.55)"; ctx.lineWidth = Math.max(0.8, rx * 0.05); ctx.stroke();
    }
    ctx.beginPath(); ctx.ellipse(cx, y, rx, ry, 0, 0, TAU);
    ctx.strokeStyle = "rgba(255,228,186,.28)"; ctx.lineWidth = 1.4; ctx.stroke();
    ctx.restore();
  }
  /* 刀痕（修光阶段逐渐收干净） */
  function chisel(ctx, cx, cy, s, pc, a) {
    if (a <= 0) { return; }
    ctx.save(); bodyPath(ctx, cx, cy, s, pc); ctx.clip();
    ctx.globalAlpha = a;
    for (var i = 0; i < 46; i++) {
      var u = rnd(i * 5.3), y = cy + (TOP + u * SPAN) * s;
      var hw = halfWidth(u, pc) * s;
      var dir = rnd(i * 7.1) > 0.5 ? 1 : -1;
      var x0 = cx + dir * hw * (0.15 + rnd(i * 2.9) * 0.75);
      ctx.beginPath();
      ctx.moveTo(x0, y);
      ctx.quadraticCurveTo(x0 + dir * s * 0.026, y + s * 0.012, x0 + dir * s * 0.05, y - s * 0.004);
      ctx.strokeStyle = "rgba(58,32,14,.5)"; ctx.lineWidth = Math.max(0.8, s * 0.004);
      ctx.stroke();
    }
    ctx.restore();
  }

  /* ---- 定像：中轴 + 比例粉线 + 虚线轮廓 ---- */
  function layoutLines(ctx, cx, cy, s, a, dash) {
    if (a <= 0) { return; }
    ctx.save(); ctx.globalAlpha = a;
    ctx.strokeStyle = rgba(GOLD_L, 0.55); ctx.lineWidth = 1.2;
    ctx.beginPath(); ctx.moveTo(cx, cy + (TOP - 0.06) * s); ctx.lineTo(cx, cy + (TOP + SPAN + 0.03) * s); ctx.stroke();
    var marks = [[0.126, '颈'], [0.205, '肩'], [0.470, '腰'], [0.700, '膝'], [0.861, '座']];
    for (var i = 0; i < marks.length; i++) {
      var y = cy + (TOP + marks[i][0] * SPAN) * s;
      ctx.beginPath(); ctx.moveTo(cx - s * 0.34, y); ctx.lineTo(cx + s * 0.34, y);
      ctx.strokeStyle = rgba(GOLD, 0.30); ctx.lineWidth = 1; ctx.stroke();
      ctx.fillStyle = rgba(GOLD_L, 0.75); ctx.font = "11px " + FONT_KAI;
      ctx.textAlign = "left"; ctx.textBaseline = "bottom";
      ctx.fillText(marks[i][1], cx + s * 0.30, y - 2);
    }
    if (dash) {
      ctx.setLineDash([9, 8]); ctx.lineWidth = 1.5; ctx.strokeStyle = rgba([246, 241, 231], 0.55);
      bodyPath(ctx, cx, cy, s, 1); ctx.stroke();
      ctx.setLineDash([]);
    }
    ctx.restore();
  }

  /* ---- 彩绘与贴金 ---- */
  function painted(ctx, cx, cy, s, pLacq, pPaint, pGold, now) {
    if (pLacq <= 0 && pPaint <= 0 && pGold <= 0) { return; }
    ctx.save();
    bodyPath(ctx, cx, cy, s, 1); ctx.clip();
    var top = cy + TOP * s, bot = cy + (TOP + SPAN) * s;
    // 生漆打底：整体提亮
    if (pLacq > 0) {
      ctx.globalAlpha = pLacq * 0.9;
      ctx.fillStyle = "#C9B296";
      bodyPath(ctx, cx, cy, s, 1); ctx.fill();
      ctx.globalAlpha = 1;
    }
    // 贴金：自上而下的金层
    if (pGold > 0) {
      var gEdge = lerp(top - s * 0.03, bot, pGold);
      var gg = ctx.createLinearGradient(0, top, 0, bot);
      gg.addColorStop(0, "rgba(255,232,176,.95)");
      gg.addColorStop(0.45, "rgba(226,178,92,.92)");
      gg.addColorStop(1, "rgba(150,96,44,.9)");
      ctx.fillStyle = gg;
      ctx.fillRect(cx - s * 0.4, top - s * 0.04, s * 0.8, gEdge - top + s * 0.04);
      // 金层前沿亮线
      ctx.fillStyle = "rgba(255,246,214,.85)";
      ctx.fillRect(cx - s * 0.4, gEdge - s * 0.006, s * 0.8, s * 0.006);
    }
    // 彩绘：衣缘朱红、腰带、披帛、衣纹
    if (pPaint > 0) {
      ctx.globalAlpha = pPaint;
      ctx.fillStyle = "rgba(150,28,36,.80)";
      ctx.fillRect(cx - s * 0.3, cy + s * 0.20, s * 0.6, s * 0.030);
      ctx.fillStyle = "rgba(150,28,36,.55)";
      ctx.fillRect(cx - s * 0.24, cy + s * 0.235, s * 0.48, s * 0.013);
      ctx.fillStyle = rgba(GOLD_L, 0.92);
      ctx.fillRect(cx - s * 0.13, cy + s * 0.055, s * 0.26, s * 0.014);
      ctx.strokeStyle = "rgba(30,58,95,.55)"; ctx.lineWidth = Math.max(1.2, s * 0.008);
      ctx.beginPath(); ctx.moveTo(cx - s * 0.12, cy - s * 0.32);
      ctx.quadraticCurveTo(cx - s * 0.27, cy - s * 0.05, cx - s * 0.20, cy + s * 0.27); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(cx + s * 0.12, cy - s * 0.32);
      ctx.quadraticCurveTo(cx + s * 0.27, cy - s * 0.05, cx + s * 0.20, cy + s * 0.27); ctx.stroke();
      ctx.strokeStyle = "rgba(122,20,32,.34)"; ctx.lineWidth = Math.max(1, s * 0.0035);
      for (var i = -3; i <= 3; i++) {
        ctx.beginPath(); ctx.moveTo(cx + i * s * 0.03, cy + s * 0.02);
        ctx.quadraticCurveTo(cx + i * s * 0.06, cy + s * 0.18, cx + i * s * 0.095, cy + s * 0.30); ctx.stroke();
      }
      ctx.globalAlpha = 1;
    }
    // 莲瓣
    var petalA = Math.max(pLacq * 0.6, pPaint);
    if (petalA > 0) {
      ctx.globalAlpha = petalA;
      ctx.strokeStyle = pGold > 0.4 ? "rgba(122,20,32,.45)" : "rgba(88,52,26,.55)";
      ctx.lineWidth = Math.max(1, s * 0.0045);
      var py = cy + (TOP + 0.861 * SPAN) * s;
      for (var k = 0; k < 7; k++) {
        var x0 = cx - s * 0.20 + k * s * 0.0667;
        ctx.beginPath();
        ctx.moveTo(x0, py + s * 0.02);
        ctx.quadraticCurveTo(x0 + s * 0.0333, py + s * 0.115, x0 + s * 0.0667, py + s * 0.02);
        ctx.stroke();
      }
      ctx.globalAlpha = 1;
    }
    ctx.restore();
    // 贴金飞屑
    if (pGold > 0.02 && pGold < 0.99) {
      var gEdge2 = lerp(top - s * 0.03, bot, pGold);
      ctx.save();
      ctx.globalAlpha = (1 - Math.abs(pGold - 0.5) * 2) * 0.8;
      for (var gf = 0; gf < 20; gf++) {
        var gx = cx + (rnd(gf * 3.3) - 0.5) * s * 0.72;
        ctx.fillStyle = "rgba(255,236,180,.85)";
        ctx.fillRect(gx, gEdge2 + SIN(now * 0.002 + gf) * s * 0.05, s * 0.014, s * 0.006);
      }
      ctx.restore();
    }
  }

  /* ---- 面相与宝冠（开面） ---- */
  function face(ctx, cx, cy, s, a, opened) {
    if (a <= 0) { return; }
    var hy = cy + (TOP + 0.062 * SPAN) * s;   // 面部中心
    ctx.save(); ctx.globalAlpha = a;
    ctx.strokeStyle = "rgba(72,34,18,.62)"; ctx.lineWidth = Math.max(0.9, s * 0.0032); ctx.lineCap = "round";
    // 眉
    ctx.beginPath(); ctx.moveTo(cx - s * 0.034, hy - s * 0.012);
    ctx.quadraticCurveTo(cx - s * 0.017, hy - s * 0.022, cx - s * 0.004, hy - s * 0.012); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(cx + s * 0.004, hy - s * 0.012);
    ctx.quadraticCurveTo(cx + s * 0.017, hy - s * 0.022, cx + s * 0.034, hy - s * 0.012); ctx.stroke();
    // 微阖的眼
    ctx.beginPath(); ctx.moveTo(cx - s * 0.030, hy + s * 0.002);
    ctx.quadraticCurveTo(cx - s * 0.016, hy + s * 0.010, cx - s * 0.004, hy + s * 0.002); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(cx + s * 0.004, hy + s * 0.002);
    ctx.quadraticCurveTo(cx + s * 0.016, hy + s * 0.010, cx + s * 0.030, hy + s * 0.002); ctx.stroke();
    // 鼻与口
    ctx.beginPath(); ctx.moveTo(cx, hy + s * 0.004); ctx.lineTo(cx, hy + s * 0.018); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(cx - s * 0.010, hy + s * 0.027);
    ctx.quadraticCurveTo(cx, hy + s * 0.0305, cx + s * 0.010, hy + s * 0.027); ctx.stroke();
    if (opened > 0) {
      // 开光点眼
      ctx.globalAlpha = a * opened;
      ctx.fillStyle = "rgba(255,246,214,.95)";
      ctx.beginPath(); ctx.arc(cx - s * 0.017, hy + s * 0.005, s * 0.0035, 0, TAU); ctx.fill();
      ctx.beginPath(); ctx.arc(cx + s * 0.017, hy + s * 0.005, s * 0.0035, 0, TAU); ctx.fill();
      ctx.fillStyle = rgba(RED, 0.8);
      ctx.beginPath(); ctx.arc(cx, hy - s * 0.026, s * 0.004, 0, TAU); ctx.fill();
      ctx.globalAlpha = a;
    }
    // 宝冠
    ctx.fillStyle = rgba(GOLD_L, 0.92);
    ctx.beginPath();
    var cy0 = cy + (TOP + 0.026 * SPAN) * s;
    ctx.moveTo(cx - s * 0.058, cy0);
    ctx.quadraticCurveTo(cx - s * 0.040, cy0 - s * 0.058, cx - s * 0.013, cy0 - s * 0.050);
    ctx.quadraticCurveTo(cx, cy0 - s * 0.078, cx + s * 0.013, cy0 - s * 0.050);
    ctx.quadraticCurveTo(cx + s * 0.040, cy0 - s * 0.058, cx + s * 0.058, cy0);
    ctx.quadraticCurveTo(cx, cy0 - s * 0.020, cx - s * 0.058, cy0);
    ctx.closePath(); ctx.fill();
    ctx.strokeStyle = "rgba(96,40,16,.5)"; ctx.lineWidth = 1; ctx.stroke();
    ctx.restore();
  }

  /* ---- 舟形背光与头光（开光） ---- */
  function mandorla(ctx, cx, cy, s, a, now) {
    if (a <= 0) { return; }
    var topY = cy - s * 0.74, botY = cy + s * 0.44, mw = s * 0.44;
    ctx.save(); ctx.globalAlpha = a;
    var g = ctx.createRadialGradient(cx, cy - s * 0.1, s * 0.05, cx, cy - s * 0.1, s * 0.95);
    g.addColorStop(0, "rgba(255,247,224,.34)");
    g.addColorStop(0.5, "rgba(232,183,97,.18)");
    g.addColorStop(1, "rgba(212,162,76,0)");
    ctx.fillStyle = g;
    ctx.beginPath(); ctx.ellipse(cx, cy - s * 0.1, s * 0.9, s * 0.9, 0, 0, TAU); ctx.fill();
    // 舟形外焰
    ctx.beginPath();
    ctx.moveTo(cx, topY);
    ctx.bezierCurveTo(cx + mw, cy - s * 0.34, cx + mw * 0.86, cy + s * 0.16, cx, botY);
    ctx.bezierCurveTo(cx - mw * 0.86, cy + s * 0.16, cx - mw, cy - s * 0.34, cx, topY);
    ctx.closePath();
    ctx.strokeStyle = rgba(GOLD_L, 0.85); ctx.lineWidth = Math.max(1.4, s * 0.006); ctx.stroke();
    ctx.fillStyle = "rgba(255,240,206,.07)"; ctx.fill();
    // 焰口珠
    for (var k = 0; k < 26; k++) {
      var t = k / 26, ang = -Math.PI / 2 + t * TAU;
      var rr = 1 + 0.05 * SIN(now * 0.0016 + k);
      var px = cx + COS(ang) * mw * 0.99 * rr;
      var py = cy - s * 0.15 + SIN(ang) * (s * 0.60) * rr;
      ctx.beginPath(); ctx.arc(px, py, Math.max(1, s * 0.006), 0, TAU);
      ctx.fillStyle = rgba(GOLD, 0.5 + 0.4 * Math.abs(SIN(now * 0.0018 + k)));
      ctx.fill();
    }
    // 头光
    ctx.beginPath(); ctx.arc(cx, cy + (TOP + 0.062 * SPAN) * s, s * 0.13, 0, TAU);
    ctx.strokeStyle = "rgba(255,236,180,.8)"; ctx.lineWidth = Math.max(1.4, s * 0.005); ctx.stroke();
    ctx.restore();
  }

  /* ---- 斧 / 凿 / 笔 / 箔：跟随工序的器具 ---- */
  function tools(ctx, cx, cy, s, p, now) {
    var top = cy + TOP * s;
    // 开坯：斧（柄 + 斧眼 + 外扩刃口），随落斧摆动
    if (p > 0.20 && p < 0.50) {
      var pc = ease(band(p, 0.22, 0.50));
      var wy = top + waveU(pc) * SPAN * s;
      var swing = SIN(now * 0.008);
      ctx.save();
      ctx.translate(cx + s * 0.34, wy - s * 0.10);
      ctx.rotate(-0.55 + swing * 0.42);
      // 斧柄：微弯木柄，末端带握钮
      ctx.strokeStyle = "#5C3921"; ctx.lineWidth = Math.max(2.4, s * 0.015); ctx.lineCap = "round";
      ctx.beginPath();
      ctx.moveTo(-s * 0.005, 0);
      ctx.quadraticCurveTo(-s * 0.10, s * 0.03, -s * 0.20, s * 0.085);
      ctx.stroke();
      ctx.fillStyle = "#6B4426";
      ctx.beginPath(); ctx.arc(-s * 0.205, s * 0.088, Math.max(2, s * 0.012), 0, TAU); ctx.fill();
      // 斧头：靠柄一侧是斧眼，外侧是外扩的弧形刃
      var ag = ctx.createLinearGradient(0, -s * 0.05, s * 0.10, s * 0.05);
      ag.addColorStop(0, "rgba(120,130,142,.98)");
      ag.addColorStop(0.5, "rgba(206,214,224,.98)");
      ag.addColorStop(1, "rgba(150,160,172,.95)");
      ctx.fillStyle = ag;
      ctx.beginPath();
      ctx.moveTo(-s * 0.012, -s * 0.046);
      ctx.lineTo(s * 0.030, -s * 0.056);
      ctx.quadraticCurveTo(s * 0.098, -s * 0.040, s * 0.104, s * 0.004);
      ctx.quadraticCurveTo(s * 0.098, s * 0.048, s * 0.030, s * 0.060);
      ctx.lineTo(-s * 0.012, s * 0.050);
      ctx.closePath(); ctx.fill();
      ctx.strokeStyle = "rgba(40,44,52,.55)"; ctx.lineWidth = 1; ctx.stroke();
      // 刃口亮线
      ctx.strokeStyle = "rgba(255,252,240,.92)"; ctx.lineWidth = Math.max(1.4, s * 0.005);
      ctx.beginPath();
      ctx.moveTo(s * 0.086, -s * 0.030);
      ctx.quadraticCurveTo(s * 0.104, s * 0.004, s * 0.086, s * 0.036);
      ctx.stroke();
      // 斧眼暗部
      ctx.fillStyle = "rgba(30,26,22,.55)";
      ctx.fillRect(-s * 0.014, -s * 0.040, s * 0.016, s * 0.082);
      ctx.restore();
    }
    // 修光：凿（钢杆 + 斜刃）与木槌
    if (p > 0.48 && p < 0.63) {
      var a = band(p, 0.48, 0.52) * (1 - band(p, 0.60, 0.63));
      var wy2 = top + (0.25 + 0.6 * band(p, 0.50, 0.62)) * SPAN * s;
      var tap = SIN(now * 0.009) * 0.35;
      ctx.save(); ctx.globalAlpha = a;
      ctx.translate(cx + s * 0.20, wy2);
      ctx.rotate(-0.30);
      // 钢杆
      ctx.fillStyle = "rgba(214,221,229,.95)";
      ctx.fillRect(0, -s * 0.009, s * 0.115, s * 0.018);
      // 斜刃口
      ctx.beginPath();
      ctx.moveTo(0, -s * 0.009); ctx.lineTo(-s * 0.030, -s * 0.016);
      ctx.lineTo(-s * 0.030, s * 0.006); ctx.lineTo(0, s * 0.009);
      ctx.closePath(); ctx.fillStyle = "rgba(236,241,246,.98)"; ctx.fill();
      // 木柄
      ctx.fillStyle = "rgba(92,57,33,.98)";
      ctx.fillRect(s * 0.115, -s * 0.014, s * 0.085, s * 0.028);
      ctx.restore();
      // 木槌
      ctx.save(); ctx.globalAlpha = a;
      ctx.translate(cx + s * 0.34, wy2 - s * 0.06 - tap * s * 0.05);
      ctx.rotate(0.5 - tap * 0.5);
      ctx.strokeStyle = "rgba(92,57,33,.98)"; ctx.lineWidth = Math.max(2, s * 0.011);
      ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(s * 0.10, s * 0.06); ctx.stroke();
      ctx.fillStyle = "rgba(138,95,53,.98)";
      ctx.fillRect(-s * 0.045, -s * 0.028, s * 0.075, s * 0.056);
      ctx.restore();
    }
    // 彩绘：毛笔（竹杆 + 深色笔管 + 吸了朱漆的软毫），笔尖贴着衣缘走
    if (p > 0.62 && p < 0.80) {
      var a2 = band(p, 0.62, 0.66) * (1 - band(p, 0.76, 0.80));
      var t3 = band(p, 0.62, 0.78);
      var wy3 = top + (0.30 + 0.60 * t3) * SPAN * s;
      var bx = cx + s * 0.26;
      ctx.save(); ctx.globalAlpha = a2;
      ctx.translate(bx, wy3);
      ctx.rotate(2.35);
      // 竹杆
      ctx.strokeStyle = "#8A6A3E"; ctx.lineWidth = Math.max(2.2, s * 0.013); ctx.lineCap = "round";
      ctx.beginPath(); ctx.moveTo(s * 0.02, 0); ctx.lineTo(s * 0.20, 0); ctx.stroke();
      ctx.strokeStyle = "rgba(255,240,206,.35)"; ctx.lineWidth = Math.max(1, s * 0.004);
      ctx.beginPath(); ctx.moveTo(s * 0.04, -s * 0.004); ctx.lineTo(s * 0.19, -s * 0.004); ctx.stroke();
      // 笔管
      ctx.fillStyle = "#2B211C";
      ctx.fillRect(s * 0.005, -s * 0.010, s * 0.026, s * 0.020);
      // 软毫（含朱漆）
      var lg = ctx.createLinearGradient(-s * 0.055, 0, s * 0.01, 0);
      lg.addColorStop(0, "rgba(150,28,36,.95)");
      lg.addColorStop(1, "rgba(74,52,38,.95)");
      ctx.fillStyle = lg;
      ctx.beginPath();
      ctx.moveTo(s * 0.008, -s * 0.009);
      ctx.quadraticCurveTo(-s * 0.048, -s * 0.010, -s * 0.058, 0);
      ctx.quadraticCurveTo(-s * 0.048, s * 0.010, s * 0.008, s * 0.009);
      ctx.closePath(); ctx.fill();
      ctx.restore();
      // 笔尖拖出的一道湿漆
      ctx.save(); ctx.globalAlpha = a2 * 0.8;
      ctx.strokeStyle = "rgba(150,28,36,.7)"; ctx.lineWidth = Math.max(1.4, s * 0.006); ctx.lineCap = "round";
      ctx.beginPath();
      ctx.moveTo(bx - s * 0.02, wy3 + s * 0.012);
      ctx.quadraticCurveTo(bx - s * 0.10, wy3 + s * 0.030, bx - s * 0.17, wy3 + s * 0.018);
      ctx.stroke();
      ctx.restore();
    }
    // 贴金：金箔
    if (p > 0.74 && p < 0.88) {
      var a3 = band(p, 0.74, 0.78) * (1 - band(p, 0.84, 0.88));
      ctx.save(); ctx.globalAlpha = a3;
      ctx.translate(cx - s * 0.60, top + (0.14 + 0.40 * band(p, 0.74, 0.88)) * SPAN * s);
      ctx.rotate(-0.14 + SIN(now * 0.0016) * 0.07);
      // 持箔的竹镊（夹在箔角，不外伸）
      ctx.strokeStyle = "rgba(126,152,102,.9)"; ctx.lineWidth = Math.max(1.4, s * 0.006);
      ctx.beginPath(); ctx.moveTo(s * 0.19, s * 0.01); ctx.lineTo(s * 0.27, -s * 0.06); ctx.stroke();
      var fg = ctx.createLinearGradient(0, 0, s * 0.2, s * 0.16);
      fg.addColorStop(0, "rgba(255,244,206,.98)");
      fg.addColorStop(0.5, "rgba(232,183,97,.96)");
      fg.addColorStop(1, "rgba(176,120,44,.92)");
      ctx.fillStyle = fg;
      ctx.fillRect(0, 0, s * 0.2, s * 0.16);
      ctx.strokeStyle = "rgba(255,250,232,.85)"; ctx.lineWidth = 1;
      ctx.strokeRect(0, 0, s * 0.2, s * 0.16);
      // 箔面反光
      ctx.globalAlpha = a3 * 0.5;
      ctx.fillStyle = "rgba(255,255,255,.55)";
      ctx.beginPath();
      ctx.moveTo(0, s * 0.16); ctx.lineTo(s * 0.2, 0); ctx.lineTo(s * 0.2, s * 0.05); ctx.lineTo(s * 0.05, s * 0.16);
      ctx.closePath(); ctx.fill();
      ctx.restore();
    }
  }

  /* ---- 木屑 ---- */
  function chips(ctx, cx, cy, s, pc, now) {
    if (pc <= 0.02 || pc >= 0.995) { return; }
    var wy = cy + (TOP + waveU(pc) * SPAN) * s;
    var hw = BLOCK * s;
    ctx.save();
    for (var k = 0; k < 30; k++) {
      var age = (now * 0.00055 + rnd(k * 1.7)) % 1;
      var dir = rnd(k * 3.1) > 0.5 ? 1 : -1;
      var v = 0.35 + rnd(k * 5.7) * 0.9;
      var x = cx + dir * (hw * (0.6 + rnd(k) * 0.5)) + dir * age * s * v * 0.9;
      var y = wy - age * s * 0.16 + age * age * s * 0.42;
      ctx.globalAlpha = 0.6 * (1 - age) * Math.min(1, pc * 6);
      ctx.fillStyle = k % 3 === 0 ? "#A87543" : "#7A5230";
      ctx.save();
      ctx.translate(x, y); ctx.rotate(age * 6 + k);
      ctx.fillRect(-s * 0.014, -s * 0.006, s * 0.028, s * 0.011);
      ctx.restore();
    }
    ctx.restore();
  }

  /* ---- 背景板：整块木料纹理 + 木节涡纹（呼应「木雕彩绘」宣传物料的木作底） ---- */
  function backdrop(ctx, w, h, now) {
    var g = ctx.createLinearGradient(0, 0, w, h);
    g.addColorStop(0, "#4A2C16");
    g.addColorStop(0.45, "#6B4426");
    g.addColorStop(0.75, "#4A2B15");
    g.addColorStop(1, "#2A180C");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, w, h);
    // 竖向木纹：疏密不均的长弧
    for (var i = 0; i < 34; i++) {
      var x0 = (i / 34) * w + rnd(i * 1.7) * (w / 34) * 1.4;
      var amp = w * (0.012 + rnd(i * 3.3) * 0.030);
      var ph = rnd(i * 5.1) * TAU;
      ctx.beginPath();
      for (var y = -10; y <= h + 10; y += 14) {
        var x = x0 + SIN(y * 0.0042 + ph) * amp + SIN(y * 0.0011 + ph * 1.7) * amp * 1.6;
        if (y === -10) { ctx.moveTo(x, y); } else { ctx.lineTo(x, y); }
      }
      ctx.strokeStyle = "rgba(28,15,7," + (0.10 + (i % 5) * 0.030) + ")";
      ctx.lineWidth = Math.max(0.9, h * 0.0022) * (1 + (i % 3) * 0.5);
      ctx.stroke();
    }
    // 亮纹
    for (var b = 0; b < 9; b++) {
      var bx = ((b + 0.5) / 9) * w + SIN(b * 2.1) * w * 0.02;
      ctx.beginPath();
      for (var y2 = 0; y2 <= h; y2 += 16) {
        var x2 = bx + SIN(y2 * 0.005 + b) * w * 0.014;
        if (y2 === 0) { ctx.moveTo(x2, y2); } else { ctx.lineTo(x2, y2); }
      }
      ctx.strokeStyle = "rgba(255,222,168,.055)";
      ctx.lineWidth = Math.max(0.8, h * 0.0016);
      ctx.stroke();
    }
    // 木节：涡纹同心椭圆
    var knots = [[0.72, 0.30, 0.062], [0.20, 0.74, 0.040]];
    for (var k = 0; k < knots.length; k++) {
      var kx = knots[k][0] * w, ky = knots[k][1] * h, kr = knots[k][2] * Math.min(w, h);
      for (var q = 5; q >= 1; q--) {
        ctx.beginPath();
        ctx.ellipse(kx, ky, kr * q / 5.2, kr * q / 3.6, 0.32 + k * 0.4, 0, TAU);
        ctx.strokeStyle = "rgba(26,13,6," + (0.16 + (5 - q) * 0.05) + ")";
        ctx.lineWidth = Math.max(1, kr * 0.10);
        ctx.stroke();
      }
      ctx.beginPath();
      ctx.ellipse(kx, ky, kr * 0.20, kr * 0.34, 0.32 + k * 0.4, 0, TAU);
      ctx.fillStyle = "rgba(22,11,5,.5)"; ctx.fill();
    }
    // 山峦剪影：把造像供在山里的观感带进来（海报下半的墨色岭脊）
    var ridgeBase = h * 0.995;
    var ridges = [
      { amp: h * 0.115, y: ridgeBase - h * 0.155, c: "rgba(38,22,12,.42)", f: 0.0055, p: 0.7 },
      { amp: h * 0.085, y: ridgeBase - h * 0.085, c: "rgba(24,14,8,.55)", f: 0.0082, p: 2.4 },
      { amp: h * 0.055, y: ridgeBase - h * 0.030, c: "rgba(12,7,4,.62)", f: 0.0125, p: 4.1 }
    ];
    for (var rg = 0; rg < ridges.length; rg++) {
      var R = ridges[rg];
      ctx.beginPath();
      ctx.moveTo(-10, h + 10);
      for (var mx = -10; mx <= w + 10; mx += 9) {
        var my = R.y - SIN(mx * R.f + R.p) * R.amp - SIN(mx * R.f * 2.7 + R.p * 1.6) * R.amp * 0.34;
        ctx.lineTo(mx, my);
      }
      ctx.lineTo(w + 10, h + 10);
      ctx.closePath();
      ctx.fillStyle = R.c;
      ctx.fill();
    }
    // 岭脊亮边：木纹被光勾出的那道棱
    ctx.beginPath();
    for (var m2 = -10; m2 <= w + 10; m2 += 9) {
      var y2b = ridges[1].y - SIN(m2 * ridges[1].f + ridges[1].p) * ridges[1].amp - SIN(m2 * ridges[1].f * 2.7 + ridges[1].p * 1.6) * ridges[1].amp * 0.34;
      if (m2 === -10) { ctx.moveTo(m2, y2b); } else { ctx.lineTo(m2, y2b); }
    }
    ctx.strokeStyle = "rgba(255,214,158,.10)";
    ctx.lineWidth = Math.max(1, h * 0.0022);
    ctx.stroke();

    // 暗角：把视线压回像身
    var vg = ctx.createRadialGradient(w * 0.62, h * 0.48, Math.min(w, h) * 0.16, w * 0.62, h * 0.48, Math.max(w, h) * 0.82);
    vg.addColorStop(0, "rgba(0,0,0,0)");
    vg.addColorStop(0.62, "rgba(10,6,4,.42)");
    vg.addColorStop(1, "rgba(8,5,3,.86)");
    ctx.fillStyle = vg;
    ctx.fillRect(0, 0, w, h);
  }

  /* ---- 光柱与浮尘（呼应造像馆侧光） ---- */
  function beam(ctx, w, h, cx, cy, s, a) {
    ctx.save();
    ctx.globalAlpha = a;
    var g = ctx.createLinearGradient(w * 0.18, 0, cx + s * 0.2, cy + s * 0.4);
    g.addColorStop(0, "rgba(255,244,222,.16)");
    g.addColorStop(1, "rgba(255,244,222,0)");
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.moveTo(w * 0.06, -h * 0.05); ctx.lineTo(w * 0.34, -h * 0.05);
    ctx.lineTo(cx + s * 0.34, cy + s * 0.5); ctx.lineTo(cx - s * 0.02, cy + s * 0.56);
    ctx.closePath(); ctx.fill();
    ctx.restore();
  }
  function motes(ctx, w, h, now, count) {
    for (var d = 0; d < (count || 30); d++) {
      var x = (rnd(d * 1.9) * 0.9 + 0.05) * w;
      var y = ((now * 0.010 + d * 57) % (h + 40)) - 20;
      ctx.fillStyle = rgba(GOLD_L, 0.05 + (d % 4) * 0.016);
      ctx.beginPath(); ctx.arc(x, y, 0.9 + (d % 3) * 0.5, 0, TAU); ctx.fill();
    }
  }
  function smoke(ctx, cx, cy, s, a, now) {
    if (a <= 0) { return; }
    ctx.save(); ctx.globalAlpha = a * 0.5;
    for (var i = 0; i < 3; i++) {
      ctx.beginPath();
      var bx = cx + (i - 1) * s * 0.16, by = cy + s * 0.46;
      for (var k = 0; k <= 12; k++) {
        var t = k / 12;
        var x = bx + SIN(t * 3.1 + now * 0.0009 + i) * s * 0.05 * t;
        var y = by - t * s * 0.62;
        if (k === 0) { ctx.moveTo(x, y); } else { ctx.lineTo(x, y); }
      }
      ctx.strokeStyle = "rgba(246,241,231,.30)"; ctx.lineWidth = Math.max(1, s * 0.004);
      ctx.stroke();
    }
    ctx.restore();
  }
  function seal(ctx, cx, cy, r, text, color, rot, a) {
    if (a <= 0) { return; }
    ctx.save(); ctx.globalAlpha = a;
    ctx.translate(cx, cy); ctx.rotate(rot || 0);
    ctx.fillStyle = rgba(color, 0.16);
    ctx.beginPath(); ctx.arc(0, 0, r, 0, TAU); ctx.fill();
    ctx.strokeStyle = rgba(color, 0.95); ctx.lineWidth = Math.max(2, r * 0.075);
    ctx.beginPath(); ctx.arc(0, 0, r, 0, TAU); ctx.stroke();
    ctx.lineWidth = Math.max(1, r * 0.03);
    ctx.beginPath(); ctx.arc(0, 0, r * 0.83, 0, TAU); ctx.stroke();
    ctx.fillStyle = rgba(color, 0.95);
    ctx.font = "600 " + Math.round(r * 0.62) + "px " + FONT_KAI;
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.fillText(text, 0, r * 0.04);
    ctx.restore();
  }

  /* ---- 阶段表：落地页刻度与 AR 章节共用 ---- */
  var STAGES = [
    { key: 'wood',   name: '选木',   en: 'Choosing the Wood',   at: [0.00, 0.10] },
    { key: 'layout', name: '定像',   en: 'Fixing the Iconography', at: [0.10, 0.22] },
    { key: 'block',  name: '开坯',   en: 'Blocking Out',        at: [0.22, 0.50] },
    { key: 'refine', name: '修光',   en: 'Refining',            at: [0.50, 0.62] },
    { key: 'paint',  name: '彩绘贴金', en: 'Painting & Gilding', at: [0.62, 0.84] },
    { key: 'open',   name: '开光',   en: 'Consecration',        at: [0.84, 1.00] }
  ];
  /* AR 场景一为 5 章：把章序 + 章内进度映射到同一根进度轴 */
  var MAP = [0.00, 0.10, 0.22, 0.50, 0.84, 1.00];
  function progress(idx, local) {
    var i = clamp(Math.round(idx), 0, MAP.length - 2);
    return lerp(MAP[i], MAP[i + 1], clamp(local, 0, 1));
  }
  function stageOf(p) {
    for (var i = STAGES.length - 1; i >= 0; i--) { if (p >= STAGES[i].at[0]) { return i; } }
    return 0;
  }

  /* ================= 主绘制 ================= */
  function draw(ctx, w, h, p, now, opts) {
    opts = opts || {};
    p = clamp(p, 0, 1);
    var box = opts.box || autoBox(w, h);
    var cx = box.cx, cy = box.cy, s = box.s;
    var pLine = band(p, 0.10, 0.20);
    var pc = ease(band(p, 0.22, 0.50));
    var pSand = band(p, 0.50, 0.62);
    var pLacq = band(p, 0.58, 0.66);
    var pPaint = ease(band(p, 0.62, 0.80));
    var pGold = ease(band(p, 0.72, 0.86));
    var pOpen = band(p, 0.84, 1.00);

    if (opts.backdrop) { backdrop(ctx, w, h, now); }
    if (opts.beam !== false) { beam(ctx, w, h, cx, cy, s, opts.backdrop ? 0.75 : 0.9); }

    // 背光（开光阶段在像后亮起）
    if (pOpen > 0) { mandorla(ctx, cx, cy, s, ease(pOpen), now); }

    // 落影
    ctx.save();
    ctx.globalAlpha = 0.5 * (0.35 + 0.65 * pc);
    var sg = ctx.createRadialGradient(cx, cy + s * 0.42, 0, cx, cy + s * 0.42, s * 0.42);
    sg.addColorStop(0, "rgba(0,0,0,.55)"); sg.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = sg;
    ctx.beginPath(); ctx.ellipse(cx, cy + s * 0.42, s * 0.40, s * 0.07, 0, 0, TAU); ctx.fill();
    ctx.restore();

    // 木体
    ctx.save();
    var wg = ctx.createLinearGradient(cx - BLOCK * s, 0, cx + BLOCK * s, 0);
    wg.addColorStop(0, "#2E1B0F"); wg.addColorStop(0.34, "#5C3921");
    wg.addColorStop(0.62, "#7A5230"); wg.addColorStop(1, "#3A2213");
    ctx.fillStyle = wg;
    bodyPath(ctx, cx, cy, s, pc); ctx.fill();
    ctx.restore();
    grain(ctx, cx, cy, s, pc, 1 - pLacq * 0.85);
    endRings(ctx, cx, cy, s, (1 - pc * 2.4) * (1 - pLacq), pc);
    chisel(ctx, cx, cy, s, pc, (1 - pSand) * (pc > 0.5 ? 1 : pc * 2));

    // 彩绘 / 贴金
    if (pLacq > 0 || pPaint > 0 || pGold > 0) { painted(ctx, cx, cy, s, pLacq, pPaint, pGold, now); }
    // 开面
    face(ctx, cx, cy, s, band(p, 0.40, 0.56) * (0.6 + 0.4 * pSand), band(p, 0.88, 0.97));
    // 定像粉线（进入开坯即隐去）
    layoutLines(ctx, cx, cy, s, pLine * (1 - band(p, 0.20, 0.30)), true);

    chips(ctx, cx, cy, s, pc, now);
    if (opts.tools !== false) { tools(ctx, cx, cy, s, p, now); }
    smoke(ctx, cx, cy, s, band(p, 0.88, 1), now);
    if (pOpen > 0.42) {
      seal(ctx, cx + s * 0.34, cy + s * 0.20, s * 0.068, "开", RED, -0.12, band(pOpen, 0.42, 0.8));
    }
    if (opts.motes !== false) { motes(ctx, w, h, now, opts.moteCount || 26); }
    if (opts.caption && opts.stageLabel) {
      ctx.save();
      ctx.font = "600 12px " + FONT_SANS; ctx.textAlign = "left"; ctx.textBaseline = "top";
      ctx.fillStyle = rgba(GOLD_L, 0.9);
      ctx.fillText(opts.stageLabel, 18, 16);
      ctx.restore();
    }
  }

  global.WOOD_TO_STATUE = {
    draw: draw,
    autoBox: autoBox,
    bodyPath: bodyPath,
    halfWidth: halfWidth,
    finalHW: finalHW,
    progress: progress,
    stageOf: stageOf,
    STAGES: STAGES,
    MAP: MAP,
    backdrop: backdrop,
    utils: { clamp: clamp, lerp: lerp, ease: ease, band: band, rgba: rgba, seal: seal, motes: motes, beam: beam }
  };
})(window);
