// Wishlist: favourites persisted in LocalStorage.
import { observeReveals } from './animations.js';
import { $, $$, storage, toast, escapeHtml, imgHTML, formatBudgetRange, heartIcon } from './utils.js';

const KEY = 'wanderwise.wishlist';
let destinations = [];
let favs = new Set();

export const isFav = (id) => favs.has(Number(id));

export function favButton(d, { label = false, cls = '' } = {}) {
  const on = isFav(d.id);
  return `<button type="button" class="fav ${cls} ${on ? 'is-on' : ''}" data-fav="${d.id}" data-fav-label="${label ? '1' : ''}"
    aria-pressed="${on}" aria-label="${on ? 'Remove' : 'Save'} ${escapeHtml(d.name)} ${on ? 'from' : 'to'} wishlist">
    ${heartIcon}${label ? `<span>${on ? 'Saved' : 'Save to wishlist'}</span>` : ''}</button>`;
}

function persist() {
  storage.set(KEY, Array.from(favs));
}

export function toggleFav(id) {
  id = Number(id);
  const d = destinations.find((x) => x.id === id);
  if (!d) return;
  if (favs.has(id)) {
    favs.delete(id);
    toast(`${d.name} removed from your wishlist`);
  } else {
    favs.add(id);
    toast(`${d.name} saved to your wishlist`);
  }
  persist();
  sync();
}

// Update every favourite button, the header badge and the wishlist section.
export function syncWishlist() { sync(); }

function sync() {
  $$('[data-fav]').forEach((btn) => {
    const d = destinations.find((x) => x.id === Number(btn.dataset.fav));
    if (!d) return;
    const on = isFav(d.id);
    const wasOn = btn.classList.contains('is-on');
    btn.classList.toggle('is-on', on);
    btn.setAttribute('aria-pressed', String(on));
    btn.setAttribute('aria-label', `${on ? 'Remove' : 'Save'} ${d.name} ${on ? 'from' : 'to'} wishlist`);
    if (btn.dataset.favLabel) btn.querySelector('span').textContent = on ? 'Saved' : 'Save to wishlist';
    if (on && !wasOn) {
      btn.classList.remove('pop');
      void btn.offsetWidth; // restart keyframe
      btn.classList.add('pop');
    }
  });
  const badge = $('[data-wishlist-count]');
  if (badge) {
    badge.textContent = favs.size;
    badge.hidden = favs.size === 0;
  }
  renderWishlist();
}

function renderWishlist() {
  const grid = $('#wishlist-grid');
  const empty = $('#wishlist-empty');
  if (!grid || !empty) return;
  const saved = destinations.filter((d) => favs.has(d.id));
  empty.hidden = saved.length > 0;
  grid.hidden = saved.length === 0;
  grid.innerHTML = saved.map((d) => `
    <article class="wish-card">
      <div class="wish-card__img">${imgHTML(d)}</div>
      <div class="wish-card__body">
        <h3>${escapeHtml(d.name)}</h3>
        <p class="muted">${escapeHtml(d.country)} · ${escapeHtml(d.category)}</p>
        <p class="wish-card__price">${formatBudgetRange(d)} <small>est. / person</small></p>
        <div class="wish-card__actions">
          <button class="btn btn--small btn--dark" type="button" data-open="${d.id}">Details</button>
          <button class="btn btn--small btn--outline" type="button" data-plan-add="${d.id}">Add to plan</button>
          <button class="btn btn--small btn--text" type="button" data-remove-fav="${d.id}" aria-label="Remove ${escapeHtml(d.name)} from wishlist">Remove</button>
        </div>
      </div>
    </article>`).join('');
  observeReveals(grid);
}

let bound = false;

export function initWishlist(list) {
  destinations = list;
  const stored = storage.get(KEY, []);
  favs = new Set((Array.isArray(stored) ? stored : []).map(Number).filter((id) => list.some((d) => d.id === id)));

  if (!bound) {
    bound = true;
    document.addEventListener('click', (e) => {
      const fav = e.target.closest('[data-fav]');
      if (fav) { toggleFav(fav.dataset.fav); return; }
      const rm = e.target.closest('[data-remove-fav]');
      if (rm) toggleFav(rm.dataset.removeFav);
    });
  }
  sync();
}
