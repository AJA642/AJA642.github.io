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

  // Mobile nav menu -- hamburger trigger shown only at phone widths
  // (CSS hides it above the 767px breakpoint), revealing a small dropdown
  // with Skills, Contact, and Projects in place of the nav-links row that
  // no longer fits next to the theme toggle on a narrow screen.
  var navMenuTrigger = document.getElementById('nav-menu-trigger');
  var navMenu = document.getElementById('nav-mobile-menu');
  var navHeader = document.querySelector('.g-nav');
  if (navMenuTrigger && navMenu && navHeader) {
    function closeNavMenu() {
      navHeader.classList.remove('is-menu-open');
      navMenuTrigger.setAttribute('aria-expanded', 'false');
      navMenu.setAttribute('aria-hidden', 'true');
    }
    function openNavMenu() {
      navHeader.classList.add('is-menu-open');
      navMenuTrigger.setAttribute('aria-expanded', 'true');
      navMenu.setAttribute('aria-hidden', 'false');
    }

    navMenuTrigger.addEventListener('click', function (e) {
      e.stopPropagation();
      if (navHeader.classList.contains('is-menu-open')) {
        closeNavMenu();
      } else {
        openNavMenu();
      }
    });

    navMenu.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', closeNavMenu);
    });

    document.addEventListener('click', function (e) {
      if (!navHeader.contains(e.target)) closeNavMenu();
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        closeNavMenu();
        navMenuTrigger.focus();
      }
    });
  }

  // Theme toggle — flips html[data-theme] between the default (dark,
  // no attribute needed) and "light", persists the choice, and keeps
  // the button's aria state and label in sync. The inline script in
  // <head> already applied any stored choice before first paint, so
  // this only needs to wire up the click.
  var themeToggle = document.getElementById('theme-toggle');
  if (themeToggle) {
    var root = document.documentElement;

    function currentTheme() {
      return root.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
    }
    function syncToggle(theme) {
      root.style.colorScheme = theme;
      themeToggle.setAttribute('aria-pressed', theme === 'light' ? 'true' : 'false');
      themeToggle.setAttribute('aria-label', theme === 'light' ? 'Switch to dark theme' : 'Switch to light theme');
    }

    syncToggle(currentTheme());

    themeToggle.addEventListener('click', function () {
      var next = currentTheme() === 'light' ? 'dark' : 'light';
      if (next === 'light') {
        root.setAttribute('data-theme', 'light');
      } else {
        root.removeAttribute('data-theme');
      }
      syncToggle(next);
      try { localStorage.setItem('theme', next); } catch (e) {}
    });
  }
})();
