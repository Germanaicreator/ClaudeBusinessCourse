/* ─── AI Experts Invoice Dashboard — app.js ──────────────────────────────── */

// ─── MOBILE SIDEBAR ────────────────────────────────────────────────────────
(function () {
  const sidebar  = document.getElementById('sidebar');
  const overlay  = document.getElementById('sidebarOverlay');
  const hamburger = document.getElementById('hamburger');
  if (!sidebar || !hamburger) return;

  function openSidebar() {
    sidebar.classList.add('mobile-open');
    overlay.classList.add('open');
    document.body.style.overflow = 'hidden';
  }
  function closeSidebar() {
    sidebar.classList.remove('mobile-open');
    overlay.classList.remove('open');
    document.body.style.overflow = '';
  }

  hamburger.addEventListener('click', openSidebar);
  overlay.addEventListener('click', closeSidebar);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeSidebar(); });
})();

// ─── MODAL HELPERS ─────────────────────────────────────────────────────────
function openModal(id) {
  const el = document.getElementById(id);
  if (el) {
    el.classList.add('open');
    document.body.style.overflow = 'hidden';
    // Focus first input
    const first = el.querySelector('input:not([readonly]),select,textarea');
    if (first) setTimeout(() => first.focus(), 80);
  }
}
function closeModal(id) {
  const el = document.getElementById(id);
  if (el) {
    el.classList.remove('open');
    document.body.style.overflow = '';
  }
}

// Close modal on backdrop click
document.addEventListener('click', function (e) {
  if (e.target.classList.contains('modal-backdrop')) {
    e.target.classList.remove('open');
    document.body.style.overflow = '';
  }
});

// Close on Escape
document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-backdrop.open').forEach(el => {
      el.classList.remove('open');
      document.body.style.overflow = '';
    });
  }
});

// ─── AUTO-DISMISS FLASH ─────────────────────────────────────────────────────
(function () {
  const flashWrap = document.getElementById('flashWrap');
  if (!flashWrap) return;
  setTimeout(() => {
    flashWrap.querySelectorAll('.flash').forEach(f => {
      f.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
      f.style.opacity    = '0';
      f.style.transform  = 'translateY(-8px)';
      setTimeout(() => f.remove(), 400);
    });
  }, 5000);
})();

// ─── ACTIVE NAV HIGHLIGHT FIX ───────────────────────────────────────────────
// (Handled in Jinja; this just ensures invoice sub-pages highlight correctly)
(function () {
  const path = window.location.pathname;
  document.querySelectorAll('.nav-link').forEach(link => {
    const href = link.getAttribute('href') || '';
    if (href && href !== '/' && path.startsWith(href)) {
      link.classList.add('active');
    }
  });
})();

// ─── FORM HELPERS ──────────────────────────────────────────────────────────
// Show loading state on Finalize button (uses formaction, so we watch for that)
document.addEventListener('click', function (e) {
  const btn = e.target.closest('#btnFinalize');
  if (!btn) return;
  setTimeout(() => {
    btn.textContent = 'Generating PDF…';
    btn.disabled = true;
  }, 10);
});

// ─── NUMBER FORMATTING ─────────────────────────────────────────────────────
function formatCurrency(n) {
  const num = parseFloat(n) || 0;
  return num.toFixed(2)
    .replace(/\B(?=(\d{3})+(?!\d))/g, 'X')
    .replace('.', ',')
    .replace(/X/g, '.')
    + ' €';
}

// ─── TOOLTIP SHIM ─────────────────────────────────────────────────────────
(function () {
  document.querySelectorAll('[title]').forEach(el => {
    el.setAttribute('data-title', el.getAttribute('title'));
  });
})();
