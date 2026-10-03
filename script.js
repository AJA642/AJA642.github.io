(function () {
  var reveals = document.querySelectorAll('.reveal');
  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  if (reveals.length) {
    if (prefersReducedMotion || !('IntersectionObserver' in window)) {
      reveals.forEach(function (el) { el.classList.add('is-visible'); });
    } else {
      var observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            observer.unobserve(entry.target);
          }
        });
      }, { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });

      reveals.forEach(function (el) { observer.observe(el); });
    }
  }

  // Hero wordmark → nav handoff. The nav bar itself is always visible, but
  // its own wordmark starts hidden — the hero's "Ashish Abraham" line owns
  // that spot on the landing view. Once the hero line scrolls up and out
  // from behind the nav's reserved 56px, the nav's wordmark fades in on
  // the left — and fades back out if the user scrolls back up past that
  // point, so the name never actually leaves the page.
  var navWordmark = document.getElementById('nav-wordmark');
  var heroName = document.getElementById('hero-name');
  if (navWordmark && heroName) {
    if ('IntersectionObserver' in window) {
      var navHeightPx = 56; // matches .g-nav height in styles.css
      var navObserver = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          navWordmark.classList.toggle('is-visible', !entry.isIntersecting);
        });
      }, { rootMargin: '-' + navHeightPx + 'px 0px 0px 0px', threshold: 0 });
      navObserver.observe(heroName);
    } else {
      navWordmark.classList.add('is-visible');
    }
  }

  // Scroll-down cue on the hero — fades out the moment the user scrolls
  // under their own steam (not just once it scrolls past), and comes back
  // if they return to the very top.
  var scrollCue = document.querySelector('.g-scroll-cue');
  if (scrollCue) {
    var cueTicking = false;
    function updateCue() {
      scrollCue.classList.toggle('is-hidden', window.scrollY > 4);
      cueTicking = false;
    }
    window.addEventListener('scroll', function () {
      if (!cueTicking) {
        window.requestAnimationFrame(updateCue);
        cueTicking = true;
      }
    }, { passive: true });
  }

  // Slow, eased in-page scrolling for anchor links (nav, scroll cue, footer)
  // instead of the browser's fast/fixed-duration native smooth scroll.
  var NAV_HEIGHT = 56;
  var SCROLL_DURATION = 950; // ms — eased in-page scroll speed

  function easeInOutCubic(t) {
    return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
  }

  function smoothScrollTo(targetY) {
    var startY = window.scrollY;
    var distance = targetY - startY;
    var startTime = null;

    function step(timestamp) {
      if (startTime === null) startTime = timestamp;
      var elapsed = timestamp - startTime;
      var progress = Math.min(elapsed / SCROLL_DURATION, 1);
      window.scrollTo(0, startY + distance * easeInOutCubic(progress));
      if (progress < 1) {
        window.requestAnimationFrame(step);
      }
    }
    window.requestAnimationFrame(step);
  }

  document.querySelectorAll('a[href^="#"]').forEach(function (link) {
    var id = link.getAttribute('href').slice(1);
    if (!id) return;
    link.addEventListener('click', function (e) {
      var target = document.getElementById(id);
      if (!target) return;
      e.preventDefault();
      var targetY = target.getBoundingClientRect().top + window.scrollY - NAV_HEIGHT + 90;
      targetY = Math.max(0, targetY);
      if (prefersReducedMotion) {
        window.scrollTo(0, targetY);
      } else {
        smoothScrollTo(targetY);
      }
      if (history.pushState) history.pushState(null, '', '#' + id);
    });
  });

  // Case-study "Project Links" dropdown — a single text trigger that
  // reveals the project's GitHub repo (and live dashboard, where one
  // exists) instead of showing them as standing buttons on the page.
  document.querySelectorAll('.g-case-links').forEach(function (wrap) {
    var trigger = wrap.querySelector('.g-case-links-trigger');
    var menu = wrap.querySelector('.g-case-links-menu');
    if (!trigger || !menu) return;

    function closeMenu() {
      wrap.classList.remove('is-open');
      trigger.setAttribute('aria-expanded', 'false');
    }
    function openMenu() {
      wrap.classList.add('is-open');
      trigger.setAttribute('aria-expanded', 'true');
    }

    trigger.addEventListener('click', function (e) {
      e.stopPropagation();
      if (wrap.classList.contains('is-open')) {
        closeMenu();
      } else {
        openMenu();
      }
    });

    document.addEventListener('click', function (e) {
      if (!wrap.contains(e.target)) closeMenu();
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        closeMenu();
        trigger.focus();
      }
    });
  });
})();
