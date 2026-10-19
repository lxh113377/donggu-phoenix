/* main.js — 页面装配、滚动叙事、图腾召唤与摄像头降级链 */
(function () {
  'use strict';

  var C = window.CULTURE || { meta: {}, hero: {}, culture: [], craftsmen: [], merch: [], roadmap: [] };
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- 文案兜底（culture.js 404 时仍可完整渲染） ---------- */
  var FALLBACK = {
    meta: { title: '畲 · 凤鸣东固', team: '江西科技学院 · 薪火寰行实践团',
            place: '江西省吉安市青原区东固畲族乡' },
    hero: { tag: 'She Ethnic Phoenix · Donggu',
            lead: '一枚图腾，一只凤凰。\n扫描它，让三百年前的羽衣在屏幕上重新张开。',
            cta: '轻触图腾 · 唤凤' },
    culture: [{ no: '01', kicker: '起源', title: '三公主的羽衣',
                body: '畲族奉盘瓠为始祖。传说盘瓠因平番有功，被高辛帝招为东床快婿；成婚那日，三公主凤冠凤衣。此后畲家生女，便备一身凤凰装。' }],
    craftsmen: [], merch: [], roadmap: []
  };
  if (!C.culture || !C.culture.length) C = Object.assign({}, FALLBACK, { culture: FALLBACK.culture });

  /* ---------- Toast ---------- */
  var toastEl = $('#toast'), toastTimer = null;
  function toast(msg, ms) {
    if (!toastEl) return;
    toastEl.textContent = msg;
    toastEl.classList.add('on');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toastEl.classList.remove('on'); }, ms || 2600);
  }

  /* ---------- Hero 文案 ---------- */
  (function heroCopy() {
    var lead = $('#hero-lead'), cta = $('#cta-summon');
    if (lead) lead.textContent = (C.hero && C.hero.lead) || FALLBACK.hero.lead;
    if (cta) cta.textContent = (C.hero && C.hero.cta) || FALLBACK.hero.cta;
    var t = $('#hero-title');
    if (t && C.hero && C.hero.line2) {
      t.innerHTML = C.hero.line2.replace(/^(.)/, '$1') + '<em>' + ((C.meta && C.meta.title) || FALLBACK.meta.title) + '</em>';
    }
  })();

  /* ---------- 文化卡片 ---------- */
  (function renderCulture() {
    var box = $('#culture-grid');
    if (!box) return;
    box.innerHTML = (C.culture || []).map(function (c) {
      return '<article class="culture-card">' +
        '<div><span class="no">' + (c.no || '') + '</span><span class="kick">' + (c.kicker || '') + '</span></div>' +
        '<h3>' + (c.title || '') + '</h3>' +
        '<p>' + (c.body || '') + '</p>' +
        '<div class="notes">' + (c.notes || []).map(function (n) { return '<span>' + n + '</span>'; }).join('') + '</div>' +
        '</article>';
    }).join('');
  })();

  /* ---------- 匠人 ---------- */
  (function renderCraft() {
    var box = $('#craft-grid');
    if (!box || !C.craftsmen || !C.craftsmen.length) { if (box) box.parentNode.removeChild(box); return; }
    box.innerHTML = C.craftsmen.map(function (p) {
      return '<article class="craft-card">' +
        '<img class="avatar" src="' + (p.avatar || 'assets/img/phoenix-mark.svg') + '" alt="' + (p.name || '') + '"' +
        ' onerror="this.src=\'assets/img/phoenix-mark.svg\'" width="74" height="74">' +
        '<h3>' + (p.name || '') + '</h3>' +
        '<p class="role">' + (p.role || '') + '</p>' +
        '<blockquote>' + (p.quote || '') + '</blockquote>' +
        '<dl>' + (p.blocks || []).map(function (b) {
          return '<div><dt>' + b.k + '</dt><dd>' + b.v + '</dd></div>';
        }).join('') + '</dl>' +
        '</article>';
    }).join('');
  })();

  /* ---------- 文创（分类筛选） ---------- */
  (function renderMerch() {
    var tabs = $('#merch-tabs'), grid = $('#merch-grid');
    if (!grid || !C.merch || !C.merch.length) { if (grid) grid.parentNode.removeChild(grid); if (tabs) tabs.remove(); return; }
    var tiers = ['全部'];
    C.merch.forEach(function (m) { if (tiers.indexOf(m.tier) < 0) tiers.push(m.tier); });

    tabs.innerHTML = tiers.map(function (t, i) {
      return '<button type="button" role="tab" aria-selected="' + (i === 0) + '" data-tier="' + t + '">' + t + '</button>';
    }).join('');

    function paint(tier) {
      grid.innerHTML = C.merch.filter(function (m) { return tier === '全部' || m.tier === tier; })
        .map(function (m) {
          var img = m.image
            ? '<figure class="merch-shot"><img src="' + m.image + '" alt="' + (m.name || '') + ' 效果图" loading="lazy" width="380" height="380" onerror="this.style.opacity=0"></figure>'
            : '<figure class="merch-shot placeholder"><img src="assets/img/phoenix-mark.svg" alt="" aria-hidden="true"></figure>';
          return '<article class="merch-item">' +
            img +
            '<div class="tier">' + (m.tier || '') + '</div>' +
            '<h3>' + (m.name || '') + '</h3>' +
            '<div class="spec">' + (m.spec || '') + '</div>' +
            '<p>' + (m.desc || '') + '</p>' +
            '</article>';
        }).join('');
    }
    paint('全部');
    tabs.addEventListener('click', function (e) {
      var b = e.target.closest('button[data-tier]');
      if (!b) return;
      $$('button', tabs).forEach(function (x) { x.setAttribute('aria-selected', String(x === b)); });
      paint(b.getAttribute('data-tier'));
    });
  })();

  /* ---------- 路线图 ---------- */
  (function renderRoad() {
    var box = $('#road-grid');
    if (!box || !C.roadmap || !C.roadmap.length) { if (box) box.parentNode.removeChild(box); return; }
    box.innerHTML = C.roadmap.map(function (r) {
      var now = r.status === '当前版本';
      return '<article class="road-item' + (now ? ' now' : '') + '">' +
        '<div class="st">' + (r.status || '') + '</div>' +
        '<h3>' + (r.title || '') + '</h3>' +
        '<p>' + (r.desc || '') + '</p>' +
        '</article>';
    }).join('');
  })();

  /* ---------- 站点 URL 展示 ---------- */
  (function showUrl() {
    var el = $('#site-url');
    if (!el) return;
    var LIVE = 'https://lxh113377.github.io/donggu-phoenix/';
    var local = location.protocol === 'file:' || location.hostname === '127.0.0.1' || location.hostname === 'localhost';
    el.textContent = local ? LIVE : location.href.split('#')[0];
    el.setAttribute('title', LIVE + (local ? '（当前为本地预览）' : ''));
  })();

  /* ---------- 粒子凤凰 ---------- */
  var phoenix = null, stage = $('#stage');
  if (stage && window.Phoenix) {
    phoenix = new window.Phoenix(stage, {
      anchor: document.querySelector('.hero-visual'),
      onReady: function () {
        document.body.classList.add('ready');
        hideBoot();
      },
      onFlight: function () {
        var v = $('#summon-veil'); if (v) v.classList.add('on');
        toast('凤凰已起飞 · 向下阅读它的故事', 3200);
      }
    });
    window.__phoenix = phoenix;
    phoenix.load().catch(function () { hideBoot(); });
    window.addEventListener('resize', function () {
      if (phoenix) { phoenix.isMobile = window.innerWidth < 900; phoenix._resize(); }
    }, { passive: true });
  } else {
    hideBoot();
  }

  function hideBoot() {
    var b = $('#boot');
    if (b) { b.classList.add('done'); setTimeout(function () { b.remove(); }, 900); }
  }
  // 兜底：4 秒后无论如何收起载入层
  setTimeout(hideBoot, 4000);

  function summon(source) {
    if (phoenix && phoenix.particles.length) {
      phoenix.summon();
    } else {
      toast('动画正在准备，稍后再试', 1800);
    }
    if (window.__onSummon) window.__onSummon(source);
  }

  /* ---------- 召唤按钮 / 图腾点击 ---------- */
  document.addEventListener('click', function (e) {
    var t = e.target.closest('#cta-summon, #totem-hit');
    if (!t) return;
    e.preventDefault();
    summon('click');
    if (t.id === 'cta-summon') {
      window.scrollTo({ top: 0, behavior: reduced ? 'auto' : 'smooth' });
    }
  });

  /* ---------- 扫地滚动：nav 实心 + reveal ---------- */
  var nav = $('#nav');
  function onScroll() {
    if (nav) nav.classList.toggle('solid', window.scrollY > 40);
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -8% 0px' });
    $$('.reveal').forEach(function (el) { io.observe(el); });
  } else {
    $$('.reveal').forEach(function (el) { el.classList.add('in'); });
  }

  /* ---------- 摄像头扫描（三级降级） ---------- */
  var cam = $('#cam'), video = $('#cam-video'), camHint = $('#cam-hint'), camClose = $('#cam-close');
  var stream = null, rafId = null, probeCanvas = null, probeCtx = null, scanStart = 0;

  function stopCam() {
    if (rafId) { cancelAnimationFrame(rafId); rafId = null; }
    if (stream) { stream.getTracks().forEach(function (t) { t.stop(); }); stream = null; }
    if (video) video.srcObject = null;
    if (cam) cam.classList.remove('on');
    document.documentElement.style.overflow = '';
  }

  function openCamFallback(reason) {
    stopCam();
    toast(reason || '已切换为「轻触召唤」', 3000);
    summon('fallback');
  }

  /* 真机识别：轻量像素判定 —— 取景框中心的暖色（红/金）占比超过阈值即视为对准图腾 */
  function probe() {
    if (!video || video.readyState < 2) return false;
    var w = 96, h = 96;
    if (!probeCanvas) {
      probeCanvas = document.createElement('canvas');
      probeCanvas.width = w; probeCanvas.height = h;
      probeCtx = probeCanvas.getContext('2d', { willReadFrequently: true });
    }
    try { probeCtx.drawImage(video, 0, 0, w, h); } catch (e) { return false; }
    var d;
    try { d = probeCtx.getImageData(0, 0, w, h).data; } catch (e) { return false; }
    var hit = 0, tot = 0;
    for (var i = 0; i < d.length; i += 4) {
      var r = d[i], g = d[i + 1], b = d[i + 2];
      // 中心区裁剪（取中间 60%）
      var px = (i / 4) % w, py = Math.floor((i / 4) / w);
      if (px < w * 0.2 || px > w * 0.8 || py < h * 0.2 || py > h * 0.8) continue;
      tot++;
      var warm = (r > 90 && r > g * 1.18 && r > b * 1.35) || (r > 150 && g > 110 && b < 110);
      if (warm) hit++;
    }
    return tot > 0 && (hit / tot) > 0.16;
  }

  function scanLoop() {
    rafId = requestAnimationFrame(scanLoop);
    if (probe()) {
      if (camHint) camHint.textContent = '已认出图腾 · 凤凰正在飞来';
      stopCam();
      summon('camera');
      return;
    }
    var sec = (performance.now() - scanStart) / 1000;
    if (camHint && sec > 3.5) camHint.textContent = '把图腾放进取景框中央 · 或点击任意处直接唤凤';
  }

  function startScan() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      openCamFallback('此设备不支持摄像头扫描，已切换为轻触召唤');
      return;
    }
    if (location.protocol !== 'https:' && location.hostname !== 'localhost' && location.protocol !== 'file:') {
      openCamFallback('非安全连接，无法调用摄像头，已切换为轻触召唤');
      return;
    }
    cam.classList.add('on');
    document.documentElement.style.overflow = 'hidden';
    if (camHint) camHint.textContent = '正在请求摄像头…';
    navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: 'environment' } }, audio: false })
      .then(function (s) {
        stream = s;
        video.srcObject = s;
        return video.play().catch(function () {});
      })
      .then(function () {
        if (camHint) camHint.textContent = '把图腾放进取景框中央';
        scanStart = performance.now();
        scanLoop();
      })
      .catch(function (err) {
        var name = (err && err.name) || '';
        var msg = name === 'NotAllowedError' ? '摄像头权限被拒绝，已切换为轻触召唤'
          : name === 'NotFoundError' ? '未找到摄像头，已切换为轻触召唤'
          : '摄像头不可用，已切换为轻触召唤';
        openCamFallback(msg);
      });
  }

  var btnScan = $('#btn-scan');
  if (btnScan) btnScan.addEventListener('click', startScan);
  if (camClose) camClose.addEventListener('click', stopCam);
  if (cam) cam.addEventListener('click', function (e) {
    if (e.target === cam || e.target.classList.contains('guide')) { stopCam(); summon('tap-camera'); }
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') stopCam(); });

  /* ---------- 全局暴露（供自动化验收读取） ---------- */
  window.__site = {
    ready: true,
    version: '1.0.0',
    summon: summon,
    state: function () { return phoenix ? phoenix.state : 'none'; },
    fps: function () { return phoenix ? phoenix.fps : 0; },
    count: function () { return phoenix ? phoenix.particles.length : 0; }
  };
})();
