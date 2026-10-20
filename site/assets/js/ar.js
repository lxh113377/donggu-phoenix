/* ar.js — 轻量化 AR 展陈馆控制层
 * 职责：全屏舞台、摄像头实景叠加、识别锁定与降级、场景切换、章节叙事、集章与停留计时。
 * 设计原则：零依赖、零模型文件、零外部请求；摄像头只是可选背景，关闭也能完整看三段动画。
 */
(function (global) {
  'use strict';

  var D = global.AR_DATA || { scenes: [], route: [], ui: {}, meta: {} };
  var U = (global.AR_SCENES && global.AR_SCENES.utils) || { clamp: function (v, a, b) { return v < a ? a : v > b ? b : v; } };
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var reduced = !!(global.matchMedia && global.matchMedia("(prefers-reduced-motion: reduce)").matches);
  var STORE_KEY = "donggu-ar-v1";

  /* ---------- 状态 ---------- */
  var state = {
    open: false,
    sceneIdx: -1,
    scene: null,
    playing: false,
    t: 0,
    mode: "gallery",     // gallery（展柜模式）| camera（实景叠加）
    locked: false,
    stamps: [],
    visits: 0,
    dwell: 0,             // 本页累计 AR 停留秒数
    chapterDone: [],
    fps: 0
  };

  function loadStore() {
    try {
      var raw = global.localStorage && localStorage.getItem(STORE_KEY);
      if (!raw) { return; }
      var o = JSON.parse(raw);
      state.stamps = Array.isArray(o.stamps) ? o.stamps : [];
      state.dwell = typeof o.dwell === "number" ? o.dwell : 0;
      state.visits = typeof o.visits === "number" ? o.visits : 0;
    } catch (e) { /* 隐私模式/无 storage 时静默降级为内存态 */ }
  }
  function saveStore() {
    try {
      if (!global.localStorage) { return; }
      localStorage.setItem(STORE_KEY, JSON.stringify({
        stamps: state.stamps, dwell: Math.round(state.dwell), visits: state.visits, at: Date.now()
      }));
    } catch (e) { /* 同上 */ }
  }
  loadStore();

  /* ---------- DOM ---------- */
  var el = {};
  function q() {
    el.root = $("#ar");
    el.video = $("#ar-video");
    el.canvas = $("#ar-stage");
    el.title = $("#ar-title");
    el.en = $("#ar-en");
    el.kicker = $("#ar-kicker");
    el.chapter = $("#ar-chapter");
    el.chapterEn = $("#ar-chapter-en");
    el.body = $("#ar-body");
    el.bodyEn = $("#ar-body-en");
    el.hint = $("#ar-hint");
    el.badge = $("#ar-badge");
    el.bar = $("#ar-bar");
    el.time = $("#ar-time");
    el.stamps = $("#ar-stamps");
    el.dwell = $("#ar-dwell");
    el.close = $("#ar-close");
    el.play = $("#ar-play");
    el.prev = $("#ar-prev");
    el.next = $("#ar-next");
    el.restart = $("#ar-restart");
    el.dots = $("#ar-dots");
    el.camToggle = $("#ar-cam-toggle");
    el.toast = $("#toast");
  }

  function toast(msg, ms) {
    if (!el.toast) { return; }
    el.toast.textContent = msg;
    el.toast.classList.add("on");
    clearTimeout(toast._t);
    toast._t = setTimeout(function () { el.toast.classList.remove("on"); }, ms || 2600);
  }

  /* ---------- 画布 ---------- */
  var ctx = null, dpr = 1, W = 0, H = 0, raf = null, lastNow = 0;
  var fpsFrames = 0, fpsT = 0;

  function resize() {
    if (!el.canvas) { return; }
    dpr = Math.min(global.devicePixelRatio || 1, 2);
    W = el.canvas.clientWidth || global.innerWidth;
    H = el.canvas.clientHeight || global.innerHeight;
    el.canvas.width = Math.round(W * dpr);
    el.canvas.height = Math.round(H * dpr);
    if (!ctx) { ctx = el.canvas.getContext("2d", { alpha: true }); }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function frame(now) {
    raf = requestAnimationFrame(frame);
    var dt = Math.min(64, now - lastNow);
    lastNow = now;
    if (!state.open || !state.scene) { return; }

    if (state.playing) {
      state.t += dt / 1000;
      state.dwell += dt / 1000;
      if (state.t >= state.scene.duration) {
        state.t = state.scene.duration;
        state.playing = false;
        complete();
      }
    }

    ctx.clearRect(0, 0, W, H);
    state.scene.seek(state.t);
    state.scene.draw(ctx, W, H, now);

    fpsFrames++;
    if (now - fpsT > 900) {
      state.fps = Math.round(fpsFrames * 1000 / (now - fpsT));
      fpsFrames = 0;
      fpsT = now;
    }
    paintHud();
  }

  function chapterIndex() {
    var s = state.scene;
    if (!s) { return 0; }
    var n = s.chapters.length, len = s.duration / n;
    return U.clamp(Math.floor(state.t / len), 0, n - 1);
  }

  var lastChapter = -1;
  function paintHud() {
    var s = state.scene;
    if (!s) { return; }
    var ci = chapterIndex();
    var ch = s.chapters[ci];
    if (ci !== lastChapter) {
      lastChapter = ci;
      if (el.chapter) { el.chapter.textContent = ch.title; }
      if (el.chapterEn) { el.chapterEn.textContent = ch.en || ""; }
      if (el.body) { el.body.textContent = ch.body || ""; }
      if (el.bodyEn) { el.bodyEn.textContent = ch.enBody || ""; }
      el.root.classList.remove("beat");
      void el.root.offsetWidth;
      el.root.classList.add("beat");
    }
    if (el.bar) { el.bar.style.width = (state.t / s.duration * 100).toFixed(2) + "%"; }
    if (el.time) { el.time.textContent = fmt(state.t) + " / " + fmt(s.duration); }
    if (el.dwell) { el.dwell.textContent = fmt(state.dwell); }
    if (el.play) {
      var label = state.playing ? (D.ui.pause || "暂停") : (D.ui.play || "继续");
      if (el.play.textContent !== label) { el.play.textContent = label; }
    }
  }

  function fmt(sec) {
    var m = Math.floor(sec / 60), s = Math.floor(sec % 60);
    return (m < 10 ? "0" : "") + m + ":" + (s < 10 ? "0" : "") + s;
  }

  /* ---------- 场景装配 ---------- */
  function sceneData(id) {
    for (var i = 0; i < D.scenes.length; i++) {
      if (D.scenes[i].id === id) { return D.scenes[i]; }
    }
    return null;
  }

  function paintStamps() {
    if (!el.stamps) { return; }
    el.stamps.innerHTML = D.scenes.map(function (s) {
      var got = state.stamps.indexOf(s.id) >= 0;
      return '<span class="stamp' + (got ? " got" : "") + '" title="' + s.stamp + '">' + (got ? s.stamp : "○") + "</span>";
    }).join("");
    var all = state.stamps.length >= D.scenes.length;
    var line = $("#ar-stamp-line");
    if (line) {
      line.textContent = all ? "三章集齐 · 已解锁完整动线" : (D.ui.stamps || "集章") + " " + state.stamps.length + "/" + D.scenes.length;
    }
    updateStats();
  }

  function paintDots() {
    if (!el.dots) { return; }
    el.dots.innerHTML = D.scenes.map(function (s, i) {
      return '<button type="button" role="tab" data-scene="' + s.id + '" aria-selected="' + (i === state.sceneIdx) + '">' +
        '<b>' + s.no + "</b>" + s.name + "</button>";
    }).join("");
  }

  function loadScene(id, autoplay) {
    var data = sceneData(id);
    if (!data) { return; }
    state.sceneIdx = D.scenes.indexOf(data);
    state.scene = global.AR_SCENES.create(id, data);
    state.t = 0;
    lastChapter = -1;
    state.chapterDone = [];
    if (el.title) { el.title.textContent = data.name; }
    if (el.en) { el.en.textContent = data.en; }
    if (el.kicker) { el.kicker.textContent = data.kicker; }
    paintDots();
    paintHud();
    state.playing = autoplay !== false;
    // 减少动态效果（prefers-reduced-motion）：不自动播放，直接给一张有信息量的关键帧
    if (reduced && state.playing) {
      state.playing = false;
      state.t = typeof data.poster === "number" ? data.poster : 0;
      lastChapter = -1;
    }
    if (el.play) { el.play.textContent = state.playing ? (D.ui.pause || "暂停") : (D.ui.play || "继续"); }
    try { global.location.hash = "ar=" + id; } catch (e) { /* 某些内置浏览器限制 */ }
  }

  function complete() {
    var s = state.scene;
    if (!s) { return; }
    if (state.stamps.indexOf(s.id) < 0) {
      state.stamps.push(s.id);
      saveStore();
      paintStamps();
      toast(D.ui.done || "本段完成 · 已落章", 3000);
    }
    state.sceneDone = true;
  }

  /* ---------- 摄像头实景叠加 ---------- */
  var stream = null, probing = false, probeCvs = null, probeCtx = null, scanStart = 0;

  function setMode(mode, msg) {
    state.mode = mode;
    if (el.root) { el.root.classList.toggle("cam", mode === "camera"); }
    if (el.badge) {
      el.badge.textContent = mode === "camera" ? (D.ui.camMode || "实景叠加") : (D.ui.displayMode || "展柜模式");
    }
    if (msg) { toast(msg, 2800); }
  }

  function stopCamera() {
    probing = false;
    if (stream) {
      stream.getTracks().forEach(function (t) { t.stop(); });
      stream = null;
    }
    if (el.video) { el.video.srcObject = null; }
    if (el.root) { el.root.classList.remove("cam"); }
    state.mode = "gallery";
    if (el.badge) { el.badge.textContent = D.ui.displayMode || "展柜模式"; }
  }

  function warmRatio() {
    if (!el.video || el.video.readyState < 2) { return -1; }
    var w = 72, h = 72;
    if (!probeCvs) {
      probeCvs = document.createElement("canvas");
      probeCvs.width = w; probeCvs.height = h;
      probeCtx = probeCvs.getContext("2d", { willReadFrequently: true });
    }
    try { probeCtx.drawImage(el.video, 0, 0, w, h); } catch (e) { return -1; }
    var d;
    try { d = probeCtx.getImageData(0, 0, w, h).data; } catch (e) { return -1; }
    var hit = 0, tot = 0;
    for (var i = 0; i < d.length; i += 4) {
      var px = (i / 4) % w, py = Math.floor((i / 4) / w);
      if (px < w * 0.2 || px > w * 0.8 || py < h * 0.2 || py > h * 0.8) { continue; }
      tot++;
      var r = d[i], g = d[i + 1], b = d[i + 2];
      if ((r > 90 && r > g * 1.18 && r > b * 1.35) || (r > 150 && g > 110 && b < 110)) { hit++; }
    }
    return tot ? hit / tot : -1;
  }

  function probeLoop() {
    if (!probing) { return; }
    var ratio = warmRatio();
    if (ratio > 0.16) {
      state.locked = true;
      if (el.root) { el.root.classList.add("locked"); }
      if (el.hint) { el.hint.textContent = D.ui.locked || "已锁定 · 开始叠加"; }
      setTimeout(function () {
        probing = false;
        if (el.hint) { el.hint.textContent = ""; }
        state.playing = true;
      }, 900);
      return;
    }
    var sec = (performance.now() - scanStart) / 1000;
    if (el.hint && sec > 4) {
      el.hint.textContent = D.ui.scanHintAdd || "对准后自动叠加，也可直接开演";
    }
    setTimeout(probeLoop, 220);
  }

  function startCamera() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setMode("gallery", D.ui.noCam || "没有可用摄像头，已切到展柜模式");
      return Promise.resolve(false);
    }
    if (global.location.protocol !== "https:" && global.location.hostname !== "localhost" && global.location.hostname !== "127.0.0.1" && global.location.protocol !== "file:") {
      setMode("gallery", "非安全连接，无法调用摄像头，已切到展柜模式");
      return Promise.resolve(false);
    }
    return navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: "environment" } }, audio: false })
      .then(function (s) {
        stream = s;
        el.video.srcObject = s;
        return el.video.play().catch(function () {});
      })
      .then(function () {
        setMode("camera");
        if (el.hint) { el.hint.textContent = D.ui.scanHint || "把造像或地标放进取景框中央"; }
        scanStart = performance.now();
        probing = true;
        probeLoop();
        return true;
      })
      .catch(function (err) {
        var name = (err && err.name) || "";
        var m = name === "NotAllowedError" ? "摄像头权限被拒绝，已切到展柜模式"
          : name === "NotFoundError" ? "未找到摄像头，已切到展柜模式"
          : "摄像头不可用，已切到展柜模式";
        setMode("gallery", m);
        return false;
      });
  }

  /* ---------- 开关 ---------- */
  var lastFocus = null;

  function focusables() {
    if (!el.root) { return []; }
    return $$("button, [href], input, select, textarea, [tabindex]:not([tabindex='-1'])", el.root)
      .filter(function (n) { return n.offsetParent !== null && !n.disabled; });
  }

  function trapTab(e) {
    if (e.key !== "Tab") { return; }
    var list = focusables();
    if (!list.length) { return; }
    var first = list[0], last = list[list.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  }

  function open(id, opts) {
    opts = opts || {};
    q();
    if (!el.root) { return; }
    // ar-data.js 缺失/损坏时不崩：直接提示，页面其余部分不受影响
    if (!D.scenes || !D.scenes.length) {
      toast("AR 内容未加载，请检查网络后刷新", 3200);
      return;
    }
    if (!state.open) { state.visits++; }
    if (!state.open) { lastFocus = document.activeElement; }
    state.open = true;
    el.root.classList.add("on");
    el.root.setAttribute("aria-hidden", "false");
    // 焦点移入播放层，避免读屏与键盘仍停在底下的页面
    setTimeout(function () { if (el.close) { el.close.focus({ preventScroll: true }); } }, 0);
    document.documentElement.style.overflow = "hidden";
    // 播放层是全屏对话框：Tab 只在层内循环
    el.root.addEventListener("keydown", trapTab);
    resize();
    if (!raf) { lastNow = performance.now(); fpsT = lastNow; raf = requestAnimationFrame(frame); }
    paintStamps();
    loadScene(id || D.scenes[0].id, opts.autoplay !== false);
    if (opts.camera !== false) { startCamera(); } else { setMode("gallery"); }
    if (reduced) { toast("已按「减少动态效果」切为手动分镜，可用「下一段」逐章翻看", 3400); }
    saveStore();
  }

  function close() {
    state.open = false;
    state.playing = false;
    if (el.root) {
      el.root.classList.remove("on");
      el.root.setAttribute("aria-hidden", "true");
    }
    if (raf) { cancelAnimationFrame(raf); raf = null; }
    stopCamera();
    document.documentElement.style.overflow = "";
    if (el.root) { el.root.removeEventListener("keydown", trapTab); }
    try { history.replaceState(null, "", location.pathname + location.search); } catch (e) { /* noop */ }
    saveStore();
    // 焦点还给打开播放层的那个元素
    if (lastFocus && lastFocus.focus) {
      try { lastFocus.focus({ preventScroll: true }); } catch (e) { lastFocus.focus(); }
    }
    lastFocus = null;
  }

  function updateStats() {
    var stats = $("#ar-stats-line");
    if (!stats) { return; }
    var total = D.scenes.reduce(function (a, s) { return a + s.duration; }, 0);
    stats.textContent = "三段合计 " + total + " 秒 · " + ((D.meta && D.meta.dwell) || "") +
      " · 集章 " + state.stamps.length + "/" + D.scenes.length +
      " · 停留计时与集章全部在本地完成，不上传任何数据。";
  }

  /* ---------- 落地页场景卡 ---------- */
  function renderCards() {
    var box = $("#ar-cards");
    if (!box) { return; }
    box.innerHTML = D.scenes.map(function (s) {
      var ch = s.chapters.map(function (c) { return "<li>" + c.title + "</li>"; }).join("");
      /* 出处：不能只显示数量。读者/评审看到「N 条」却看不到是什么，
       * 会质疑出处标得实不实。用原生 <details> 默认收起（不打断阅读流），
       * 点开逐条列出；有 url 的给可点击链接（rel/target 齐全）。
       * 链接只在用户主动点击时发起请求，不违反「页面自身零外部请求」。 */
      var extra = "";
      if (s.sources && s.sources.length) {
        var items = s.sources.map(function (src) {
          var label = src.label || "";
          if (src.url) {
            return '<li><a href="' + src.url + '" target="_blank" rel="noopener noreferrer">' +
              label + '</a></li>';
          }
          return "<li>" + label + "</li>";
        }).join("");
        extra = '<details class="ar-src">' +
          '<summary>素材出处 ' + s.sources.length + ' 条</summary>' +
          '<ol>' + items + '</ol>' +
          '</details>';
      }
      return '<article class="ar-card">' +
        '<span class="no">' + s.no + "</span>" +
        "<h3>" + s.name + "</h3>" +
        '<p class="en">' + s.en + "</p>" +
        '<span class="kick">' + s.kicker + "</span>" +
        '<p class="tagline">' + s.tagline + "</p>" +
        "<ol>" + ch + "</ol>" +
        '<span class="dur">时长 ' + s.duration + "s · 落「" + s.stamp + "」</span>" +
        extra +
        '<a class="go" role="button" tabindex="0" data-ar="' + s.id + '" href="#ar-gallery" aria-label="开演 ' + s.name + '">开演</a>' +
        "</article>";
    }).join("");
    updateStats();
  }

  /* ---------- 交互绑定 ---------- */
  function bind() {
    q();
    renderCards();
    if (!el.root) { return; }
    if (el.close) { el.close.addEventListener("click", close); }
    if (el.play) {
      el.play.addEventListener("click", function () {
        if (!state.scene) { return; }
        if (state.t >= state.scene.duration) { state.t = 0; }
        state.playing = !state.playing;
      });
    }
    if (el.restart) {
      el.restart.addEventListener("click", function () {
        state.t = 0; lastChapter = -1; state.playing = true;
      });
    }
    function step(dir) {
      var s = state.scene;
      if (!s) { return; }
      var n = s.chapters.length, len = s.duration / n;
      var ci = U.clamp(chapterIndex() + dir, 0, n - 1);
      state.t = ci * len + 0.001;
      lastChapter = -1;
    }
    if (el.prev) { el.prev.addEventListener("click", function () { step(-1); }); }
    if (el.next) { el.next.addEventListener("click", function () { step(1); }); }
    if (el.camToggle) {
      el.camToggle.addEventListener("click", function () {
        if (state.mode === "camera") { stopCamera(); toast("已切回展柜模式", 2000); }
        else { startCamera(); }
      });
    }
    if (el.dots) {
      el.dots.addEventListener("click", function (e) {
        var b = e.target.closest("button[data-scene]");
        if (!b) { return; }
        loadScene(b.getAttribute("data-scene"), true);
      });
    }
    document.addEventListener("click", function (e) {
      var t = e.target.closest("[data-ar]");
      if (!t) { return; }
      e.preventDefault();
      var id = t.getAttribute("data-ar");
      open(id === "gallery" ? (D.scenes[0] && D.scenes[0].id) : id, { camera: t.getAttribute("data-nocam") !== "1" });
    });
    document.addEventListener("keydown", function (e) {
      if (!state.open) { return; }
      if (e.key === "Escape") { close(); }
      else if (e.key === "ArrowRight") { step(1); }
      else if (e.key === "ArrowLeft") { step(-1); }
      else if (e.key === " ") { e.preventDefault(); state.playing = !state.playing; }
    });
    global.addEventListener("resize", function () { if (state.open) { resize(); } }, { passive: true });
    document.addEventListener("visibilitychange", function () {
      if (document.hidden && state.playing) { state.playing = false; }
    });
    // 直接以 #ar=xxx 进场（展板二维码可带参数直达某一段）
    function readHash() {
      var m = /^#ar=([a-z]+)$/.exec(global.location.hash || "");
      return m ? m[1] : null;
    }
    // 首次加载：展签/文创上的场景直连二维码 .../#ar=craft | #ar=red | #ar=phoenix
    try {
      var first = readHash();
      // 展签扫码 = 现场手机，直接尝试实景叠加；失败会自动落回展柜模式
      if (first) { open(first, { camera: true }); }
    } catch (e) { /* 哈希异常不影响页面 */ }
    // 同页内改哈希（例如从一张展签扫到另一张、或站内链接）：跟随切换
    var _closingByHash = false;
    global.addEventListener("hashchange", function () {
      try {
        var id = readHash();
        if (!id) {
          // HASH-BACK-FIX: hash cleared by browser back -> close AR too.
          if (state.open && !_closingByHash) {
            _closingByHash = true;
            try { close(); } finally { _closingByHash = false; }
          }
          return;
        }
        if (!state.open) { open(id, { camera: false }); }
        else if (!state.scene || state.scene.id !== id) { loadScene(id, true); }
      } catch (e) { /* noop */ }
    });
  }

  /* ---------- 对外 API（供自动化验收） ---------- */
  global.__ar = {
    open: open,
    close: close,
    goto: function (id) { if (!state.open) { open(id); } else { loadScene(id, true); } },
    seek: function (sec) { state.t = sec; lastChapter = -1; },
    play: function (v) { state.playing = v !== false; },
    stats: function () {
      return {
        open: state.open, scene: state.scene ? state.scene.id : null,
        mode: state.mode, locked: state.locked, playing: state.playing,
        t: Math.round(state.t * 10) / 10,
        chapter: state.scene ? chapterIndex() : -1,
        stamps: state.stamps.slice(), visits: state.visits,
        dwell: Math.round(state.dwell), fps: state.fps,
        canvas: W + "x" + H
      };
    },
    scenes: D.scenes.map(function (s) { return { id: s.id, name: s.name, duration: s.duration, chapters: s.chapters.length }; })
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else { bind(); }
})(window);