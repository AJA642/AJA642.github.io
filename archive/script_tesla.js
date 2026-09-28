(function () {
  var header = document.querySelector('.t-header');
  if (!header) return;

  function onScroll() {
    header.classList.toggle('t-header--scrolled', window.scrollY > 40);
  }

  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();
})();
