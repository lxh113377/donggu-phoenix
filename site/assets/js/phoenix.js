/* phoenix.js — 畲族凤凰粒子引擎
 * 从 phoenix-totem.svg 采样轮廓与配色，驱动 2000+ 粒子完成「图腾呼吸 → 碎裂 → 展翅飞舞 → 归位」。
 * 无第三方依赖；devicePixelRatio 适配；prefers-reduced-motion 与低端机自动降级。
 */
(function (global) {
  'use strict';

  var SVG_URL = 'assets/img/phoenix-particle.svg';   // 纯剪影，便于像素采样
  var SAMPLE = 460;              // 采样画布边长
  var RING_CUT = 0.5;            // 归一化半径外直接丢弃

  function Phoenix(canvas, opts) {
    opts = opts || {};
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d', { alpha: true });
    this.dpr = Math.min(global.devicePixelRatio || 1, 2);
    this.reduced = global.matchMedia && global.matchMedia('(prefers-reduced-motion: reduce)').matches;
    this.state = 'loading';
    this.t = 0;
    this.fps = 0;
    this._frames = 0; this._fpsT = 0;
    this.onReady = opts.onReady || function () {};
    this.isMobile = global.innerWidth < 900;
    this.anchor = opts.anchor || null;
    this.maxParticles = opts.maxParticles || (this.isMobile ? 1500 : 2600);
    this.particles = [];
    this._raf = null;
    this._last = 0;
    this._summonT = -1;
    this._resize = this._resize.bind(this);
    this._tick = this._tick.bind(this);
    this._visible = true;
  }

  Phoenix.prototype.load = function () {
    var self = this;
    return new Promise(function (resolve) {
      var img = new Image();
      img.crossOrigin = 'anonymous';
      img.onload = function () {
        try { self._sample(img); } catch (e) { self._fallback(); }
        resolve(self);
      };
      img.onerror = function () { self._fallback(); resolve(self); };
      img.src = SVG_URL;
    });
  };

  Phoenix.prototype._fallback = function () {
    // SVG 采样失败 → 用解析式凤凰轮廓兜底
    var pts = [], cols = [];
    for (var i = 0; i < this.maxParticles; i++) {
      var a = Math.random() * Math.PI * 2;
      var rr = Math.pow(Math.random(), 0.55) * 0.4;
      var x = 0.5 + Math.cos(a) * rr * 0.9;
      var y = 0.5 + Math.sin(a) * rr;
      pts.push(x, y);
      cols.push(211, 79, 43);
    }
    this._build(pts, cols, 1);
  };

  /* 从剪影位图采样目标点，并按位置重新着色为畲族凤凰装配色 */
  Phoenix.prototype._sample = function (img) {
    var c = document.createElement('canvas');
    c.width = SAMPLE; c.height = SAMPLE;
    var g = c.getContext('2d', { willReadFrequently: true });
    g.clearRect(0, 0, SAMPLE, SAMPLE);
    g.drawImage(img, 0, 0, SAMPLE, SAMPLE);
    var data = g.getImageData(0, 0, SAMPLE, SAMPLE).data;

    var cand = [];
    for (var y = 0; y < SAMPLE; y += 1) {
      for (var x = 0; x < SAMPLE; x += 1) {
        var i = (y * SAMPLE + x) * 4;
        if (data[i + 3] < 60) continue;
        var nx = x / SAMPLE, ny = y / SAMPLE;
        if (Math.hypot(nx - 0.5, ny - 0.5) > RING_CUT) continue;
        cand.push(nx, ny);
      }
    }
    var n = cand.length / 2;
    if (n < 300) { this._fallback(); return; }
    var step = Math.max(1, Math.floor(n / this.maxParticles));
    var pts = [], cols = [];
    for (var k = 0; k < n; k += step) {
      var px = cand[k * 2], py = cand[k * 2 + 1];
      pts.push(px, py);
      var rgb = this._colorAt(px, py);
      cols.push(rgb[0], rgb[1], rgb[2]);
    }
    this._build(pts, cols, step);
  };

  /* 位置着色：翼尖金、翼中桃红、翼根深红、身体朱红、尾羽金→蓝渐变 */
  Phoenix.prototype._colorAt = function (x, y) {
    var dx = x - 0.5, dy = y - 0.5;
    var ax = Math.abs(dx) * 2;          // 0 中轴 -> 1 边缘
    var ay = dy * 2;                    // -1 上 -> 1 下
    var r, g, b;
    if (ay > 0.32) {
      // 尾羽：金 -> 深蓝
      var t = Math.min(1, (ay - 0.32) / 0.62);
      r = Math.round(232 + (30 - 232) * t);
      g = Math.round(183 + (58 - 183) * t);
      b = Math.round(97 + (95 - 97) * t);
    } else if (ax > 0.28) {
      // 翼：根深红 -> 中桃红 -> 尖金
      var u = Math.min(1, (ax - 0.28) / 0.62);
      if (u < 0.5) {
        var s = u / 0.5;
        r = Math.round(122 + (217 - 122) * s);
        g = Math.round(20 + (79 - 20) * s);
        b = Math.round(32 + (43 - 32) * s);
      } else {
        var s2 = (u - 0.5) / 0.5;
        r = Math.round(217 + (232 - 217) * s2);
        g = Math.round(79 + (183 - 79) * s2);
        b = Math.round(43 + (97 - 43) * s2);
      }
    } else {
      // 身体与冠：朱红高光
      var v = Math.min(1, Math.max(0, (ay + 0.5) / 0.9));
      r = Math.round(232 - 40 * v);
      g = Math.round(103 - 40 * v);
      b = Math.round(86 - 20 * v);
    }
    return [r, g, b];
  };

  Phoenix.prototype._build = function (pts, cols, step) {
    var count = pts.length / 2;
    var arr = new Array(count);
    for (var i = 0; i < count; i++) {
      var tx = pts[i * 2], ty = pts[i * 2 + 1];
      arr[i] = {
        tx: tx, ty: ty,
        x: tx + (Math.random() - 0.5) * 1.6,
        y: ty + (Math.random() - 0.5) * 1.6,
        vx: 0, vy: 0,
        r: 28, g: 79, b: 43,
        size: 0.9 + Math.random() * 1.5,
        ph: Math.random() * Math.PI * 2,   // 相位（呼吸/扑翼）
        k: 0.055 + Math.random() * 0.05,   // 弹簧刚度
        damp: 0.86 + Math.random() * 0.05
      };
    }
    if (cols && cols.length === count * 3) {
      var opa = [];
      for (var j = 0; j < count; j++) {
        arr[j].r = cols[j * 3]; arr[j].g = cols[j * 3 + 1]; arr[j].b = cols[j * 3 + 2];
      }
    }
    this.particles = arr;
    this.count = count;
    this.state = 'assemble';
    this.t = 0;
    this._resize();
    this._start();
  };

  Phoenix.prototype._resize = function () {
    var w = this.canvas.clientWidth || global.innerWidth;
    var h = this.canvas.clientHeight || global.innerHeight;
    this.w = w; this.h = h;
    this.canvas.width = Math.round(w * this.dpr);
    this.canvas.height = Math.round(h * this.dpr);
    this.ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    // 默认铺满画布；若提供了 anchor 元素，则以它为圆心（桌面分栏布局）
    this.scale = Math.min(w, h) * 0.92;
    this.ox = w / 2; this.oy = h / 2;

    var a = this.anchor;
    if (a) {
      var cr = this.canvas.getBoundingClientRect();
      var ar = a.getBoundingClientRect();
      if (ar.width > 8 && cr.width > 8) {
        this.ox = ar.left - cr.left + ar.width / 2;
        this.oy = ar.top - cr.top + ar.height / 2;
        this.scale = Math.min(ar.width, ar.height) * 1.02;
      }
    }
    if (this.isMobile && !this.anchor) this.oy = h * 0.42;
  };

  Phoenix.prototype._start = function () {
    if (this.reduced) { this._drawStatic(); this.onReady(this); return; }
    global.addEventListener('resize', this._resize, { passive: true });
    document.addEventListener('visibilitychange', function () {
      this._visible = !document.hidden;
    }.bind(this));
    this._last = performance.now();
    this._raf = requestAnimationFrame(this._tick);
  };

  Phoenix.prototype.summon = function () {
    if (this.state === 'burst' || this.state === 'flight') return;
    this.state = 'burst';
    this.t = 0;
    var ps = this.particles, i;
    for (i = 0; i < ps.length; i++) {
      var p = ps[i];
      var a = Math.atan2(p.y - 0.5, p.x - 0.5) + (Math.random() - 0.5) * 0.9;
      var sp = 0.010 + Math.random() * 0.026;
      p.vx += Math.cos(a) * sp * 22;
      p.vy += Math.sin(a) * sp * 22;
    }
    this._summonT = performance.now();
    if (this.onSummon) this.onSummon();
  };

  Phoenix.prototype.settle = function () {
    this.state = 'settle'; this.t = 0;
  };

  Phoenix.prototype._targets = function (time) {
    // 计算本帧目标点：assemble/idle 为图腾深呼吸；flight 为扑翼飞行
    var st = this.state;
    var ps = this.particles;
    var flap = Math.sin(time * 0.0042);
    var fly = st === 'flight' || st === 'burst';
    var drift = fly ? { x: Math.sin(time * 0.0009) * 0.035, y: Math.sin(time * 0.0013) * 0.022 } : { x: 0, y: 0 };
    var spread = st === 'flight' ? 1.10 : 1.0;
    var out = this._tbuf || (this._tbuf = new Float32Array(ps.length * 2));
    for (var i = 0; i < ps.length; i++) {
      var p = ps[i];
      var tx = p.tx, ty = p.ty;
      if (st !== 'burst') {
        // 扑翼：以身体中轴为轴，按离轴距离做旋转位移
        var dx = tx - 0.5, dy = ty - 0.5;
        var ax = Math.abs(dx);
        var amt = Math.min(1, ax * 5.2) * 0.16 * flap;
        var ny = dy * Math.cos(amt) - dx * Math.sin(amt) * Math.sign(dx || 1) * 0.6;
        ty = 0.5 + ny;
        tx = 0.5 + dx * (1 + 0.05 * flap * Math.min(1, ax * 3));
      }
      // 呼吸 / 抖动
      var jt = st === 'flight' ? 0.0018 : 0.0011;
      tx += Math.sin(time * 0.0016 + p.ph) * jt;
      ty += Math.cos(time * 0.0019 + p.ph * 1.3) * jt;
      out[i * 2] = 0.5 + (tx - 0.5) * spread + drift.x;
      out[i * 2 + 1] = 0.5 + (ty - 0.5) * spread + drift.y;
    }
    return out;
  };

  Phoenix.prototype._tick = function (now) {
    this._raf = requestAnimationFrame(this._tick);
    var dt = Math.min(48, now - this._last);
    this._last = now;
    if (!this._visible || dt <= 0) return;

    this.t += dt;
    this._frames++;
    if (now - this._fpsT > 900) {
      this.fps = Math.round(this._frames * 1000 / (now - this._fpsT));
      this._frames = 0; this._fpsT = now;
      global.__phoenixFps = this.fps;
    }

    // 状态推进
    if (this.state === 'assemble' && this.t > 1400) { this.state = 'idle'; this.t = 0; this.onReady(this); }
    if (this.state === 'burst' && this.t > 520) { this.state = 'flight'; this.t = 0; if (this.onFlight) this.onFlight(); }
    if (this.state === 'settle' && this.t > 1500) { this.state = 'idle'; this.t = 0; }

    var ctx = this.ctx;
    var fade = this.state === 'flight' ? 0.18 : 0.24;
    ctx.globalCompositeOperation = 'destination-out';
    ctx.fillStyle = 'rgba(0,0,0,' + fade + ')';
    ctx.fillRect(0, 0, this.w, this.h);
    ctx.globalCompositeOperation = 'lighter';

    var tg = this._targets(now);
    var ps = this.particles;
    var sc = this.scale, ox = this.ox, oy = this.oy;
    for (var i = 0; i < ps.length; i++) {
      var p = ps[i];
      var tx = tg[i * 2] * sc + ox - sc / 2;
      var ty = tg[i * 2 + 1] * sc + oy - sc / 2;
      var k = p.k * (dt / 16.7);
      p.vx += (tx - p.x) * k;
      p.vy += (ty - p.y) * k;
      p.vx *= Math.pow(p.damp, dt / 16.7);
      p.vy *= Math.pow(p.damp, dt / 16.7);
      p.x += p.vx; p.y += p.vy;
      var sz = p.size * (this.isMobile ? 1.35 : 1.6);
      var tw = 0.72 + 0.28 * Math.sin(now * 0.003 + p.ph);
      ctx.fillStyle = 'rgba(' + p.r + ',' + p.g + ',' + p.b + ',' + (0.46 * tw).toFixed(3) + ')';
      ctx.beginPath();
      ctx.arc(p.x, p.y, sz * 0.62, 0, 6.2832);
      ctx.fill();
    }
    ctx.globalCompositeOperation = 'source-over';
  };

  Phoenix.prototype._drawStatic = function () {
    // 降级：一次性画出静态光点图腾
    this._resize();
    var ctx = this.ctx;
    ctx.clearRect(0, 0, this.w, this.h);
    var sc = this.scale, ox = this.ox - sc / 2, oy = this.oy - sc / 2;
    for (var i = 0; i < this.particles.length; i++) {
      var p = this.particles[i];
      ctx.fillStyle = 'rgba(' + p.r + ',' + p.g + ',' + p.b + ',0.9)';
      var s = p.size * 1.1;
      ctx.fillRect(p.tx * sc + ox, p.ty * sc + oy, s, s);
    }
    this.state = 'idle';
    global.__phoenixFps = 0;
    this.onReady(this);
  };

  Phoenix.prototype.destroy = function () {
    if (this._raf) cancelAnimationFrame(this._raf);
    global.removeEventListener('resize', this._resize);
  };

  global.Phoenix = Phoenix;
})(window);
