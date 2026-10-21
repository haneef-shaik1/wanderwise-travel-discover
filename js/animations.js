// Scroll-driven behaviour: progress bar, hero parallax, the sticky destination
// showcase, reveal-on-scroll, counters, nav highlighting and the experiences accordion.
// Scrolling itself is never hijacked: we only read scroll position and set CSS variables / classes.
import { $, $$, clamp, prefersReducedMotion } from './utils.js';

const reduced = () => prefersReducedMotion();

/* One shared rAF-throttled scroll loop so every effect reads scroll once per frame. */
const subscribers = new Set();
let ticking = false;
function onScroll() {
  if (ticking) return;
  ticking = true;
  requestAnimationFrame(() => {
    subscribers.forEach((fn) => fn(window.scrollY, window.innerHeight));
    ticking = false;
  });
}
function subscribe(fn) {
  subscribers.add(fn);
  fn(window.scrollY, window.innerHeight);
}

/* ---------- Page progress, header state, hero + CTA parallax ---------- */
function initPageScroll() {
  const bar = $('[data-page-progress]');
  const header = $('[data-header]');
  const hero = $('[data-hero]');
  const bg = $('[data-parallax="bg"]');
  const mist = $$('[data-parallax="mist"]');
  const content = $('[data-parallax="content"]');
  const ctaBg = $('[data-parallax-simple]');
  const cta = ctaBg?.closest('.cta');

  subscribe((y, vh) => {
    const max = document.documentElement.scrollHeight - vh;
    bar.style.transform = `scaleX(${max > 0 ? clamp(y / max, 0, 1) : 0})`;
    header.classList.toggle('is-scrolled', y > 24);

    if (reduced()) return;

    // Hero: layers travel at different speeds (depth illusion) while content fades out.
    if (y < vh * 1.2) {
      bg.style.transform = `translate3d(0, ${y * 0.32}px, 0) scale(${1 + y * 0.00008})`;
      mist.forEach((m, i) => { m.style.transform = `translate3d(0, ${y * (0.12 + i * 0.12)}px, 0)`; });
      content.style.transform = `translate3d(0, ${y * -0.12}px, 0)`;
      content.style.opacity = String(clamp(1 - y / (vh * 0.75), 0, 1));
      hero.classList.toggle('is-past', y > vh * 0.9);
    }

    // Final CTA background drifts slower than the page.
    if (cta) {
      const r = cta.getBoundingClientRect();
      if (r.bottom > 0 && r.top < vh) {
        const p = (vh - r.top) / (vh + r.height);
        ctaBg.style.transform = `translate3d(0, ${(p - 0.5) * -90}px, 0) scale(1.15)`;
      }
    }
  });
}

/* ---------- B. Sticky, scroll-driven destination showcase ---------- */
export function initShowcaseScroll() {
  const track = $('[data-showcase-track]');
  if (!track) return;
  const slides = $$('[data-slide]', track);
  const panels = $$('[data-panel]', track);
  const dots = $$('[data-dot]', track);
  const current = $('[data-current]', track);
  const fill = $('[data-showcase-progress]', track);
  const hint = $('.showcase__hint', track);
  const n = slides.length;
  let active = -1;

  function setActive(i) {
    if (i === active) return;
    active = i;
    slides.forEach((s, k) => {
      s.classList.toggle('is-active', k === i);
      s.classList.toggle('is-past', k < i);
    });
    panels.forEach((p, k) => {
      p.classList.toggle('is-active', k === i);
      p.classList.toggle('is-past', k < i);
      p.classList.toggle('is-next', k > i);
      if (k === i) p.removeAttribute('inert'); else p.setAttribute('inert', '');
    });
    dots.forEach((d, k) => {
      d.classList.toggle('is-active', k === i);
      if (k === i) d.setAttribute('aria-current', 'true'); else d.removeAttribute('aria-current');
    });
    current.textContent = String(i + 1).padStart(2, '0');
  }

  subscribe((y, vh) => {
    if (!track.offsetParent) return; // hidden (mobile / reduced-motion layout)
    const rect = track.getBoundingClientRect();
    if (rect.bottom < -vh || rect.top > vh * 2) return;
    const total = Math.max(1, rect.height - vh);
    const progress = clamp(-rect.top / total, 0, 1);
    const pos = progress * n;
    setActive(Math.min(n - 1, Math.floor(pos)));

    // Continuous parallax inside each slide: image drifts as its "turn" passes.
    slides.forEach((s, k) => {
      const rel = clamp(pos - k - 0.5, -1.2, 1.2); // -0.5 .. 0.5 while active
      s.style.setProperty('--shift', (rel * -70).toFixed(1));
    });
    fill.style.transform = `scaleX(${progress})`;
    if (hint) hint.classList.toggle('is-hidden', progress > 0.04);
  });

  dots.forEach((dot) => dot.addEventListener('click', () => {
    const i = Number(dot.dataset.dot);
    const top = track.getBoundingClientRect().top + window.scrollY;
    const total = track.offsetHeight - window.innerHeight;
    window.scrollTo({ top: top + ((i + 0.5) / n) * total, behavior: reduced() ? 'auto' : 'smooth' });
  }));
}

/* ---------- Mobile: side-scrolling rows (Discover cards + Explore grid) ---------- */
// CSS does the snapping. This helper highlights the card nearest the centre,
// builds the dots under the row and hides the "Swipe" hint after the first swipe.
function createSwipeRow(row, ui, cardSelector) {
  const hint = ui && $('.swipe-ui__hint', ui);
  const dotBox = ui && $('.swipe-ui__dots', ui);
  let cards = [];
  let dots = [];
  let frame = 0;

  const setCurrent = (i) => {
    cards.forEach((c, k) => c.classList.toggle('is-current', k === i));
    dots.forEach((d, k) => d.classList.toggle('is-active', k === i));
  };
  const update = () => {
    frame = 0;
    if (!cards.length || !row.offsetParent) return; // hidden on large screens
    const centre = row.scrollLeft + row.clientWidth / 2;
    let best = 0;
    let bestDist = Infinity;
    cards.forEach((c, k) => {
      const dist = Math.abs(c.offsetLeft + c.offsetWidth / 2 - centre);
      if (dist < bestDist) { bestDist = dist; best = k; }
    });
    setCurrent(best);
    if (hint) hint.classList.toggle('is-hidden', row.scrollLeft > 24);
  };
  // Call again whenever the cards change (for example after a search or filter).
  const refresh = (reset = false) => {
    cards = $$(cardSelector, row);
    if (reset) row.scrollLeft = 0;
    if (dotBox) {
      dotBox.innerHTML = cards.map(() => '<i></i>').join('');
      dots = $$('i', dotBox);
    }
    if (ui) ui.hidden = cards.length === 0;
    if (hint) hint.classList.remove('is-hidden');
    update();
  };

  row.addEventListener('scroll', () => { if (!frame) frame = requestAnimationFrame(update); }, { passive: true });
  window.addEventListener('resize', update, { passive: true });
  refresh();
  return { refresh };
}

export function initShowcaseRow() {
  const row = $('.showcase-list');
  if (row) createSwipeRow(row, $('#showcase-mount .swipe-ui'), '.story');
}

let gridRow;
export function initGridRow() {
  const row = $('#destination-grid');
  if (row) gridRow = createSwipeRow(row, $('[data-grid-swipe]'), '.card');
}
export function refreshGridRow() { gridRow?.refresh(true); }

/* ---------- Reveal on scroll (IntersectionObserver) ---------- */
let revealObserver;
export function observeReveals(root = document) {
  const targets = $$('[data-reveal]:not(.is-visible), .card:not(.is-visible), .wish-card:not(.is-visible)', root);
  if (reduced() || !('IntersectionObserver' in window)) {
    targets.forEach((t) => t.classList.add('is-visible'));
    return;
  }
  revealObserver ||= new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      if (e.isIntersecting) {
        e.target.classList.add('is-visible');
        revealObserver.unobserve(e.target);
      }
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -6% 0px' });
  targets.forEach((t) => revealObserver.observe(t));
}

/* ---------- Counters ---------- */
export function initCounters(values = {}) {
  $$('[data-count-source]').forEach((el) => {
    if (values[el.dataset.countSource] != null) el.dataset.count = values[el.dataset.countSource];
  });
  const els = $$('[data-count]');
  const run = (el) => {
    const end = Number(el.dataset.count) || 0;
    if (reduced() || end === 0) { el.textContent = end; return; }
    const start = performance.now();
    const dur = 1100;
    const step = (t) => {
      const p = clamp((t - start) / dur, 0, 1);
      el.textContent = Math.round(end * (1 - Math.pow(1 - p, 3)));
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  };
  const io = new IntersectionObserver((entries) => entries.forEach((e) => {
    if (e.isIntersecting) { run(e.target); io.unobserve(e.target); }
  }), { threshold: 0.6 });
  els.forEach((el) => io.observe(el));
}

/* ---------- Experiences accordion ---------- */
function initExperiences() {
  const items = $$('[data-exp]');
  const activate = (item) => {
    items.forEach((it) => {
      const on = it === item;
      it.classList.toggle('is-active', on);
      $('.exp__trigger', it).setAttribute('aria-expanded', String(on));
    });
  };
  items.forEach((it) => {
    $('.exp__trigger', it).addEventListener('click', () => activate(it));
    it.addEventListener('mouseenter', () => { if (window.matchMedia('(hover: hover) and (min-width: 861px)').matches) activate(it); });
  });
}

/* ---------- Header: mobile menu + active section link ---------- */
function initNav() {
  const toggle = $('[data-menu-toggle]');
  const nav = $('[data-nav]');
  const setOpen = (open) => {
    nav.classList.toggle('is-open', open);
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
    document.documentElement.classList.toggle('menu-open', open);
  };
  toggle.addEventListener('click', () => setOpen(!nav.classList.contains('is-open')));
  nav.addEventListener('click', (e) => { if (e.target.closest('a')) setOpen(false); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') setOpen(false); });

  const links = $$('[data-nav-link]');
  const map = new Map(links.map((l) => [l.getAttribute('href').slice(1), l]));
  const io = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      if (!e.isIntersecting) return;
      links.forEach((l) => l.classList.remove('is-current'));
      map.get(e.target.id)?.classList.add('is-current');
    });
  }, { rootMargin: '-45% 0px -50% 0px' });
  map.forEach((_, id) => { const s = document.getElementById(id); if (s) io.observe(s); });
}

export function initAnimations() {
  initPageScroll();
  initNav();
  initExperiences();
  observeReveals();
  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll, { passive: true });
}
