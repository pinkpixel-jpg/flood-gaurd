(function () {
  var reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var body = document.body;
  var page = body.getAttribute('data-page');
  var hasAnime = typeof anime !== 'undefined';
  var hasGsap = typeof gsap !== 'undefined';
  var hasST = hasGsap && typeof ScrollTrigger !== 'undefined';
  if (hasST) gsap.registerPlugin(ScrollTrigger);

  function initCurtain() {
    var curtain = document.getElementById('curtain');
    if (!curtain) return;
    if (!hasAnime || reduced) {
      curtain.style.display = 'none';
      return;
    }
    curtain.style.display = 'none';
    document.addEventListener('click', function (e) {
      var a = e.target.closest ? e.target.closest('a[href]') : null;
      if (!a) return;
      if (a.classList.contains('no-curtain')) return;
      var href = a.getAttribute('href');
      if (!href || href.charAt(0) === '#' || a.target === '_blank' ||
          e.metaKey || e.ctrlKey || e.shiftKey || a.download) return;
      if (!/\.html($|\?|#)/.test(href) && !/\/$/.test(href)) return;
      if (a.origin !== location.origin) return;
      e.preventDefault();
      curtain.style.display = 'block';
      anime({
        targets: curtain,
        translateY: ['101%', '0%'],
        duration: 480,
        easing: 'easeInQuart',
        complete: function () {
          window.location.href = a.href;
        }
      });
    });
  }

  function initLenis() {
    if (typeof Lenis === 'undefined' || reduced) return;
    var lenis = new Lenis({
      duration: 1.15,
      easing: function (t) { return Math.min(1, 1.001 - Math.pow(2, -10 * t)); },
      smoothWheel: true
    });
    window.__lenis = lenis;
    if (hasST) {
      lenis.on('scroll', ScrollTrigger.update);
      gsap.ticker.add(function (time) { lenis.raf(time * 1000); });
      gsap.ticker.lagSmoothing(0);
    } else {
      function raf(time) {
        lenis.raf(time);
        requestAnimationFrame(raf);
      }
      requestAnimationFrame(raf);
    }
    document.querySelectorAll('a[href^="#"]').forEach(function (a) {
      a.addEventListener('click', function (e) {
        var id = a.getAttribute('href');
        if (id.length < 2) return;
        var el = document.querySelector(id);
        if (!el) return;
        e.preventDefault();
        lenis.scrollTo(el, { offset: -70, duration: 1.4 });
      });
    });
  }

  function initReveals() {
    /* Data-filled panels must NEVER be hidden by reveal animations.
       Exempt anything belonging to the dynamic app layer. */
    document.querySelectorAll(".reveal-block").forEach(function (el) {
      var dynamic = (el.id && el.id.indexOf("fg-") === 0) ||
                    !!el.querySelector('[id^="fg-"]');
      if (dynamic || reduced || !hasST) {
        el.classList.remove("reveal-block");
        el.classList.add("motion-off");
        el.style.opacity = 1;
        el.style.transform = "none";
      }
    });

    var heroBits = document.querySelectorAll('[data-reveal]');
    if (heroBits.length && hasAnime && !reduced) {
      anime({
        targets: '[data-reveal]',
        opacity: [0, 1],
        translateY: [34, 0],
        duration: 900,
        delay: anime.stagger(90, { start: 150 }),
        easing: 'easeOutQuart'
      });
    } else {
      Array.prototype.forEach.call(heroBits, function (el) {
        el.style.opacity = 1;
        el.style.transform = 'none';
      });
    }

    if (!hasST || reduced) {
      document.querySelectorAll('.reveal-block').forEach(function (el) {
        el.classList.add('motion-off');
        el.style.opacity = 1;
        el.style.transform = 'none';
      });
      return;
    }

    gsap.utils.toArray('.reveal-block').forEach(function (el) {
      gsap.fromTo(el,
        { opacity: 0, y: 46 },
        {
          opacity: 1, y: 0, duration: 0.9, ease: 'power3.out',
          scrollTrigger: { trigger: el, start: 'top 82%' }
        });
    });

    gsap.utils.toArray('.chapter').forEach(function (ch) {
      var kids = ch.querySelectorAll('.ch-index, .ch-tag, .ch-rule, .ch-note, .ch-body h2, .ch-body p, .ch-points li, .ch-link');
      gsap.fromTo(kids,
        { opacity: 0, y: 30 },
        {
          opacity: 1, y: 0, duration: 0.75, ease: 'power3.out', stagger: 0.06,
          scrollTrigger: { trigger: ch, start: 'top 78%' }
        });
    });

    var gaugeFills = document.querySelectorAll('.gauge-fill');
    gaugeFills.forEach(function (f) {
      var target = f.style.width;
      f.style.width = '0%';
      ScrollTrigger.create({
        trigger: f,
        start: 'top 92%',
        once: true,
        onEnter: function () {
          f.style.width = target;
        }
      });
    });

    var dayCols = document.querySelectorAll('.day-col');
    if (dayCols.length) {
      gsap.fromTo(dayCols,
        { scaleY: 0 },
        {
          scaleY: 1, duration: 0.85, ease: 'power3.out', stagger: 0.07,
          scrollTrigger: { trigger: '.chart-days', start: 'top 85%' }
        });
    }

    var routeRows = document.querySelectorAll('.route-row');
    if (routeRows.length) {
      gsap.fromTo(routeRows,
        { opacity: 0, x: -26 },
        {
          opacity: 1, x: 0, duration: 0.6, ease: 'power2.out', stagger: 0.08,
          scrollTrigger: { trigger: '.route-table', start: 'top 85%' }
        });
    }

    var tlItems = document.querySelectorAll('.tl-item');
    if (tlItems.length) {
      gsap.fromTo(tlItems,
        { opacity: 0, y: 40 },
        {
          opacity: 1, y: 0, duration: 0.8, ease: 'power3.out', stagger: 0.12,
          scrollTrigger: { trigger: '.timeline', start: 'top 80%' }
        });
    }
  }

  function initCounters() {
    var nums = document.querySelectorAll('[data-count]');
    nums.forEach(function (el) {
      var end = parseFloat(el.getAttribute('data-count'));
      var decimals = (el.getAttribute('data-decimals') | 0);
      var suffix = el.getAttribute('data-suffix') || '';
      if (!hasGsap || reduced) {
        el.textContent = end.toFixed(decimals) + suffix;
        return;
      }
      var obj = { v: 0 };
      gsap.to(obj, {
        v: end, duration: 1.6, ease: 'power2.out',
        scrollTrigger: { trigger: el, start: 'top 90%', once: true },
        onUpdate: function () { el.textContent = obj.v.toFixed(decimals) + suffix; }
      });
    });
  }

  function initToast() {
    var toast = document.getElementById('toast');
    if (!toast) return;
    window.showToast = function (msg) {
      toast.textContent = msg;
      toast.classList.add('show');
      clearTimeout(toast._t);
      toast._t = setTimeout(function () { toast.classList.remove('show'); }, 3200);
    };
    document.querySelectorAll('form[data-demo]').forEach(function (form) {
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        if (window.showToast) showToast(form.getAttribute('data-demo') || 'Saved (demo)');
        form.reset();
      });
    });
  }

  function initClock() {
    var clocks = document.querySelectorAll('#clock, .js-clock');
    if (!clocks.length) return;
    function tick() {
      var now = new Date();
      var s = now.toLocaleTimeString('en-IN', { hour12: false });
      clocks.forEach(function (c) { c.textContent = s + ' IST'; });
    }
    tick();
    setInterval(tick, 1000);
  }

  document.addEventListener('DOMContentLoaded', function () {
    initCurtain();
    initLenis();
    initReveals();
    initCounters();
    initToast();
    initClock();
    var yr = document.querySelectorAll('.js-year');
    yr.forEach(function (y) { y.textContent = new Date().getFullYear(); });
  });
})();
