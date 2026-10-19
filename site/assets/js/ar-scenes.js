/* ar-scenes.js — AR 展陈三场景渲染器（Canvas 2D，零依赖、零模型文件、零外部请求）
 * 所有图形由代码绘制（造像、红旗、山谷、凤凰均为参数化矢量）。
 * 场景一 craft：一木成像 —— 选木 → 定像 → 开坯 → 修光 → 彩绘贴金 → 开光（几何见 wood-to-statue.js）
 * 场景二 red：东固会师 → 龙冈大捷 → 白云山首战 → 六渡坳
 * 场景三 phoenix：图腾浮现 → 三公主羽衣 → 振翅盘旋 → 落羽归位
 * 版式：宽屏（>=900px）主体画面靠右、左侧留解说；窄屏主画面靠上、解说在下。
 */
(function (global) {
  'use strict';
  var TAU = Math.PI * 2;
  var FONT_KAI = "Kaiti SC, KaiTi, STKaiti, Songti SC, serif";
  var FONT_SANS = "system-ui, PingFang SC, Microsoft YaHei, sans-serif";
  var SIN = Math.sin, COS = Math.cos;
  function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
  function ease(t) { t = clamp(t, 0, 1); return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2; }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function rgba(c, a) { return "rgba(" + c[0] + "," + c[1] + "," + c[2] + "," + a + ")"; }
  var GOLD = [212, 162, 76], GOLD_L = [232, 183, 97], RED = [179, 32, 44];

  /* 画面安全区：宽屏铺满（解说在左侧留白处），窄屏只占上半屏，下半留给解说 */
  function visualBox(w, h) {
    if (w >= 900) {
      return { cx: w * 0.68, cy: h * 0.47, s: Math.min(h * 0.72, w * 0.33), top: 0, bottom: h };
    }
    var top = Math.min(104, h * 0.13);
    var bottom = h * 0.385;
    return {
      cx: w * 0.5,
      cy: top + (bottom - top) * 0.5,
      s: Math.min(w * 0.88, (bottom - top) * 0.96),
      top: top,
      bottom: bottom
    };
  }

  function sealMark(ctx, cx, cy, r, text, color, rot) {
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(rot || 0);
    ctx.fillStyle = rgba(color, 0.14);
    ctx.beginPath();
    ctx.arc(0, 0, r, 0, TAU);
    ctx.fill();
    ctx.strokeStyle = rgba(color, 0.95);
    ctx.lineWidth = Math.max(2, r * 0.075);
    ctx.beginPath();
    ctx.arc(0, 0, r, 0, TAU);
    ctx.stroke();
    ctx.lineWidth = Math.max(1, r * 0.03);
    ctx.beginPath();
    ctx.arc(0, 0, r * 0.83, 0, TAU);
    ctx.stroke();
    ctx.fillStyle = rgba(color, 0.95);
    ctx.font = "600 " + Math.round(r * 0.62) + "px " + FONT_KAI;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(text, 0, r * 0.04);
    ctx.restore();
  }

  function dust(ctx, w, h, now, color, count) {
    for (var d = 0; d < (count || 26); d++) {
      var x = (SIN(d * 1.37) * 0.5 + 0.5) * w;
      var y = ((now * 0.011 + d * 61) % (h + 40)) - 20;
      ctx.fillStyle = rgba(color, 0.05 + (d % 4) * 0.016);
      ctx.beginPath();
      ctx.arc(x, y, 0.9 + (d % 3) * 0.5, 0, TAU);
      ctx.fill();
    }
  }

  function chapterRail(ctx, w, h, chapters, idx) {
    var labels = [], i;
    for (i = 0; i < chapters.length; i++) {
      labels.push(chapters[i].title.replace(/^[一二三四五] · /, ""));
    }
    ctx.save();
    if (w >= 900) {
      var x = w - Math.min(58, w * 0.055);
      var top = h * 0.5 - (labels.length - 1) * 34;
      ctx.textAlign = "right";
      ctx.textBaseline = "middle";
      for (i = 0; i < labels.length; i++) {
        var y = top + i * 68;
        var on = i <= idx;
        ctx.font = (i === idx ? "13px " : "12px ") + FONT_SANS;
        ctx.fillStyle = i === idx ? "rgba(242,233,220,.92)" : (on ? "rgba(242,233,220,.5)" : "rgba(242,233,220,.24)");
        ctx.fillText(labels[i], x - 18, y);
        ctx.beginPath();
        ctx.arc(x, y, i === idx ? 3.6 : 2.4, 0, TAU);
        ctx.fillStyle = i === idx ? rgba(GOLD_L, 0.95) : (on ? rgba(GOLD, 0.55) : rgba(GOLD, 0.22));
        ctx.fill();
        if (i < labels.length - 1) {
          ctx.beginPath();
          ctx.moveTo(x, y + 8);
          ctx.lineTo(x, y + 60);
          ctx.strokeStyle = "rgba(212,162,76,.16)";
          ctx.lineWidth = 1;
          ctx.stroke();
        }
      }
    } else {
      var gap = Math.min(26, w * 0.07);
      var y2 = h * 0.455;
      var startX = w * 0.5 - (labels.length - 1) * gap / 2;
      for (i = 0; i < labels.length; i++) {
        var on2 = i <= idx;
        ctx.beginPath();
        ctx.arc(startX + i * gap, y2, i === idx ? 3.4 : 2.2, 0, TAU);
        ctx.fillStyle = i === idx ? rgba(GOLD_L, 0.95) : (on2 ? rgba(GOLD, 0.5) : rgba(GOLD, 0.2));
        ctx.fill();
      }
    }
    ctx.restore();
  }

  /* ================= 场景一：东固传统造像 —— 一木成像（连续雕刻） =================
   * 画面几何统一由 assets/js/wood-to-statue.js 提供：一段樟木随解说进度被连续雕成神像，
   * 五章映射到同一根进度轴（选木→定像→开坯→修光·彩绘·贴金→开光），与落地页「一木成像」同源。
   */
  function CraftScene(data) {
    this.id = "craft";
    this.data = data;
    this.name = data.name;
    this.en = data.en;
    this.duration = data.duration;
    this.chapters = data.chapters;
    this.t = 0;
  }
  CraftScene.prototype.seek = function (t) { this.t = clamp(t, 0, this.duration); };

  CraftScene.prototype.draw = function (ctx, w, h, now) {
    var S = Math.min(w, h), box = visualBox(w, h);
    var n = this.chapters.length;
    var stageLen = this.duration / n;
    var idx = clamp(Math.floor(this.t / stageLen), 0, n - 1);
    var local = (this.t - idx * stageLen) / stageLen;

    var bg = ctx.createRadialGradient(box.cx, box.cy, S * 0.05, box.cx, box.cy, S * 0.95);
    bg.addColorStop(0, "rgba(126,66,26,.36)");
    bg.addColorStop(0.5, "rgba(44,24,14,.2)");
    bg.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, w, h);

    var E = global.WOOD_TO_STATUE;
    if (E) {
      // 本场景有背光，顶点比另两段高：略缩并下移，避开顶部场景胶囊与右侧章节轨
      var cbox = w >= 900
        ? { cx: box.cx, cy: box.cy + box.s * 0.05, s: box.s * 0.90 }
        : { cx: box.cx, cy: box.cy + box.s * 0.02, s: box.s * 0.92 };
      E.draw(ctx, w, h, E.progress(idx, local), now, { box: cbox, moteCount: 28 });
    } else {
      // 引擎缺失时的兜底：只画一条中轴与虚线轮廓，不留白屏
      ctx.save();
      ctx.strokeStyle = "rgba(232,183,97,.5)";
      ctx.lineWidth = 1.4; ctx.setLineDash([9, 8]);
      ctx.beginPath();
      ctx.moveTo(box.cx, box.cy - box.s * 0.62);
      ctx.lineTo(box.cx, box.cy + box.s * 0.40);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.restore();
    }

    dust(ctx, w, h, now, GOLD_L, 28);
    chapterRail(ctx, w, h, this.chapters, idx);
  };
  /* ================= 场景二：红色地标历史复原 ================= */
  function RedScene(data) {
    this.id = "red";
    this.data = data;
    this.name = data.name;
    this.en = data.en;
    this.duration = data.duration;
    this.chapters = data.chapters;
    this.t = 0;
    this.stars = [];
    for (var i = 0; i < 56; i++) {
      this.stars.push([Math.random(), Math.random() * 0.5, Math.random() * 1.1 + 0.4]);
    }
    this.trees = [];
    for (var j = 0; j < 22; j++) {
      this.trees.push([Math.random(), 0.5 + Math.random() * 0.16, 0.5 + Math.random()]);
    }
  }
  RedScene.prototype.seek = function (t) { this.t = clamp(t, 0, this.duration); };

  function ridges(ctx, w, h, baseY, color, amp, phase) {
    ctx.beginPath();
    ctx.moveTo(-10, h);
    for (var x = -10; x <= w + 10; x += 12) {
      var y = baseY - SIN(x * 0.006 + phase) * amp - SIN(x * 0.017 + phase * 1.7) * amp * 0.42;
      ctx.lineTo(x, y);
    }
    ctx.lineTo(w + 10, h);
    ctx.closePath();
    ctx.fillStyle = color;
    ctx.fill();
  }

  function redFlag(ctx, x, y, s, wave) {
    ctx.save();
    ctx.translate(x, y);
    ctx.strokeStyle = "rgba(216,201,180,.75)";
    ctx.lineWidth = Math.max(1, s * 0.05);
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(0, -s * 2.2);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(0, -s * 2.2);
    var i;
    for (i = 0; i <= 10; i++) {
      var u = i / 10;
      ctx.lineTo(u * s * 1.5, -s * 2.2 + SIN(u * 4 + wave) * s * 0.16 + u * s * 0.06);
    }
    for (i = 10; i >= 0; i--) {
      var u2 = i / 10;
      ctx.lineTo(u2 * s * 1.5, -s * 1.5 + SIN(u2 * 4 + wave) * s * 0.16 + u2 * s * 0.06);
    }
    ctx.closePath();
    ctx.fillStyle = "rgba(179,32,44,.94)";
    ctx.fill();
    ctx.beginPath();
    for (var k = 0; k < 10; k++) {
      var ang = -Math.PI / 2 + k * Math.PI / 5;
      var rad = (k % 2 === 0) ? s * 0.2 : s * 0.085;
      var px = s * 0.55 + COS(ang) * rad;
      var py = -s * 1.9 + SIN(ang) * rad;
      if (k === 0) { ctx.moveTo(px, py); } else { ctx.lineTo(px, py); }
    }
    ctx.closePath();
    ctx.fillStyle = "rgba(232,183,97,.95)";
    ctx.fill();
    ctx.restore();
  }

  function soldier(ctx, x, y, s, dir) {
    ctx.save();
    ctx.translate(x, y);
    ctx.scale(dir || 1, 1);
    ctx.fillStyle = "rgba(16,14,13,.9)";
    ctx.beginPath();
    ctx.arc(0, -s * 0.86, s * 0.11, 0, TAU);
    ctx.fill();
    ctx.fillRect(-s * 0.035, -s * 0.78, s * 0.07, s * 0.05);
    ctx.beginPath();
    ctx.moveTo(-s * 0.11, -s * 0.74);
    ctx.lineTo(s * 0.11, -s * 0.74);
    ctx.lineTo(s * 0.09, -s * 0.3);
    ctx.lineTo(-s * 0.09, -s * 0.3);
    ctx.closePath();
    ctx.fill();
    ctx.strokeStyle = "rgba(16,14,13,.9)";
    ctx.lineWidth = s * 0.07;
    ctx.beginPath();
    ctx.moveTo(-s * 0.05, -s * 0.3);
    ctx.lineTo(-s * 0.08, 0);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(s * 0.05, -s * 0.3);
    ctx.lineTo(s * 0.1, 0);
    ctx.stroke();
    ctx.strokeStyle = "rgba(58,42,28,.9)";
    ctx.lineWidth = Math.max(1, s * 0.035);
    ctx.beginPath();
    ctx.moveTo(s * 0.04, -s * 0.62);
    ctx.lineTo(s * 0.34, -s * 0.94);
    ctx.stroke();
    ctx.restore();
  }

  RedScene.prototype.draw = function (ctx, w, h, now) {
    var n = this.chapters.length;
    var t = this.t;
    var stageLen = this.duration / n;
    var idx = clamp(Math.floor(t / stageLen), 0, n - 1);
    var local = (t - idx * stageLen) / stageLen;
    var box = visualBox(w, h);
    var S = w >= 900 ? Math.min(w, h) : Math.min(w, (box.bottom - box.top) * 1.9);
    var baseY = w >= 900 ? h * 0.74 : box.bottom;
    if (w >= 900) {
      ctx.save();
    } else {
      // 窄屏：把历史现场裁在上半屏，避免压住解说文字
      ctx.save();
      ctx.beginPath();
      ctx.rect(0, 0, w, box.bottom + 6);
      ctx.clip();
    }
    var skies = [
      ["#1B1A22", "#4A2230", "#8A3A2C"],
      ["#12151E", "#3B1C24", "#7C3128"],
      ["#0E1622", "#26364D", "#6B4A3C"],
      ["#0C1118", "#1E2836", "#573F35"]
    ];
    var sk = skies[idx];
    var sky = ctx.createLinearGradient(0, 0, 0, baseY + S * 0.1);
    sky.addColorStop(0, sk[0]);
    sky.addColorStop(0.55, sk[1]);
    sky.addColorStop(1, sk[2]);
    ctx.fillStyle = sky;
    ctx.fillRect(0, 0, w, h);

    var skyTop = w >= 900 ? 0 : box.top;
    var skyH = w >= 900 ? h : (box.bottom - box.top);
    for (var s0 = 0; s0 < this.stars.length; s0++) {
      var st = this.stars[s0];
      var tw = 0.35 + 0.65 * Math.abs(SIN(now * 0.0012 + s0));
      ctx.fillStyle = "rgba(246,241,231," + (0.1 + 0.2 * tw) + ")";
      ctx.beginPath();
      ctx.arc(st[0] * w, skyTop + st[1] * skyH, st[2], 0, TAU);
      ctx.fill();
    }

    ridges(ctx, w, h, baseY - S * 0.18, "rgba(28,32,42,.85)", S * 0.05, 0.6);
    ridges(ctx, w, h, baseY - S * 0.085, "rgba(20,24,30,.92)", S * 0.075, 2.1);
    ridges(ctx, w, h, baseY + S * 0.012, "rgba(12,14,18,.98)", S * 0.045, 4.3);

    ctx.fillStyle = "rgba(8,10,12,.95)";
    for (var tt = 0; tt < this.trees.length; tt++) {
      var tr = this.trees[tt];
      var tx = tr[0] * w;
      var ty = w >= 900 ? tr[1] * h + S * 0.03 : baseY - (1 - tr[1]) * (box.bottom - box.top) * 0.9 + S * 0.05;
      var ts = tr[2] * (w >= 900 ? S * 0.05 : S * 0.045);
      ctx.beginPath();
      ctx.moveTo(tx - ts * 0.4, ty);
      ctx.lineTo(tx, ty - ts * 2.2);
      ctx.lineTo(tx + ts * 0.4, ty);
      ctx.closePath();
      ctx.fill();
    }

    var fg = ctx.createLinearGradient(0, baseY, 0, h);
    fg.addColorStop(0, "rgba(10,10,10,0)");
    fg.addColorStop(1, "rgba(6,6,6,.6)");
    ctx.fillStyle = fg;
    ctx.fillRect(0, baseY, w, h - baseY);

    var cx = w * 0.5;

    /* 一 · 东固会师 */
    if (idx === 0) {
      var meet = ease(clamp(local * 1.25, 0, 1));
      var y0 = baseY - S * 0.02;
      var leftX = w >= 900 ? lerp(w * 0.46, w * 0.56, meet) : lerp(w * 0.16, w * 0.36, meet);
      var rightX = w >= 900 ? lerp(w * 0.92, w * 0.78, meet) : lerp(w * 0.84, w * 0.64, meet);
      soldier(ctx, leftX - S * 0.16, y0, S * 0.062, 1);
      soldier(ctx, leftX - S * 0.08, y0, S * 0.07, 1);
      soldier(ctx, leftX, y0, S * 0.078, 1);
      soldier(ctx, rightX + S * 0.16, y0, S * 0.062, -1);
      soldier(ctx, rightX + S * 0.08, y0, S * 0.07, -1);
      soldier(ctx, rightX, y0, S * 0.078, -1);
      var flagX = w >= 900 ? w * 0.60 : cx - S * 0.01;
      redFlag(ctx, flagX, y0 + S * 0.005, S * 0.05 * (0.5 + meet * 0.9), now * 0.004);
      redFlag(ctx, flagX + (w >= 900 ? w * 0.1 : S * 0.1), y0 + S * 0.005, S * 0.038 * (0.4 + meet * 0.9), now * 0.005);
      var gx = w >= 900 ? w * 0.66 : cx;
      var gl = ctx.createRadialGradient(gx, y0 - S * 0.16, 0, gx, y0 - S * 0.16, Math.max(2, S * 0.36 * (0.4 + meet)));
      gl.addColorStop(0, "rgba(232,183,97," + (0.3 * meet) + ")");
      gl.addColorStop(1, "rgba(232,183,97,0)");
      ctx.fillStyle = gl;
      ctx.fillRect(0, 0, w, h);
    }

    /* 二 · 龙冈大捷：山谷「布袋」合围 */
    if (idx === 1) {
      var close = ease(clamp(local * 1.1, 0, 1));
      var y1 = baseY - S * 0.03;
      var xL = w >= 900 ? w * 0.44 : w * 0.16;
      var xR = w >= 900 ? w * 0.90 : w * 0.86;
      var xC = (xL + xR) / 2;
      ctx.beginPath();
      ctx.moveTo(xL, y1);
      ctx.quadraticCurveTo(xC, y1 - S * 0.3, xR, y1);
      ctx.strokeStyle = "rgba(212,162,76," + (0.24 + 0.3 * close) + ")";
      ctx.lineWidth = 2;
      ctx.setLineDash([10, 8]);
      ctx.stroke();
      ctx.setLineDash([]);
      for (var arm = 0; arm < 2; arm++) {
        var sx = arm === 0 ? xL : xR;
        var dir = arm === 0 ? 1 : -1;
        var ex = sx + dir * (xR - xL) * 0.16 * close;
        var ey = y1 - S * (0.015 + 0.07 * close);
        ctx.strokeStyle = "rgba(217,79,43,.92)";
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(sx, y1 - S * 0.01);
        ctx.lineTo(ex, ey);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(ex, ey);
        ctx.lineTo(ex - dir * S * 0.05, ey - S * 0.022);
        ctx.lineTo(ex - dir * S * 0.034, ey + S * 0.036);
        ctx.closePath();
        ctx.fillStyle = "rgba(217,79,43,.92)";
        ctx.fill();
        soldier(ctx, sx, y1, S * 0.07, dir);
        soldier(ctx, sx - dir * S * 0.09, y1, S * 0.062, dir);
      }
      ctx.fillStyle = "rgba(160,160,172,.62)";
      for (var en = 0; en < 10; en++) {
        var ang = en * 0.7 + now * 0.0004;
        var rr2 = S * 0.05 + (en % 3) * S * 0.02;
        ctx.beginPath();
        ctx.arc(xC + COS(ang) * rr2 * 1.7, y1 - S * 0.07 + SIN(ang) * rr2 * 0.7, 2.4, 0, TAU);
        ctx.fill();
      }
      for (var fl = 0; fl < 5; fl++) {
        var fa = 0.12 + 0.16 * Math.abs(SIN(now * 0.004 + fl * 1.7));
        var fx = xC + (fl - 2) * S * 0.09;
        var fy = y1 - S * 0.1 - (fl % 2) * S * 0.03;
        var fgr = ctx.createRadialGradient(fx, fy, 0, fx, fy, S * 0.06);
        fgr.addColorStop(0, "rgba(255,176,84," + fa + ")");
        fgr.addColorStop(1, "rgba(255,120,40,0)");
        ctx.fillStyle = fgr;
        ctx.beginPath();
        ctx.arc(fx, fy, S * 0.06, 0, TAU);
        ctx.fill();
      }
    }

    /* 三 · 白云山首战 */
    if (idx === 2) {
      var sweep = ease(clamp(local * 1.15, 0, 1));
      var hillY = baseY - S * 0.3;
      ctx.beginPath();
      ctx.moveTo(w * 0.3, baseY + S * 0.05);
      ctx.quadraticCurveTo(w * 0.7, hillY - S * 0.12, w * 1.02, baseY + S * 0.03);
      ctx.lineTo(w * 1.02, h);
      ctx.lineTo(w * 0.3, h);
      ctx.closePath();
      ctx.fillStyle = "rgba(16,20,24,.96)";
      ctx.fill();
      var hx = w * 0.46, hy = baseY - S * 0.05;
      ctx.fillStyle = "rgba(34,28,22,.96)";
      ctx.fillRect(hx - S * 0.055, hy - S * 0.07, S * 0.11, S * 0.07);
      ctx.beginPath();
      ctx.moveTo(hx - S * 0.078, hy - S * 0.07);
      ctx.lineTo(hx, hy - S * 0.14);
      ctx.lineTo(hx + S * 0.078, hy - S * 0.07);
      ctx.closePath();
      ctx.fill();
      ctx.fillStyle = "rgba(232,183,97,.55)";
      ctx.fillRect(hx - S * 0.016, hy - S * 0.05, S * 0.032, S * 0.03);
      for (var a3 = 0; a3 < 6; a3++) {
        var t0 = clamp(sweep * 1.4 - a3 * 0.08, 0, 1);
        if (t0 <= 0) { continue; }
        var sx3 = w * (0.7 + a3 * 0.045), sy3 = hillY + S * 0.05 + a3 * S * 0.012;
        var ex3 = lerp(sx3, w * 0.46, ease(t0)), ey3 = lerp(sy3, baseY + S * 0.02, ease(t0));
        ctx.strokeStyle = "rgba(217,79,43," + (0.55 * (1 - t0 * 0.3)) + ")";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(sx3, sy3);
        ctx.lineTo(ex3, ey3);
        ctx.stroke();
      }
      redFlag(ctx, w * 0.54, baseY - S * 0.01, S * 0.038, now * 0.004);
      // 白云
      ctx.fillStyle = "rgba(226,232,238,.1)";
      for (var cl = 0; cl < 4; cl++) {
        var clx = (cl * 0.27 + 0.1) * w + SIN(now * 0.0004 + cl) * 12;
        var cly = h * 0.24 + cl * S * 0.03;
        ctx.beginPath();
        ctx.ellipse(clx, cly, S * 0.11, S * 0.035, 0, 0, TAU);
        ctx.fill();
      }
    }

    /* 四 · 六渡坳 */
    if (idx === 3) {
      for (var p = 0; p < 3; p++) {
        var px3 = ((local * 0.55 + p * 0.33) % 1) * (w * 1.25) - w * 0.12;
        var py3 = h * 0.16 + p * S * 0.05 + SIN(now * 0.002 + p) * 4;
        ctx.save();
        ctx.translate(px3, py3);
        ctx.fillStyle = "rgba(158,164,176,.6)";
        ctx.beginPath();
        ctx.moveTo(-S * 0.05, 0);
        ctx.lineTo(0, -S * 0.02);
        ctx.lineTo(S * 0.05, 0);
        ctx.lineTo(0, S * 0.012);
        ctx.closePath();
        ctx.fill();
        ctx.fillRect(-S * 0.055, -S * 0.005, S * 0.11, S * 0.009);
        ctx.restore();
      }
      ctx.strokeStyle = "rgba(255,196,120,.55)";
      ctx.lineWidth = 1.2;
      for (var bu = 0; bu < 3; bu++) {
        var bx = w * (0.52 + bu * 0.05), by = h * 0.22 + bu * S * 0.03;
        ctx.beginPath();
        ctx.moveTo(bx, by);
        ctx.lineTo(bx + S * 0.02, by + S * 0.17);
        ctx.stroke();
      }
      var mx = w * 0.62, mbase = baseY + S * 0.02;
      ctx.fillStyle = "rgba(198,190,176,.94)";
      ctx.beginPath();
      ctx.moveTo(mx - S * 0.08, mbase);
      ctx.lineTo(mx - S * 0.052, mbase - S * 0.36);
      ctx.lineTo(mx, mbase - S * 0.42);
      ctx.lineTo(mx + S * 0.052, mbase - S * 0.36);
      ctx.lineTo(mx + S * 0.08, mbase);
      ctx.closePath();
      ctx.fill();
      ctx.fillStyle = "rgba(122,20,32,.85)";
      ctx.font = "600 " + Math.round(S * 0.03) + "px " + FONT_KAI;
      ctx.textAlign = "center";
      ctx.fillText("黄公略", mx, mbase - S * 0.19);
      ctx.fillStyle = "rgba(246,241,231,.6)";
      ctx.font = "11px " + FONT_SANS;
      ctx.fillText("1901 - 1931", mx, mbase - S * 0.155);
      ctx.fillStyle = "rgba(212,162,76,.9)";
      for (var flw = 0; flw < 5; flw++) {
        ctx.beginPath();
        ctx.arc(mx - S * 0.045 + flw * S * 0.022, mbase - S * 0.008, S * 0.007, 0, TAU);
        ctx.fill();
      }
    }

    if (w < 900) {
      // 渐隐到黑，接住下方解说区
      var fade = ctx.createLinearGradient(0, box.bottom - S * 0.26, 0, box.bottom + S * 0.1);
      fade.addColorStop(0, "rgba(8,7,10,0)");
      fade.addColorStop(0.62, "rgba(8,7,10,.72)");
      fade.addColorStop(1, "rgba(8,7,10,1)");
      ctx.fillStyle = fade;
      ctx.fillRect(0, box.bottom - S * 0.26, w, S * 0.36);
    }
    ctx.restore();

    ctx.save();
    ctx.globalAlpha = 0.14;
    ctx.fillStyle = "rgba(232,183,97,1)";
    ctx.font = "600 " + Math.round(S * 0.12) + "px " + FONT_KAI;
    if (w >= 900) {
      ctx.textAlign = "left";
      ctx.textBaseline = "top";
      ctx.fillText(["1929", "1930", "1931", "1931"][idx], w * 0.06, h * 0.2);
    } else {
      ctx.textAlign = "right";
      ctx.textBaseline = "top";
      ctx.fillText(["1929", "1930", "1931", "1931"][idx], w - S * 0.04, box.top + S * 0.06);
    }
    ctx.restore();

    chapterRail(ctx, w, h, this.chapters, idx);
  };
  /* ================= 场景三：畲族凤凰图腾 ================= */
  function PhoenixScene(data) {
    this.id = "phoenix";
    this.data = data;
    this.name = data.name;
    this.en = data.en;
    this.duration = data.duration;
    this.chapters = data.chapters;
    this.t = 0;
    this.palettes = [
      { wing: "#D94F2B", wingDeep: "#7A1420", tip: "#E8B761", body: "#E8325A", tail: "#E8B761", tail2: "#1E3A5F" },
      { wing: "#C8443C", wingDeep: "#8C2030", tip: "#F0C978", body: "#E8506A", tail: "#F0C978", tail2: "#23406B" },
      { wing: "#9E3B34", wingDeep: "#5E1A24", tip: "#D4A24C", body: "#C24A50", tail: "#D4A24C", tail2: "#1B2C44" }
    ];
  }
  PhoenixScene.prototype.seek = function (t) { this.t = clamp(t, 0, this.duration); };

  /* 单侧翼：以肩为轴，羽片带锯齿后缘 + 覆羽分层，避免读成花瓣 */
  function wingPath(ctx, s, side, flapAmt) {
    ctx.save();
    ctx.translate(side * s * 0.05, -s * 0.02);
    ctx.rotate(side * flapAmt);
    var L = s * 1.0;
    // 主翼形
    ctx.beginPath();
    ctx.moveTo(0, s * 0.1);
    ctx.quadraticCurveTo(side * L * 0.18, -s * 0.30, side * L * 0.62, -s * 0.34);
    ctx.quadraticCurveTo(side * L * 0.9, -s * 0.36, side * L * 1.0, -s * 0.12);
    // 后缘：三道羽尖
    ctx.lineTo(side * L * 0.82, -s * 0.02);
    ctx.lineTo(side * L * 0.88, s * 0.06);
    ctx.lineTo(side * L * 0.6, s * 0.08);
    ctx.lineTo(side * L * 0.63, s * 0.16);
    ctx.lineTo(side * L * 0.33, s * 0.12);
    ctx.lineTo(side * L * 0.34, s * 0.2);
    ctx.quadraticCurveTo(side * L * 0.12, s * 0.2, 0, s * 0.1);
    ctx.closePath();
    ctx.restore();
  }

  function drawPhoenix(ctx, cx, cy, s, flap, pal, spread) {
    spread = spread || 1;
    var wf = SIN(flap);
    var i, f, side;
    /* 尾羽：三组长羽，自尾根向下散开（实心羽片，非线条） */
    for (i = 0; i < 5; i++) {
      var k2 = (i - 2) / 2;                 // -1 .. 1
      var baseX = cx + k2 * s * 0.07;
      var tipX2 = cx + k2 * s * 0.72;
      var tipY2 = cy + s * (0.9 - Math.abs(k2) * 0.2) * spread;
      var halfW = s * (0.062 - Math.abs(k2) * 0.014);
      ctx.beginPath();
      ctx.moveTo(baseX - halfW, cy + s * 0.14);
      ctx.bezierCurveTo(
        baseX - halfW * 1.2, cy + s * 0.45 * spread,
        tipX2 - halfW * 0.35, cy + s * 0.72 * spread,
        tipX2, tipY2
      );
      ctx.bezierCurveTo(
        tipX2 + halfW * 0.35, cy + s * 0.72 * spread,
        baseX + halfW * 1.2, cy + s * 0.45 * spread,
        baseX + halfW, cy + s * 0.14
      );
      ctx.closePath();
      ctx.fillStyle = (i % 2 === 0) ? pal.tail : pal.tail2;
      ctx.fill();
      ctx.strokeStyle = "rgba(255,244,226,.18)";
      ctx.lineWidth = Math.max(0.8, s * 0.005);
      ctx.stroke();
    }
    /* 双翼 */
    for (side = -1; side <= 1; side += 2) {
      var amp = -side * (0.30 + wf * 0.34);
      ctx.save();
      ctx.translate(cx, cy);
      ctx.save();
      ctx.translate(side * s * 0.08, -s * 0.08);
      ctx.rotate(amp);
      var L = s * 1.0;
      var g = ctx.createLinearGradient(0, 0, side * L, -s * 0.2);
      g.addColorStop(0, pal.wingDeep);
      g.addColorStop(0.42, pal.wing);
      g.addColorStop(1, pal.tip);
      ctx.beginPath();
      ctx.moveTo(0, s * 0.1);
      ctx.quadraticCurveTo(side * L * 0.18, -s * 0.30, side * L * 0.62, -s * 0.34);
      ctx.quadraticCurveTo(side * L * 0.9, -s * 0.36, side * L * 1.0, -s * 0.12);
      ctx.lineTo(side * L * 0.82, -s * 0.02);
      ctx.lineTo(side * L * 0.88, s * 0.06);
      ctx.lineTo(side * L * 0.6, s * 0.08);
      ctx.lineTo(side * L * 0.63, s * 0.16);
      ctx.lineTo(side * L * 0.33, s * 0.12);
      ctx.lineTo(side * L * 0.34, s * 0.2);
      ctx.quadraticCurveTo(side * L * 0.12, s * 0.2, 0, s * 0.1);
      ctx.closePath();
      ctx.fillStyle = g;
      ctx.fill();
      // 覆羽分层线
      ctx.strokeStyle = "rgba(255,244,226,.26)";
      ctx.lineWidth = Math.max(0.8, s * 0.006);
      for (f = 1; f <= 4; f++) {
        ctx.beginPath();
        ctx.moveTo(side * L * 0.1 * f, s * 0.06);
        ctx.quadraticCurveTo(side * L * (0.16 + 0.16 * f), -s * 0.14, side * L * (0.26 + 0.19 * f), -s * 0.06);
        ctx.stroke();
      }
      // 羽尖暗边
      ctx.beginPath();
      ctx.moveTo(side * L * 0.6, s * 0.08);
      ctx.lineTo(side * L * 0.63, s * 0.16);
      ctx.lineTo(side * L * 0.33, s * 0.12);
      ctx.strokeStyle = "rgba(60,16,22,.35)";
      ctx.lineWidth = Math.max(1, s * 0.012);
      ctx.stroke();
      ctx.restore();
      ctx.restore();
    }
    /* 身体 */
    var bg = ctx.createLinearGradient(cx, cy - s * 0.3, cx, cy + s * 0.35);
    bg.addColorStop(0, pal.body);
    bg.addColorStop(1, pal.wingDeep);
    ctx.beginPath();
    ctx.moveTo(cx, cy - s * 0.34);
    ctx.quadraticCurveTo(cx + s * 0.19, cy - s * 0.12, cx + s * 0.11, cy + s * 0.24);
    ctx.quadraticCurveTo(cx, cy + s * 0.36, cx - s * 0.11, cy + s * 0.24);
    ctx.quadraticCurveTo(cx - s * 0.19, cy - s * 0.12, cx, cy - s * 0.34);
    ctx.closePath();
    ctx.fillStyle = bg;
    ctx.fill();
    /* 颈与头 */
    ctx.beginPath();
    ctx.moveTo(cx - s * 0.055, cy - s * 0.3);
    ctx.quadraticCurveTo(cx - s * 0.02, cy - s * 0.52, cx + s * 0.045, cy - s * 0.6);
    ctx.quadraticCurveTo(cx + s * 0.145, cy - s * 0.62, cx + s * 0.1, cy - s * 0.5);
    ctx.quadraticCurveTo(cx + s * 0.08, cy - s * 0.38, cx + s * 0.082, cy - s * 0.3);
    ctx.closePath();
    ctx.fillStyle = pal.wing;
    ctx.fill();
    /* 喙 */
    ctx.beginPath();
    ctx.moveTo(cx + s * 0.1, cy - s * 0.57);
    ctx.lineTo(cx + s * 0.2, cy - s * 0.54);
    ctx.lineTo(cx + s * 0.1, cy - s * 0.51);
    ctx.closePath();
    ctx.fillStyle = pal.tip;
    ctx.fill();
    /* 凤冠 */
    for (var c = 0; c < 3; c++) {
      ctx.beginPath();
      ctx.moveTo(cx + s * (0.06 + c * 0.025), cy - s * 0.615);
      ctx.quadraticCurveTo(
        cx + s * (0.02 + c * 0.05), cy - s * (0.76 + c * 0.03),
        cx + s * (0.16 + c * 0.04), cy - s * (0.74 + c * 0.02)
      );
      ctx.strokeStyle = pal.tip;
      ctx.lineWidth = s * 0.02;
      ctx.stroke();
    }
    /* 眼 */
    ctx.beginPath();
    ctx.arc(cx + s * 0.088, cy - s * 0.565, s * 0.012, 0, TAU);
    ctx.fillStyle = "rgba(11,9,8,.88)";
    ctx.fill();
  }

  PhoenixScene.prototype.draw = function (ctx, w, h, now) {
    var S = Math.min(w, h), box = visualBox(w, h);
    var t = this.t, n = this.chapters.length;
    var stageLen = this.duration / n;
    var idx = clamp(Math.floor(t / stageLen), 0, n - 1);
    var local = (t - idx * stageLen) / stageLen;
    var cx = box.cx, cy = box.cy;
    var fs = w >= 900 ? Math.min(box.s * 0.5, S * 0.42) : box.s * 0.3;

    var bg = ctx.createRadialGradient(cx, cy, S * 0.05, cx, cy, S * 0.9);
    bg.addColorStop(0, "rgba(96,26,34,.52)");
    bg.addColorStop(0.55, "rgba(30,24,24,.26)");
    bg.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, w, h);

    var pal = this.palettes[clamp(idx, 0, 2)];
    var appear = idx === 0 ? ease(clamp(local * 1.6, 0, 1)) : 1;
    var fadeOut = idx === 3 ? clamp((local - 0.55) / 0.45, 0, 1) : 0;
    var alpha = (idx === 3 ? 1 - fadeOut * 0.5 : 1) * appear;

    // 外环织带纹
    ctx.save();
    ctx.translate(cx, cy);
    for (var ring = 0; ring < 2; ring++) {
      var rr = fs * (1.42 + ring * 0.2);
      ctx.beginPath();
      ctx.arc(0, 0, rr, 0, TAU);
      ctx.strokeStyle = "rgba(212,162,76," + (ring ? 0.16 : 0.32) + ")";
      ctx.lineWidth = ring ? 1 : 1.6;
      if (ring) { ctx.setLineDash([14, 11]); }
      ctx.stroke();
      ctx.setLineDash([]);
    }
    var rot = now * 0.00018;
    for (var m = 0; m < 28; m++) {
      var ang = rot + m * TAU / 28;
      var r1 = fs * 1.66, r2 = fs * 1.78;
      ctx.beginPath();
      ctx.moveTo(COS(ang) * r1, SIN(ang) * r1);
      ctx.lineTo(COS(ang) * r2, SIN(ang) * r2);
      ctx.strokeStyle = "rgba(212,162,76,.2)";
      ctx.lineWidth = 1;
      ctx.stroke();
    }
    ctx.restore();

    // 金羽粒子
    ctx.save();
    ctx.globalAlpha = 0.95 * alpha;
    for (var p = 0; p < 96; p++) {
      var a0 = p * 2.399 + now * 0.00035 * (1 + (p % 5) * 0.16);
      var rBase = fs * (1.0 + (p % 17) * 0.052);
      var gather = idx === 0 ? (1 - appear * appear) * S * 0.2 : 0;
      var px = cx + COS(a0) * (rBase + gather);
      var py = cy + SIN(a0) * (rBase + gather) * 0.92;
      var twinkle = 0.35 + 0.65 * Math.abs(SIN(now * 0.0016 + p));
      ctx.fillStyle = "rgba(232,183,97," + (0.4 * twinkle * alpha) + ")";
      ctx.beginPath();
      ctx.arc(px, py, 1.1 + (p % 3) * 0.5, 0, TAU);
      ctx.fill();
    }
    ctx.restore();

    var fly = idx >= 2;
    var flap = now * (fly ? 0.006 : 0.0028);
    var driftX = fly ? SIN(now * 0.00075) * fs * 0.22 : 0;
    var driftY = fly ? COS(now * 0.0011) * fs * 0.08 : 0;
    var pulse = 1 + (fly ? 0.035 : 0.014) * SIN(now * 0.0018);
    ctx.save();
    ctx.globalAlpha = alpha;
    drawPhoenix(ctx, cx + driftX, cy + driftY, fs * pulse, flap, pal, 1 + (fly ? 0.07 * SIN(now * 0.0012) : 0));
    ctx.restore();

    // 三式凤凰装色卡（第二 / 三章）
    if (idx >= 1 && idx <= 2) {
      var showCost = 0.55 + 0.45 * ease(clamp(local * 2, 0, 1));
      var names = ["大凤凰装", "小凤凰装", "老凤凰装"];
      var pcols = ["#B3202C", "#D94F2B", "#8C6A3A"];
      var narrow = w < 900;
      var chipY = w >= 900 ? Math.min(h - 120, box.cy + fs * 1.16) : box.bottom - 34;
      var chipGap = w >= 900 ? Math.min(120, S * 0.19) : w * 0.3;
      ctx.save();
      ctx.globalAlpha = showCost;
      for (var cc = 0; cc < 3; cc++) {
        var bx = box.cx + (cc - 1) * chipGap;
        var active = cc === (idx === 1 ? 0 : 2);
        ctx.beginPath();
        ctx.arc(bx, chipY, S * 0.012, 0, TAU);
        ctx.fillStyle = pcols[cc];
        ctx.fill();
        if (active) {
          ctx.beginPath();
          ctx.arc(bx, chipY, S * 0.023, 0, TAU);
          ctx.strokeStyle = "rgba(232,183,97,.95)";
          ctx.lineWidth = 1.4;
          ctx.stroke();
        }
        ctx.font = (active ? "600 11.5px " : "11px ") + FONT_SANS;
        ctx.textAlign = "center";
        ctx.fillStyle = active ? "rgba(242,233,220,.95)" : "rgba(242,233,220,.55)";
        // 窄屏把标签放在圆点上方，避免压住下一段标题
        ctx.fillText(names[cc], bx, chipY + (narrow ? -12 : 18));
      }
      ctx.restore();
    }

    if (idx === 3 && local > 0.5) {
      ctx.save();
      ctx.globalAlpha = clamp((local - 0.5) / 0.4, 0, 1);
      sealMark(ctx, cx + fs * 1.1, cy - fs * 0.9, fs * 0.22, "凤", RED, 0.1);
      ctx.restore();
    }

    chapterRail(ctx, w, h, this.chapters, idx);
  };

  /* ================= 工厂与导出 ================= */
  function create(id, data) {
    if (id === "craft") { return new CraftScene(data); }
    if (id === "red") { return new RedScene(data); }
    if (id === "phoenix") { return new PhoenixScene(data); }
    return null;
  }

  global.AR_SCENES = {
    create: create,
    CraftScene: CraftScene,
    RedScene: RedScene,
    PhoenixScene: PhoenixScene,
    drawPhoenix: drawPhoenix,
    utils: { clamp: clamp, ease: ease, lerp: lerp, rgba: rgba, sealMark: sealMark, visualBox: visualBox }
  };
})(window);