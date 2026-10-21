// WanderWise entry point: loads data, then wires every feature module together.
import { $, $$, FALLBACK_IMAGE, escapeHtml } from './utils.js';
import {
  loadDestinations, renderShowcase, initGallery, initModal, setCategory, DATA_URL,
} from './destinations.js';
import { initWishlist, syncWishlist } from './wishlist.js';
import { initPlanner } from './planner.js';
import { initAnimations, initShowcaseScroll, initShowcaseRow, initGridRow, observeReveals, initCounters } from './animations.js';

// Any image that fails to load gets a local placeholder instead of a broken icon.
document.addEventListener('error', (e) => {
  const img = e.target;
  if (img instanceof HTMLImageElement && !img.dataset.fallback) {
    img.dataset.fallback = '1';
    img.src = FALLBACK_IMAGE;
    img.classList.add('is-fallback');
  }
}, true);

function showError(err) {
  console.error(err);
  const isFile = location.protocol === 'file:';
  const hint = isFile
    ? 'You opened this page directly from your files. Browsers block fetch() on file:// URLs, so start a local server (see README.md) and open http://localhost:8000.'
    : 'Check that data/destinations.json exists and contains valid JSON.';
  const html = `
    <div class="error-box" role="alert">
      <h3>We couldn't load the destinations</h3>
      <p>${escapeHtml(err.message)}</p>
      <p>${hint}</p>
      <button class="btn btn--dark" type="button" data-retry>Try again</button>
    </div>`;
  $('#showcase-mount').innerHTML = `<div class="container">${html}</div>`;
  $('#destination-grid').innerHTML = '';
  $('#result-count').textContent = '';
  $('[data-featured-label]').textContent = 'Unavailable';
}

function wireStaticUI() {
  $$('[data-year]').forEach((el) => { el.textContent = new Date().getFullYear(); });

  // Experience buttons jump to the gallery with that category applied.
  document.addEventListener('click', (e) => {
    const link = e.target.closest('[data-category-link]');
    if (link) {
      setCategory(link.dataset.categoryLink);
      $('#destinations').scrollIntoView({ behavior: 'smooth' });
    }
    if (e.target.closest('[data-retry]')) init();
  });
}

async function init() {
  try {
    const list = await loadDestinations();

    const featured = list.find((d) => d.featured) || list[0];
    $('[data-featured-label]').textContent = `${featured.name}, ${featured.country}`;

    initWishlist(list);        // load favourites first so buttons render in the right state
    renderShowcase(list);
    initGallery();
    initGridRow();
    initModal();
    initPlanner(list);
    initShowcaseScroll();
    initShowcaseRow();
    initCounters({
      destinations: list.length,
      categories: new Set(list.map((d) => d.category)).size,
    });
    observeReveals();
    syncWishlist();            // refresh the wishlist section and badge
  } catch (err) {
    showError(err);
  }
}

wireStaticUI();
initAnimations();
init();
