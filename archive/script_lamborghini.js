(function () {
  var openBtn = document.querySelector('.l-nav-menu-btn');
  var closeBtn = document.querySelector('.l-drawer-close');
  var drawer = document.querySelector('.l-drawer');
  if (!openBtn || !drawer) return;

  function open() {
    drawer.classList.add('is-open');
    openBtn.setAttribute('aria-expanded', 'true');
  }
  function close() {
    drawer.classList.remove('is-open');
    openBtn.setAttribute('aria-expanded', 'false');
  }

  openBtn.addEventListener('click', open);
  if (closeBtn) closeBtn.addEventListener('click', close);
  drawer.querySelectorAll('a').forEach(function (a) { a.addEventListener('click', close); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });
})();
