(function () {
  var body = document.body;
  var page = body.getAttribute('data-page');
  if (page !== 'home') return;

  var reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var hasAnime = typeof anime !== 'undefined';

  function finalizeStatic() {
    body.classList.add('motion-off');
    if (window.FGBG && window.FGBG.setRain) window.FGBG.setRain(reduced ? 0 : 0.7);
    var bg = document.getElementById('bg3d');
    if (bg) bg.style.opacity = 1;
    ['bg-grid', 'bg-contours'].forEach(function (c) {
      var el = document.querySelector('.' + c);
      if (el) el.style.opacity = 1;
    });
    var mists = document.querySelectorAll('.mist');
    for (var i = 0; i < mists.length; i++) mists[i].style.opacity = 1;
    var flash = document.getElementById('waterFlash');
    if (flash) flash.style.opacity = 0;
  }

  if (!hasAnime || reduced) {
    body.classList.add('motion-off');
    window.addEventListener('load', finalizeStatic);
    return;
  }

  var title = document.getElementById('fgTitle');
  if (title && !title.dataset.split) {
    title.dataset.split = '1';
    Array.prototype.forEach.call(title.querySelectorAll('.word'), function (word) {
      var text = word.textContent;
      word.textContent = '';
      text.split('').forEach(function (ch) {
        var s = document.createElement('span');
        s.className = 'char';
        s.textContent = ch;
        word.appendChild(s);
      });
    });
  }

  var waterZone = document.getElementById('waterZone');
  var splashLayer = document.getElementById('splash');
  var rippleLayer = document.getElementById('rippleLayer');

  var RIPPLE_COUNT = 5;
  for (var ri = 0; ri < RIPPLE_COUNT; ri++) {
    var ring = document.createElement('span');
    ring.className = 'ripple' + (ri % 2 ? ' alt' : '');
    rippleLayer.appendChild(ring);
  }

  var SPLASH_COUNT = 22;
  var particles = [];
  for (var si = 0; si < SPLASH_COUNT; si++) {
    var p = document.createElement('span');
    if (Math.random() < 0.3) p.className = 'hot';
    var size = 3 + Math.random() * 4;
    p.style.width = size.toFixed(1) + 'px';
    p.style.height = size.toFixed(1) + 'px';
    splashLayer.appendChild(p);

    var side = Math.random() < 0.5 ? -1 : 1;
    var spread = Math.pow(Math.random(), 0.7);
    var t1 = 260 + Math.random() * 240;
    var t2 = 320 + Math.random() * 380;
    p._dx = side * (26 + spread * 150);
    p._up = (60 + spread * 130) * (size / 7 + 0.45);
    p._down = p._up * (1.3 + Math.random() * 1.2);
    p._rot = side * (90 + Math.random() * 260);
    p._t1 = t1;
    p._t2 = t2;
    p._sq = 0.4 + Math.random() * 0.8;
    particles.push(p);
  }

  var tlStarted = false;

  function buildTimeline() {
    var stage = document.querySelector('.hero-stage');
    var wrap = document.getElementById('dropWrap');
    var waterLine = document.getElementById('waterLine');
    if (!wrap || !waterLine || !stage) return;

    tlStarted = true;
    var sRect = stage.getBoundingClientRect();
    var wRect = waterLine.getBoundingClientRect();
    var dRect = wrap.getBoundingClientRect();
    var baseTop = dRect.top - sRect.top;
    var impactY = (wRect.top - sRect.top) - baseTop - dRect.height * 0.94;
    var driftY = impactY * 0.08;

    var tl = anime.timeline({ autoplay: true });

    tl.add({ targets: '#bg3d', opacity: [0, 1], duration: 900, easing: 'easeOutSine' }, 0)
      .add({ targets: '.bg-grid', opacity: [0, 1], duration: 1400, easing: 'easeOutSine' }, 100)
      .add({ targets: '.bg-contours', opacity: [0, 1], duration: 1600, easing: 'easeOutSine' }, 200)
      .add({ targets: '.mist', opacity: [0, 1], duration: 1800, easing: 'easeOutSine' }, 250);

    if (window.FGBG && window.FGBG.rainState) {
      tl.add({
        targets: window.FGBG.rainState,
        rain: [0, 1],
        duration: 1700,
        easing: 'easeInOutSine'
      }, 300);
    }

    tl.add({
      targets: '#dropWrap',
      opacity: [0, 1],
      scaleX: [0.72, 1],
      scaleY: [0.72, 1],
      duration: 480,
      easing: 'easeOutBack'
    }, 600);

    tl.add({
      targets: '#dropWrap',
      rotate: [
        { value: -8, duration: 400 },
        { value: 6, duration: 480 },
        { value: -4, duration: 420 },
        { value: 0, duration: 300 }
      ],
      easing: 'easeInOutSine'
    }, 900);

    tl.add({
      targets: '#dropWrap',
      translateY: [0, driftY],
      duration: 300,
      easing: 'easeInQuad'
    }, 900);

    tl.add({
      targets: '#dropWrap',
      translateY: [driftY, impactY],
      duration: 1000,
      easing: 'easeInCubic'
    }, 1200);

    tl.add({
      targets: '#dropWrap',
      scaleY: [
        { value: 1.05, duration: 640, easing: 'easeInQuad' },
        { value: 0.97, duration: 360, easing: 'easeOutQuad' }
      ],
      scaleX: [
        { value: 0.98, duration: 640, easing: 'easeInQuad' },
        { value: 1.02, duration: 360, easing: 'easeOutQuad' }
      ]
    }, 1200);

    tl.add({
      targets: '#dropWrap',
      scaleX: [1.02, 1.34],
      scaleY: [0.97, 0.26],
      opacity: [1, 0],
      duration: 180,
      easing: 'easeOutQuad'
    }, 2200);

    tl.add({
      targets: '#waterLine',
      scaleX: [1, 1.07, 1],
      duration: 750,
      easing: 'easeOutCubic'
    }, 2200);

    tl.add({
      targets: '#waterFlash',
      opacity: [
        { value: 0.9, duration: 110, easing: 'easeOutQuad' },
        { value: 0, duration: 560, easing: 'easeInQuad' }
      ]
    }, 2200);

    tl.add({
      targets: '.ripple',
      scale: [0.1, 5],
      opacity: [
        { value: 0.85, duration: 40, easing: 'linear' },
        { value: 0, duration: 1460, easing: 'easeOutCubic' }
      ],
      delay: anime.stagger(115),
      duration: 1500,
      easing: 'easeOutCubic'
    }, 2200);

    particles.forEach(function (p, i) {
      tl.add({
        targets: p,
        translateX: [
          { value: p._dx * 0.65, duration: p._t1, easing: 'easeOutQuad' },
          { value: p._dx, duration: p._t2, easing: 'easeOutQuad' }
        ],
        translateY: [
          { value: -p._up, duration: p._t1, easing: 'easeOutQuad' },
          { value: p._down, duration: p._t2, easing: 'easeInQuad' }
        ],
        scaleX: [1, p._sq],
        scaleY: [1, p._sq],
        rotate: { value: p._rot, duration: p._t1 + p._t2, easing: 'easeOutQuad' },
        opacity: [
          { value: 1, duration: 30, easing: 'linear' },
          { value: 0.9, duration: p._t1 * 0.7, easing: 'linear' },
          { value: 0, duration: p._t2 * 0.8, easing: 'easeInQuad' }
        ]
      }, 2200 + i * 14);
    });

    tl.add({
      targets: '#fgTitle .char',
      opacity: [0, 1],
      translateY: [80, 0],
      scaleX: [0.85, 1],
      scaleY: [0.85, 1],
      duration: 850,
      delay: anime.stagger(42),
      easing: 'easeOutQuart'
    }, 2700);

    tl.add({
      targets: '.word-guard .char',
      color: '#FFD166',
      duration: 430,
      delay: anime.stagger(38),
      easing: 'easeInOutQuad',
      complete: function () {
        var g = document.querySelector('.word-guard');
        if (g) g.classList.add('lit');
      }
    }, 3100);

    tl.add({
      targets: '.tagline',
      opacity: [0, 1],
      translateY: [30, 0],
      duration: 800,
      easing: 'easeOutCubic'
    }, 3500);

    tl.add({
      targets: '.location-line',
      opacity: [0, 1],
      translateY: [22, 0],
      duration: 700,
      easing: 'easeOutCubic'
    }, 3720);

    tl.add({
      targets: ['.site-header .brand', '.site-header .nav-link', '.site-header .nav-cta'],
      opacity: [0, 1],
      translateY: [-20, 0],
      duration: 650,
      delay: anime.stagger(55),
      easing: 'easeOutCubic'
    }, 3900);

    tl.add({
      targets: '.hero-cta-row',
      opacity: [0, 1],
      translateY: [18, 0],
      duration: 750,
      easing: 'easeOutCubic'
    }, 4120);

    tl.add({
      targets: '.scroll-cue',
      opacity: [0, 1],
      duration: 700,
      easing: 'easeOutCubic'
    }, 4260);

    if (window.FGBG && window.FGBG.setRain) {
      setTimeout(function () {
        if (!document.hidden) window.FGBG.setRain(0.75);
      }, 2600);
    }
  }

  if (document.readyState === 'complete') {
    requestAnimationFrame(buildTimeline);
  } else {
    window.addEventListener('load', function () {
      requestAnimationFrame(buildTimeline);
    });
  }

  setTimeout(function () {
    if (tlStarted) return;
    finalizeStatic();
  }, 4500);
})();
