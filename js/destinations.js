// Destination data: loading, validation, immersive showcase markup,
// searchable gallery and the details modal. All content comes from data/destinations.json.
import {
  $, $$, escapeHtml, formatBudgetRange, budgetMid, imgHTML, debounce, toast,
} from './utils.js';
import { favButton } from './wishlist.js';
import { observeReveals, refreshGridRow } from './animations.js';

export const DATA_URL = 'data/destinations.json';
const REQUIRED_STRINGS = ['name', 'country', 'category', 'shortDescription', 'description', 'image', 'bestTimeToVisit'];
const REQUIRED_LISTS = ['highlights', 'activities', 'travelTips'];

let all = [];
export const getById = (id) => all.find((d) => d.id === Number(id));

/* ---------- loading & validation ---------- */

function isValid(d) {
  return d && typeof d === 'object'
    && Number.isFinite(Number(d.id))
    && REQUIRED_STRINGS.every((k) => typeof d[k] === 'string' && d[k].trim())
    && REQUIRED_LISTS.every((k) => Array.isArray(d[k]))
    && Number.isFinite(d.budgetMin) && Number.isFinite(d.budgetMax) && d.budgetMin <= d.budgetMax;
}

export async function loadDestinations() {
  const res = await fetch(DATA_URL, { cache: 'no-cache' });
  if (!res.ok) throw new Error(`Could not load ${DATA_URL} (HTTP ${res.status})`);
  const json = await res.json();
  if (!Array.isArray(json)) throw new Error('destinations.json must contain an array');
  const valid = json.filter((d) => {
    const ok = isValid(d);
    if (!ok) console.warn('Skipping invalid destination record:', d);
    return ok;
  }).map((d) => ({ ...d, id: Number(d.id), currency: d.currency || 'INR' }));
  if (!valid.length) throw new Error('No valid destination records found');
  all = valid;
  return valid;
}

/* ---------- B. Immersive showcase ---------- */

const pad = (n) => String(n).padStart(2, '0');

export function renderShowcase(list) {
  const mount = $('#showcase-mount');
  const n = list.length;

  const slides = list.map((d, i) => `
    <div class="slide" data-slide style="--z:${i + 1}">
      <div class="slide__img">${imgHTML(d, { lazy: i > 1 })}</div>
    </div>`).join('');

  const panels = list.map((d, i) => `
    <article class="panel" data-panel aria-label="${escapeHtml(d.name)}, ${escapeHtml(d.country)}">
      <span class="panel__ghost" aria-hidden="true">${pad(i + 1)}</span>
      <p class="panel__kicker rv" style="--i:0">${pad(i + 1)} — ${escapeHtml(d.category)}</p>
      <h3 class="panel__title rv" style="--i:1">${escapeHtml(d.name)}</h3>
      <p class="panel__country rv" style="--i:2">${escapeHtml(d.country)}</p>
      <p class="panel__desc rv" style="--i:3">${escapeHtml(d.shortDescription)}</p>
      <dl class="panel__stats">
        <div class="rv" style="--i:4"><dt>Category</dt><dd>${escapeHtml(d.category)}</dd></div>
        <div class="rv" style="--i:5"><dt>Best time</dt><dd>${escapeHtml(d.bestTimeToVisit)}</dd></div>
        <div class="rv" style="--i:6"><dt>Budget (est.)</dt><dd>${formatBudgetRange(d)}</dd></div>
      </dl>
      <div class="panel__actions rv" style="--i:7">
        <button class="btn btn--primary" type="button" data-open="${d.id}">Discover Destination</button>
        ${favButton(d, { label: true, cls: 'fav--ghost' })}
      </div>
    </article>`).join('');

  const dots = list.map((d, i) =>
    `<button type="button" class="dot" data-dot="${i}" aria-label="Go to ${escapeHtml(d.name)}"><span>${escapeHtml(d.name)}</span></button>`).join('');

  // Cards used on small screens (side-scrolling row) and with reduced motion (stacked list). No sticky stage.
  const cards = list.map((d, i) => `
    <article class="story" data-reveal>
      <div class="story__img">${imgHTML(d, { lazy: i > 0 })}</div>
      <div class="story__body">
        <p class="panel__kicker">${pad(i + 1)} — ${escapeHtml(d.category)}</p>
        <h3>${escapeHtml(d.name)} <small>${escapeHtml(d.country)}</small></h3>
        <p>${escapeHtml(d.shortDescription)}</p>
        <dl class="panel__stats">
          <div><dt>Best time</dt><dd>${escapeHtml(d.bestTimeToVisit)}</dd></div>
          <div><dt>Budget (est.)</dt><dd>${formatBudgetRange(d)}</dd></div>
        </dl>
        <div class="panel__actions">
          <button class="btn btn--primary" type="button" data-open="${d.id}">Discover Destination</button>
          ${favButton(d, { label: true, cls: 'fav--ghost' })}
        </div>
      </div>
    </article>`).join('');

  mount.innerHTML = `
    <div class="showcase__track" data-showcase-track style="--count:${n}">
      <div class="showcase__sticky">
        <div class="showcase__media" data-slides>${slides}</div>
        <div class="showcase__shade" aria-hidden="true"></div>
        <div class="showcase__ui container">
          <div class="showcase__panels" data-panels>${panels}</div>
          <div class="showcase__counter" aria-hidden="true">
            <span data-current>01</span>
            <span class="showcase__bar"><i data-showcase-progress></i></span>
            <span>${pad(n)}</span>
          </div>
          <nav class="showcase__dots" aria-label="Destinations">${dots}</nav>
          <p class="showcase__hint" aria-hidden="true">Keep scrolling</p>
        </div>
      </div>
    </div>
    <div class="showcase-list container">${cards}</div>
    <div class="swipe-ui" aria-hidden="true">
      <span class="swipe-ui__hint">Swipe</span>
      <div class="swipe-ui__dots">${list.map(() => '<i></i>').join('')}</div>
    </div>`;
}

/* ---------- C. Gallery: search, filter, sort ---------- */

const filters = { query: '', category: 'All', sort: 'name-asc' };

function cardHTML(d) {
  return `
    <article class="card" data-card>
      <div class="card__media">
        ${imgHTML(d)}
        <span class="card__tag">${escapeHtml(d.category)}</span>
        ${favButton(d, { cls: 'card__fav' })}
      </div>
      <div class="card__body">
        <h3 class="card__title">
          <button type="button" class="card__open" data-open="${d.id}" aria-label="Open details for ${escapeHtml(d.name)}, ${escapeHtml(d.country)}">${escapeHtml(d.name)}</button>
        </h3>
        <p class="card__country">${escapeHtml(d.country)}</p>
        <p class="card__text">${escapeHtml(d.shortDescription)}</p>
        <dl class="card__meta">
          <div><dt>Best time</dt><dd>${escapeHtml(d.bestTimeToVisit)}</dd></div>
          <div><dt>Budget (est.)</dt><dd>${formatBudgetRange(d)}</dd></div>
        </dl>
        <button type="button" class="btn btn--small btn--outline card__plan" data-plan-add="${d.id}">Add to plan</button>
      </div>
    </article>`;
}

function applyFilters() {
  const q = filters.query.trim().toLowerCase();
  let list = all.filter((d) => {
    const inCat = filters.category === 'All' || d.category === filters.category;
    const hay = [d.name, d.country, d.category, d.shortDescription, ...d.highlights].join(' ').toLowerCase();
    return inCat && (!q || hay.includes(q));
  });
  const [key, dir] = filters.sort.split('-');
  list = list.sort((a, b) => (key === 'name' ? a.name.localeCompare(b.name) : budgetMid(a) - budgetMid(b)));
  if (dir === 'desc') list.reverse();

  const grid = $('#destination-grid');
  grid.innerHTML = list.map(cardHTML).join('');
  $$('.card', grid).forEach((c, i) => c.style.setProperty('--i', Math.min(i, 8)));
  observeReveals(grid);
  refreshGridRow();          // mobile row: back to the first card, rebuild dots
  $('#empty-state').hidden = list.length > 0;
  grid.hidden = list.length === 0;
  $('#result-count').textContent = `Showing ${list.length} of ${all.length} destinations`;
}

function renderChips() {
  const cats = ['All', ...new Set(all.map((d) => d.category))];
  const box = $('#category-filters');
  box.innerHTML = cats.map((c) =>
    `<button type="button" class="chip" data-chip="${escapeHtml(c)}" aria-pressed="${c === filters.category}">${escapeHtml(c)}</button>`).join('');
}

export function setCategory(cat) {
  filters.category = all.some((d) => d.category === cat) ? cat : 'All';
  filters.query = '';
  $('#search-input').value = '';
  $$('.chip').forEach((c) => c.setAttribute('aria-pressed', String(c.dataset.chip === filters.category)));
  applyFilters();
}

export function initGallery() {
  renderChips();
  applyFilters();

  $('#search-input').addEventListener('input', debounce((e) => { filters.query = e.target.value; applyFilters(); }, 120));
  $('#sort-select').addEventListener('change', (e) => { filters.sort = e.target.value; applyFilters(); });
  $('#category-filters').addEventListener('click', (e) => {
    const chip = e.target.closest('[data-chip]');
    if (!chip) return;
    filters.category = chip.dataset.chip;
    $$('.chip').forEach((c) => c.setAttribute('aria-pressed', String(c === chip)));
    applyFilters();
  });
  $('#reset-filters').addEventListener('click', () => {
    filters.query = ''; filters.category = 'All'; filters.sort = 'name-asc';
    $('#search-input').value = ''; $('#sort-select').value = 'name-asc';
    $$('.chip').forEach((c) => c.setAttribute('aria-pressed', String(c.dataset.chip === 'All')));
    applyFilters();
  });
}

/* ---------- D. Details modal ---------- */

let lastFocus = null;

export function openDetails(id) {
  const d = getById(id);
  const dlg = $('#detail-modal');
  if (!d || !dlg) return;
  lastFocus = document.activeElement;
  const li = (items) => items.map((x) => `<li>${escapeHtml(x)}</li>`).join('');

  $('#modal-content').innerHTML = `
    <div class="modal__hero">
      ${imgHTML(d, { lazy: false })}
      <div class="modal__hero-shade"></div>
      <button class="modal__close" type="button" data-close aria-label="Close details">
        <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
      </button>
      <div class="modal__title">
        <span class="card__tag">${escapeHtml(d.category)}</span>
        <h2 id="modal-title">${escapeHtml(d.name)}</h2>
        <p>${escapeHtml(d.country)}</p>
      </div>
    </div>
    <div class="modal__body">
      <p class="modal__desc">${escapeHtml(d.description)}</p>
      <dl class="modal__facts">
        <div><dt>Best time to visit</dt><dd>${escapeHtml(d.bestTimeToVisit)}</dd></div>
        <div><dt>Estimated budget</dt><dd>${formatBudgetRange(d)} <small>per person, indicative</small></dd></div>
        ${d.idealDays ? `<div><dt>Ideal trip length</dt><dd>${escapeHtml(d.idealDays)}</dd></div>` : ''}
        ${d.climate ? `<div><dt>Climate</dt><dd>${escapeHtml(d.climate)}</dd></div>` : ''}
      </dl>
      <div class="modal__cols">
        <section><h3>Popular attractions</h3><ul>${li(d.highlights)}</ul></section>
        <section><h3>Recommended activities</h3><ul>${li(d.activities)}</ul></section>
        <section><h3>Travel tips</h3><ul>${li(d.travelTips)}</ul></section>
      </div>
      <p class="fineprint">Budgets are indicative estimates for roughly a week, excluding international flights. They are not live travel prices.</p>
      <div class="modal__actions">
        ${favButton(d, { label: true, cls: 'fav--solid' })}
        <button class="btn btn--primary" type="button" data-plan-add="${d.id}">Add to plan</button>
      </div>
    </div>`;

  if (!dlg.open) dlg.showModal();
  dlg.scrollTop = 0;
  document.documentElement.classList.add('modal-open');
}

export function initModal() {
  const dlg = $('#detail-modal');
  const close = () => { if (dlg.open) dlg.close(); };

  document.addEventListener('click', (e) => {
    const opener = e.target.closest('[data-open]');
    if (opener) openDetails(opener.dataset.open);
  });
  dlg.addEventListener('click', (e) => {
    // clicking the backdrop (the dialog element itself) or any close / plan button closes it
    if (e.target === dlg || e.target.closest('[data-close]') || e.target.closest('[data-plan-add]')) close();
  });
  dlg.addEventListener('close', () => {
    document.documentElement.classList.remove('modal-open');
    if (lastFocus && document.contains(lastFocus)) lastFocus.focus({ preventScroll: true });
  });
}

export { toast };
