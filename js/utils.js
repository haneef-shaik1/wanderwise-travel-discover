// Small shared helpers: DOM shortcuts, formatting, safe storage, toast.

export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

export const FALLBACK_IMAGE = 'assets/icons/placeholder.svg';

export const clamp = (n, min, max) => Math.min(max, Math.max(min, n));

export function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
}

const inr = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 });

export function formatMoney(amount, currency = 'INR') {
  const symbol = currency === 'INR' ? '₹' : `${currency} `;
  return `${symbol}${inr.format(Math.round(amount))}`;
}

export function formatBudgetRange(d) {
  return `${formatMoney(d.budgetMin, d.currency)} – ${formatMoney(d.budgetMax, d.currency)}`;
}

export const budgetMid = (d) => (d.budgetMin + d.budgetMax) / 2;

export const prefersReducedMotion = () =>
  window.matchMedia('(prefers-reduced-motion: reduce)').matches;

export function debounce(fn, wait = 150) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), wait);
  };
}

// LocalStorage can throw (private mode, blocked storage); never let it break the page.
export const storage = {
  get(key, fallback) {
    try {
      const raw = localStorage.getItem(key);
      return raw === null ? fallback : JSON.parse(raw);
    } catch {
      return fallback;
    }
  },
  set(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch {
      return false;
    }
  },
  remove(key) {
    try { localStorage.removeItem(key); } catch { /* ignore */ }
  },
};

let toastTimer;
export function toast(message) {
  const el = $('#toast');
  if (!el) return;
  el.textContent = message;
  el.classList.remove('is-visible');
  // restart the CSS keyframe animation
  void el.offsetWidth;
  el.classList.add('is-visible');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove('is-visible'), 2600);
}

// Reusable <img> markup with focal position and lazy loading.
export function imgHTML(d, { lazy = true, cls = '' } = {}) {
  return `<img class="${cls}" src="${escapeHtml(d.image)}" alt="${escapeHtml(d.imageAlt || `${d.name}, ${d.country}`)}" style="object-position:${escapeHtml(d.imagePosition || '50% 50%')}"${lazy ? ' loading="lazy"' : ''} decoding="async">`;
}

export const heartIcon = '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M12 21s-7.5-4.6-9.5-9.2C1.1 8.5 3 5 6.4 5c2 0 3.8 1.1 5.6 3.2C13.8 6.1 15.6 5 17.6 5 21 5 22.9 8.5 21.5 11.8 19.5 16.4 12 21 12 21z" stroke-width="1.8" stroke-linejoin="round"/></svg>';
