/* wood-demo.js — 落地页「一木成像」可拖拽雕刻台
 * 一根进度轴 p(0→1)：拖动滑杆、在画面上左右拖、或用方向键，都能把这段樟木从选木推到开光。
 * 几何与 AR 场景一共用 assets/js/wood-to-statue.js，两处画面严格同源。
 * 零依赖、零外部请求；prefers-reduced-motion 下不自动播放，只给静态像与手动拖拽。
 */
(function (global) {
  'use strict';
  var E = global.WOOD_TO_STATUE;
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var clamp = function (v, a, b) { return v < a ? a : (v > b ? b : v); };
  var reduced = !!(global.matchMedia && global.matchMedia("(prefers-reduced-motion: reduce)").matches);
  var RUN_SECONDS = 21;   // 自动走一遍的时长

  var CAP = {
    wood:   ['一 · 选木', '整段樟木要干透、无裂、少节，顺纹理立身。木性稳了，像才立得住。'],
    layout: ['二 · 定像', '丹青先生先立中轴，再分头、胸、腰、膝的比例，粉线一弹，尺寸就定死在木上。'],
    block:  ['三 · 开坯', '斧锯开大形，凿子打坯。先方后圆、先粗后细，一层层把多余的木头让出去。'],
    refine: ['四 · 修光', '把刀痕收干净。东固造像最吃紧的是开面——威而不怖、亲而不俗。'],
    paint:  ['五 · 彩绘贴金', '生漆打底，再上彩、贴金箔。眉眼的弧度、衣纹的走向，都在这时候定下神情。'],
    open:   ['六 · 开光', '神像雕成还不算完成。丹青先生亲自主持开光仪式，赋予木像「法力」，至此方告完成。']
  };
  var ORDER = ['wood', 'layout', 'block', 'refine', 'paint', 'open'];

  var root = $("#carve-sec"), canvas = $("#carve-stage"), slider = $("#carve-slider"),
      rail = $("#carve-rail"), capTitle = $("#carve-cap-title"), capBody = $("#carve-cap-body"),
      playBtn = $("#carve-play"), hint = $("#carve-hint"), pct = $("#carve-pct");

  if (!root || !canvas || !E) { return; }

  var ctx = null, dpr = 1, W = 0, H = 0;
  var p = 0, playing = !reduced, raf = null, last = 0, visible = true, dragging = false, lastStage = -1;

  function resize() {
    dpr = Math.min(global.devicePixelRatio || 1, 2);
    W = canvas.clientWidth || 900;
    H = canvas.clientHeight || 560;
    canvas.width = Math.round(W * dpr);
    canvas.height = Math.round(H * dpr);
    if (!ctx) { ctx = canvas.getContext("2d"); }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function stageIndex() { return E.stageOf(p); }

  function paintChrome() {
    var si = stageIndex();
    if (si === lastStage) { return; }
    lastStage = si;
    var key = ORDER[si];
    var c = CAP[key] || ["", ""];
    if (capTitle) { capTitle.textContent = c[0]; }
    if (capBody) { capBody.textContent = c[1]; }
    if (rail) {
      Array.prototype.forEach.call(rail.children, function (el, i) {
        el.classList.toggle("on", i === si);
        el.classList.toggle("past", i < si);
        el.setAttribute("aria-current", i === si ? "step" : "false");
      });
    }
  }

  function frame(now) {
    raf = requestAnimationFrame(frame);
    var dt = Math.min(64, now - last); last = now;
    if (!visible) { return; }
    if (playing && !dragging) {
      p += dt / 1000 / RUN_SECONDS;
      if (p >= 1) { p = 1; playing = false; setPlayLabel(); }
      if (slider) { slider.value = String(Math.round(p * 1000)); }
    }
    ctx.clearRect(0, 0, W, H);
    // 落地页取景：像身要顶满画布（原来只占 60% 高，成品细节被缩没了，
    // 「像素级复刻」在小尺寸下等于白搭）。成品图占位 = SPAN*s = 1.02s，
    // 故 s 取画布高的 0.84 倍即可让像身高度达到约 86% 画布高。
    var wide = W >= 900;
    var box = wide
      ? { cx: W * 0.66, cy: H * 0.60, s: Math.min(H * 0.84 / 1.02, W * 0.42) }
      : { cx: W * 0.5, cy: H * 0.575, s: Math.min(H * 0.84 / 1.02, W * 0.86) };
    E.draw(ctx, W, H, p, now, { box: box, moteCount: 24, backdrop: true });
    paintChrome();
    if (pct) { pct.textContent = "已成 " + Math.round(p * 100) + "%"; }
  }

  function start() {
    if (raf) { return; }
    last = performance.now();
    raf = requestAnimationFrame(frame);
  }
  function stop() { if (raf) { cancelAnimationFrame(raf); raf = null; } }

  function setPlayLabel() {
    if (!playBtn) { return; }
    playBtn.textContent = playing ? "暂停" : (p >= 1 ? "再雕一遍" : "继续");
    playBtn.setAttribute("aria-pressed", String(playing));
  }

  function setP(v) {
    p = clamp(v, 0, 1);
    if (slider) { slider.value = String(Math.round(p * 1000)); }
  }

  /* ---------- 控件 ---------- */
  if (slider) {
    slider.addEventListener("input", function () {
      setP(Number(slider.value) / 1000);
      playing = false; setPlayLabel();
    });
  }
  if (playBtn) {
    playBtn.addEventListener("click", function () {
      if (p >= 1) { p = 0; }
      playing = !playing; setPlayLabel();
    });
  }
  if (rail) {
    rail.addEventListener("click", function (e) {
      var b = e.target.closest("button[data-p]");
      if (!b) { return; }
      setP(Number(b.getAttribute("data-p")));
      playing = false; setPlayLabel();
    });
  }
  // 画面内左右拖 = 直接推刀
  function dragTo(clientX) {
    var r = canvas.getBoundingClientRect();
    setP((clientX - r.left) / Math.max(1, r.width));
  }
  canvas.addEventListener("pointerdown", function (e) {
    dragging = true; playing = false; setPlayLabel();
    if (canvas.setPointerCapture) { try { canvas.setPointerCapture(e.pointerId); } catch (err) {} }
    dragTo(e.clientX);
    if (hint) { hint.classList.add("gone"); }
  });
  canvas.addEventListener("pointermove", function (e) { if (dragging) { dragTo(e.clientX); } });
  canvas.addEventListener("pointerup", function () { dragging = false; });
  canvas.addEventListener("pointercancel", function () { dragging = false; });
  canvas.addEventListener("keydown", function (e) {
    if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
      e.preventDefault();
      setP(p + (e.key === "ArrowRight" ? 0.02 : -0.02));
      playing = false; setPlayLabel();
      if (hint) { hint.classList.add("gone"); }
    }
  });
  canvas.setAttribute("tabindex", "0");
  canvas.setAttribute("role", "slider");
  canvas.setAttribute("aria-label", "从一段樟木到一尊神像：左右拖动或按方向键推进雕刻进度");
  canvas.setAttribute("aria-valuemin", "0");
  canvas.setAttribute("aria-valuemax", "100");

  /* ---------- 可见性：滚出画面即停表，省电 ---------- */
  if ("IntersectionObserver" in global) {
    new IntersectionObserver(function (es) {
      es.forEach(function (en) {
        visible = en.isIntersecting;
        if (visible) { start(); } else { stop(); }
      });
    }, { threshold: 0.08 }).observe(root);
  }
  global.addEventListener("resize", function () { if (visible) { resize(); } }, { passive: true });
  document.addEventListener("visibilitychange", function () {
    if (document.hidden) { stop(); } else if (visible) { resize(); start(); }
  });

  /* ---------- 装配刻度轨 ---------- */
  if (rail) {
    rail.innerHTML = ORDER.map(function (k, i) {
      var at = E.STAGES[i].at[0];
      return '<button type="button" data-p="' + (Math.min(0.995, at + 0.001)).toFixed(3) + '">' +
        '<b>' + "一二三四五六".charAt(i) + '</b><span>' + E.STAGES[i].name + '</span></button>';
    }).join("");
  }
  if (reduced) {
    setP(1);
    if (hint) { hint.textContent = "已按「减少动态效果」停在成品：拖动下方滑杆可回到任意工序"; }
  }
  if (!reduced && hint) { setTimeout(function () { hint.classList.add("gone"); }, 7000); }
  resize();
  setPlayLabel();
  start();

  global.__carve = {
    stats: function () { return { p: Math.round(p * 1000) / 1000, stage: ORDER[stageIndex()], playing: playing, reduced: reduced, size: W + "x" + H }; },
    set: setP,
    play: function (v) { playing = v !== false; setPlayLabel(); }
  };
})(window);
