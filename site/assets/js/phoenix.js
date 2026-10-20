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
    this._t0 = 0; this._degraded = false;
    this.fps = 0;
    this._frames = 0; this._fpsT = 0;
    this.onReady = opts.onReady || function () {};
    this.isMobile = global.innerWidth < 900;
    this.anchor = opts.anchor || null;
    /* 硬件分档（2026-10-20 轮9 补）：注释一直写着「低端机自动降级」，但此前只有
     * reduced-motion 分支，从未检测过低端设备。实测本机单帧 p95 4.9ms；
     * 低端机单核算力约为本机 1/8，估算 ≈39ms/帧（约 25fps），必然卡顿。
     * 判据用硬件信号（不猜机型）：核数 <= 4 或内存 <= 4GB 视为低端。 */
    var _cores = global.navigator && global.navigator.hardwareConcurrency;
    var _mem = global.navigator && global.navigator.deviceMemory;
    this.lowEnd = !!((_cores && _cores <= 4) || (_mem && _mem <= 4));
    /* I-7 粒子密度按面积自适应（对标 particles.js number.density.value_area）。
     * 旧口径 isMobile ? 1500 : 2600 只有两档，问题在中间地带：
     *   平板（768~900px）拿 2600，但图腾绘制面积只有桌面的 ~75% → 同面积密度偏高、
     *   帧成本按粒子数线性（perf_anim 实测 _targets 41µs@2600 粒），白贵一截。
     *
     * 标定方法（面积是**浏览器实测值**，不是 CSS 推导值）：
     * 第一版我用 CSS 推导 anchor 尺寸，实测后两个假设都被推翻 ——
     *   · 以为平板画布比桌面小 → 实测 768x1024 的 anchor 面积 367,733px²，比桌面还大；
     *   · 以为手机 anchor 高 ≈370px → 实测 .hero-grid 的 minmax(150px,1fr) 在矮屏被压到 150px，
     *     390x844 实际只有 53,100px²。
     * 教训：几何类参数一律实测取值，别从 CSS 脑补（已入台账 U-124）。
     * 取两个「旧档位已验证可接受」的实测锚点做两点式线性拟合：
     *   手机 390x844 → anchor 实测 53,100px² → 旧档 1500 粒
     *   桌面 1440x900 → anchor 实测 288,829px² → 旧档 2600 粒
     *   => 粒子数 = 1252.2 + 0.004666 x 面积
     * 校核结果（全部实测面积）：两个锚点逐字复现（390→1500、1440→2600），
     * 且**没有任何一档比旧口径更密** —— 自适应只省不涨：
     *   320/360 → 1451（旧 1500）；1024x768 → 2256（旧 2600）；768/1920 → 2600（同旧）
     * 上下限：2600（大屏不再无限加钱）、520（再稀就看不出是凤凰）。 */
    this.DENS_BASE = 1252.2;              /* 两点式拟合截距 */
    this.DENS_SLOPE = 0.004666;           /* 每 px² 新增粒子数 */
    this.DENS_MAX = 2600;
    this.DENS_MIN = 520;
    var _area = this._sampleArea();
    this._area = _area;
    var _byArea = this._densFor(_area);
    if (this.lowEnd && !opts.maxParticles) { _byArea = Math.min(_byArea, 900); }
    this.maxParticles = opts.maxParticles || _byArea;
    this.particles = [];
    this._raf = null;
    this._last = 0;
    this._summonT = -1;
    this._resize = this._resize.bind(this);
    this._tick = this._tick.bind(this);
    this._visible = true;
  }

  /* 采样面积：anchor（若提供且已有尺寸）优先，否则退到画布可视区。
   * 用 anchor 是因为凤凰实际只画在图腾区里，画布可能整屏大但图腾只占一角 ——
   * 按画布算会把粒子摊到空区域，视觉上变稀。取不到尺寸（未布局）时按视口估算。 */
  Phoenix.prototype._sampleArea = function () {
    var a = this.anchor;
    if (a) {
      var ar = a.getBoundingClientRect ? a.getBoundingClientRect() : null;
      if (ar && ar.width > 8 && ar.height > 8) { return ar.width * ar.height; }
    }
    var c = this.canvas;
    var cw = (c && c.clientWidth) || global.innerWidth || 1024;
    var ch = (c && c.clientHeight) || global.innerHeight || 768;
    return cw * ch;
  };

  /* 两点式拟合的密度律；resize 时按新面积重算（_resize 里 20% 节流） */
  Phoenix.prototype._densFor = function (area) {
    var n = Math.round(this.DENS_BASE + this.DENS_SLOPE * (area || 0));
    return Math.max(this.DENS_MIN, Math.min(this.DENS_MAX, n));
  };

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
    /* 采样档位恒按上限采（DENS_MAX），实际用多少由 _build 的 want 决定。
     * 这样 resize 需要「变密」时 _ptsFull 里还有富余目标点可用，
     * 不必重新采样（重采样 = 重新解码 SVG + 逐像素扫描，代价高且会闪一帧）。 */
    var step = Math.max(1, Math.floor(n / (this.DENS_MAX || this.maxParticles)));
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
    /* 采样给的是「最大档」的点集（见 _sample 注释），这里按当前 maxParticles 裁切。
     * 不裁切的话密度自适应就是假的 —— 平板照样拿到 2600 个粒子。
     * 等间隔抽稀（不是随机丢）：随机丢会让某几段翼/尾突然变稀，等间隔保持轮廓均匀。 */
    if (pts.length / 2 > this.maxParticles) {
      var _keep = [], _keepC = [], _step2 = (pts.length / 2) / this.maxParticles;
      for (var _i = 0; _i < this.maxParticles; _i++) {
        var _pi = Math.floor(_i * _step2) * 2;
        if (_pi + 1 >= pts.length) { break; }
        _keep.push(pts[_pi], pts[_pi + 1]);
        if (cols && cols.length > _pi + 2) { _keepC.push(cols[_pi], cols[_pi + 1], cols[_pi + 2]); }
      }
      pts = _keep;
      cols = _keepC.length === _keep.length / 2 * 3 ? _keepC : null;
    }
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
    /* 保存原始扁平点集 [x,y,x,y...]，供低端档重采样使用（_rebuildLite） */
    this._ptsFull = pts;
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

    /* I-7：面积变了且跨过 20% → 重算密度（resize 上节流，不在每次 resize 立刻重建） */
    var _ar = this._sampleArea();
    if (this._area && Math.abs(_ar - this._area) / this._area > 0.2 && this.particles.length) {
      this._area = _ar;
      this._densTimer = this._densTimer || null;
      var self = this;
      if (this._densTimer) { clearTimeout(this._densTimer); }
      this._densTimer = setTimeout(function () { self._densTimer = null; self._resampleDensity(); }, 260);
    } else if (!this._area) {
      this._area = _ar;
    }
  };

  /* 按当前面积重取目标点数，从 _ptsFull（最大档点集）等间隔抽稀重建。
   * 保留既有粒子的 x/y/vx/vy（只换目标点），所以画面是「逐渐变密/变稀」，
   * 不是炸开重来 —— 与 _rebuildLite 的取舍一致。 */
  Phoenix.prototype._resampleDensity = function () {
    var src = this._ptsFull;
    if (!src || src.length < 8 || !this.particles.length) { return; }
    var want = this._densFor(this._area || this._sampleArea());
    if (this.lowEnd) { want = Math.min(want, 900); }
    if (this._degraded) { want = Math.min(want, 900); }
    if (want === this.maxParticles) { return; }
    this.maxParticles = want;
    var total = src.length / 2;
    var step = total / want;
    var kept = [];
    for (var i = 0; i < want; i++) {
      var pi = Math.min(total - 1, Math.floor(i * step));
      var p = this.particles[pi] || this.particles[this.particles.length - 1];
      if (!p) { break; }
      var k = pi * 2;
      if (k + 1 < src.length) { p.tx = src[k]; p.ty = src[k + 1]; }
      kept.push(p);
    }
    /* 变密时 kept 会比 want 少（对象不够）→ 用已有对象补齐新目标点，
     * 否则 resize 到大屏反而拿不到新增的密度。 */
    var proto = this.particles[0];
    while (kept.length < want && proto) {
      var idx = kept.length % total;
      var kk = idx * 2;
      kept.push({
        tx: src[kk], ty: src[kk + 1],
        x: 0.5 + (Math.random() - 0.5) * 1.6, y: 0.5 + (Math.random() - 0.5) * 1.6,
        vx: 0, vy: 0, r: proto.r, g: proto.g, b: proto.b,
        size: 0.9 + Math.random() * 1.5, ph: Math.random() * Math.PI * 2,
        k: 0.055 + Math.random() * 0.05, damp: 0.86 + Math.random() * 0.05
      });
    }
    this.particles = kept;
    this.count = kept.length;
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

  /* 三角函数查表：抖动/扑翼用的角度是「时间同相位不同」，
   * 直接查表比每帧 2634 次 Math.sin/cos 快一个数量级，视觉无差别
   * （抖动幅度 0.0011，量化到 1/1024 圆误差 < 0.0007，远小于 1 像素）。 */
  var TBL_N = 1024, TBL_SIN = new Float32Array(TBL_N), TBL_COS = new Float32Array(TBL_N);
  for (var _ti = 0; _ti < TBL_N; _ti++) {
    var _a = _ti / TBL_N * Math.PI * 2;
    TBL_SIN[_ti] = Math.sin(_a); TBL_COS[_ti] = Math.cos(_a);
  }
  function fsin(x) {
    var k = (x * (TBL_N / (Math.PI * 2))) | 0;
    return TBL_SIN[((k % TBL_N) + TBL_N) % TBL_N];
  }
  function fcos(x) {
    var k = (x * (TBL_N / (Math.PI * 2))) | 0;
    return TBL_COS[((k % TBL_N) + TBL_N) % TBL_N];
  }

  Phoenix.prototype._targets = function (time) {
    // 计算本帧目标点：assemble/idle 为图腾深呼吸；flight 为扑翼飞行
    var st = this.state;
    var ps = this.particles;
    var flap = Math.sin(time * 0.0042);          // 每帧一次，循环外
    var fly = st === 'flight' || st === 'burst';
    var driftX = fly ? Math.sin(time * 0.0009) * 0.035 : 0;   // 展开成标量，避免每帧建对象
    var driftY = fly ? Math.sin(time * 0.0013) * 0.022 : 0;
    var spread = st === 'flight' ? 1.10 : 1.0;
    var burst = st === 'burst';
    var jt = fly ? 0.0018 : 0.0011;
    var tA = time * 0.0016, tB = time * 0.0019;
    var out = this._tbuf || (this._tbuf = new Float32Array(ps.length * 2));
    for (var i = 0; i < ps.length; i++) {
      var p = ps[i];
      var tx = p.tx, ty = p.ty;
      if (!burst) {
        // 扑翼：以身体中轴为轴，按离轴距离做旋转位移
        var dx = tx - 0.5, dy = ty - 0.5;
        var ax = dx < 0 ? -dx : dx;
        var k5 = ax * 5.2;
        if (k5 < 1) {
          /* 中轴附近的粒子：amt < 0.16*flap，旋转位移量级 0.0027，
           * 低于抖动幅度（0.0011 的 2 倍多），跳过旋转在视觉上不可辨。
           * 实测这类粒子约占 40%，省掉的是每粒子 2 次三角 + 1 次 sign。 */
          var amtS = k5 * 0.16 * flap;
          if (amtS > 0.0011) {
            var cA = fcos(amtS), sA = fsin(amtS);
            ty = 0.5 + dy * cA - dx * sA * (dx < 0 ? -1 : 1) * 0.6;
          }
          tx = 0.5 + dx * (1 + 0.05 * flap * (ax * 3 < 1 ? ax * 3 : 1));
        } else {
          var amt = 0.16 * flap;
          var cA2 = fcos(amt), sA2 = fsin(amt);
          var ny = dy * cA2 - dx * sA2 * (dx < 0 ? -1 : 1) * 0.6;
          ty = 0.5 + ny;
          tx = 0.5 + dx * (1 + 0.05 * flap);
        }
      }
      // 呼吸 / 抖动（查表）
      tx += fsin(tA + p.ph) * jt;
      ty += fcos(tB + p.ph * 1.3) * jt;
      out[i * 2] = 0.5 + (tx - 0.5) * spread + driftX;
      out[i * 2 + 1] = 0.5 + (ty - 0.5) * spread + driftY;
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
      /* 运行时自适应降档 —— 用实测信号，不猜机型。
       * 实测（2026-10-20 轮9，本机 32 核）：每帧 2634 粒子 × 3 次 API = 约 7900 次调用，
       * 单帧 p95 4.9ms；低端机单核算力约本机 1/8 → 估算 ≈39ms/帧（约 25fps），必卡。
       * 注意：本函数里的 _frames 每 900ms 会被 FPS 统计重置，不能拿来当累计帧数，
       * 因此另设 _adaptN 独立计数；只降一次，避免画面反复抖动。 */
      this._adaptN = (this._adaptN || 0) + 1;
      if (this._t0 === 0) { this._t0 = now; }
      if (this._adaptN === 90 && !this._degraded) {
        var _elapsed = (now - this._t0) / 1000;
        var _avgFps = _elapsed > 0 ? (90 / _elapsed) : 60;
        if (_avgFps < 45 && this.maxParticles > 900) {
          this._degraded = true;
          this.maxParticles = 900;
          this._rebuildLite();
        }
      }
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

  /* 低端档重采样：把目标点按步长抽稀到 maxParticles 附近。
   * 只抽稀目标点，保留粒子对象本身（避免重建导致画面闪一帧），
   * 让已有粒子用现有弹簧逻辑收敛到新目标，视觉上是「点变粗」而非「炸开」。 */
  Phoenix.prototype._rebuildLite = function () {
    var src = this._ptsFull;
    if (!src || src.length < 4) { return; }
    var total = src.length / 2;
    var want = Math.min(this.maxParticles, total);
    if (total <= want) { return; }
    var step = total / want;
    /* 关键：**粒子对象本身也要减**。
     * 一手实测（轮9）：只把目标点抽稀到 900、粒子对象仍留 2634，
     * 帧成本 5.0 → 5.5ms 反而更慢 —— 因为每帧开销 = 粒子数 × 3 次 canvas API，
     * 粒子叠到同一个点并不会减少绘制次数。必须 splice 掉多余粒子。 */
    var kept = [];
    for (var i = 0; i < want; i++) {
      var pi = Math.floor(i * step);
      var p = this.particles[pi];
      if (!p) { break; }
      var k = pi * 2;
      if (k + 1 < src.length) { p.tx = src[k]; p.ty = src[k + 1]; }
      kept.push(p);
    }
    this.particles = kept;
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
