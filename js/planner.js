// Trip planner: itinerary, estimated budget and LocalStorage persistence.
import { $, storage, toast, escapeHtml, formatMoney, formatBudgetRange, imgHTML } from './utils.js';

const KEY = 'wanderwise.itinerary';
let destinations = [];
const state = { items: [], date: '', travelers: 2, budget: '' };

const byId = (id) => destinations.find((d) => d.id === Number(id));

function save(silent = true) {
  const ok = storage.set(KEY, state);
  const status = $('#plan-status');
  if (status) {
    status.textContent = ok
      ? `Saved on this device at ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}.`
      : 'Could not save: your browser is blocking LocalStorage.';
  }
  if (!silent) toast(ok ? 'Itinerary saved on this device' : 'Saving is blocked in this browser');
}

// Pure calculation, exported so it can be tested.
export function calculate(items, travelers) {
  const t = Math.max(1, Number(travelers) || 1);
  const minPP = items.reduce((s, d) => s + d.budgetMin, 0);
  const maxPP = items.reduce((s, d) => s + d.budgetMax, 0);
  const midPP = (minPP + maxPP) / 2;
  return { travelers: t, minPP, maxPP, midPP, min: minPP * t, max: maxPP * t, total: midPP * t };
}

function render() {
  const items = state.items.map(byId).filter(Boolean);
  const list = $('#itinerary-list');
  list.innerHTML = items.map((d, i) => `
    <li class="itinerary__item">
      <span class="itinerary__num">${i + 1}</span>
      <div class="itinerary__thumb">${imgHTML(d)}</div>
      <div class="itinerary__info">
        <strong>${escapeHtml(d.name)}</strong>
        <span>${escapeHtml(d.country)} · ${formatBudgetRange(d)} est. / person</span>
      </div>
      <button type="button" class="icon-btn" data-plan-remove="${d.id}" aria-label="Remove ${escapeHtml(d.name)} from itinerary">
        <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
      </button>
    </li>`).join('');
  $('#itinerary-empty').hidden = items.length > 0;

  const summary = $('#plan-summary');
  summary.hidden = items.length === 0;
  refreshSelect();
  if (!items.length) return;

  const c = calculate(items, state.travelers);
  $('#sum-pp').textContent = formatMoney(c.midPP);
  $('#sum-travelers').textContent = c.travelers;
  $('#sum-total').textContent = formatMoney(c.total);
  $('#sum-range').textContent = `${formatMoney(c.min)} – ${formatMoney(c.max)}`;

  const budgetEl = $('#sum-budget');
  const budget = Number(state.budget);
  if (budget > 0) {
    const diff = budget - c.total;
    budgetEl.hidden = false;
    budgetEl.className = `summary__budget ${diff >= 0 ? 'is-ok' : 'is-over'}`;
    budgetEl.textContent = diff >= 0
      ? `Within your budget, with about ${formatMoney(diff)} to spare.`
      : `About ${formatMoney(-diff)} over your budget. Consider fewer stops or a different season.`;
  } else {
    budgetEl.hidden = true;
  }

  const dateEl = $('#sum-date');
  if (state.date) {
    const when = new Date(`${state.date}T00:00:00`);
    const days = Math.ceil((when - new Date().setHours(0, 0, 0, 0)) / 86400000);
    dateEl.hidden = false;
    dateEl.textContent = days > 0
      ? `Departing ${when.toLocaleDateString(undefined, { day: 'numeric', month: 'long', year: 'numeric' })} · ${days} day${days === 1 ? '' : 's'} to go`
      : days === 0 ? 'Departing today' : 'That date has passed. Pick a future date.';
  } else {
    dateEl.hidden = true;
  }
}

function refreshSelect() {
  const sel = $('#plan-destination');
  const current = sel.value;
  sel.innerHTML = destinations.map((d) =>
    `<option value="${d.id}" ${state.items.includes(d.id) ? 'disabled' : ''}>${escapeHtml(d.name)}, ${escapeHtml(d.country)}${state.items.includes(d.id) ? ' (added)' : ''}</option>`).join('');
  const firstFree = destinations.find((d) => !state.items.includes(d.id));
  sel.value = current && !state.items.includes(Number(current)) ? current : (firstFree ? firstFree.id : '');
}

export function addToPlan(id, { scroll = false } = {}) {
  const d = byId(id);
  if (!d) return;
  if (state.items.includes(d.id)) {
    toast(`${d.name} is already in your itinerary`);
  } else {
    state.items.push(d.id);
    toast(`${d.name} added to your itinerary`);
    save();
    render();
  }
  if (scroll) $('#planner')?.scrollIntoView({ behavior: 'smooth' });
}

function removeFromPlan(id) {
  state.items = state.items.filter((x) => x !== Number(id));
  save();
  render();
}

export function initPlanner(list) {
  destinations = list;

  const saved = storage.get(KEY, null);
  if (saved && Array.isArray(saved.items)) {
    state.items = saved.items.map(Number).filter((id) => byId(id));
    state.date = typeof saved.date === 'string' ? saved.date : '';
    state.travelers = Math.min(20, Math.max(1, Number(saved.travelers) || 2));
    state.budget = saved.budget ?? '';
  }

  const date = $('#plan-date');
  const travelers = $('#plan-travelers');
  const budget = $('#plan-budget');
  const now = new Date();
  date.min = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
  date.value = state.date;
  travelers.value = state.travelers;
  budget.value = state.budget;

  $('#planner-form').addEventListener('submit', (e) => e.preventDefault());
  $('#plan-add').addEventListener('click', () => {
    const id = $('#plan-destination').value;
    if (id) addToPlan(id);
    else toast('Every destination is already in your itinerary');
  });
  date.addEventListener('change', () => { state.date = date.value; save(); render(); });
  travelers.addEventListener('input', () => {
    state.travelers = Math.min(20, Math.max(1, Math.floor(Number(travelers.value) || 1)));
    save(); render();
  });
  travelers.addEventListener('blur', () => { travelers.value = state.travelers; });
  budget.addEventListener('input', () => { state.budget = budget.value; save(); render(); });
  $('#plan-save').addEventListener('click', () => save(false));
  $('#plan-clear').addEventListener('click', () => {
    Object.assign(state, { items: [], date: '', travelers: 2, budget: '' });
    date.value = ''; travelers.value = 2; budget.value = '';
    storage.remove(KEY);
    $('#plan-status').textContent = 'Itinerary cleared.';
    render();
    toast('Itinerary cleared');
  });

  document.addEventListener('click', (e) => {
    const add = e.target.closest('[data-plan-add]');
    if (add) { addToPlan(add.dataset.planAdd, { scroll: !!add.closest('dialog') }); return; }
    const rm = e.target.closest('[data-plan-remove]');
    if (rm) removeFromPlan(rm.dataset.planRemove);
  });

  render();
  if (state.items.length) $('#plan-status').textContent = 'Restored your saved itinerary.';
}
