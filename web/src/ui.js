// Panels around the map: tier config, gauges, memory, ledger, approval bar.
import { $, CSSVAR, isFast } from './fx.js';
import { MODELS, EFFORTS, ROLES, DEFAULT_TIERS, unitCost } from './config.js';

const clone = (o) => JSON.parse(JSON.stringify(o));

export const store = {
  routingMode: 'auto',
  tiers: clone(DEFAULT_TIERS),
  running: false,
  sim: { claude: 0, codex: 0, tasks: 0, esc: 0, saved: 0, reviews: 0, router: 0, naive: 0 },
};

export const vendorOf = (role) => MODELS[store.tiers[role].model].vendor;
export const tierLabel = (role, effort) => {
  const t = store.tiers[role];
  return t.model === 'rules' ? 'aturan · 0 token' : `${MODELS[t.model].short} · ${effort ?? t.effort}`;
};
export const tierCost = (role, effort) => unitCost(MODELS, store.tiers[role].model, effort ?? store.tiers[role].effort);
export const resetTiers = () => { store.tiers = clone(DEFAULT_TIERS); };

// ---------- busy lock ----------
export function setBusy(b) {
  store.running = b;
  document.querySelectorAll('[data-lock]').forEach((x) => { x.disabled = b; });
  document.querySelectorAll('#cfg select').forEach((x) => {
    if (x.dataset.routingMode !== undefined) {
      x.disabled = b;
      return;
    }

    x.disabled = b || store.routingMode === 'auto';
  });
}

// ---------- tier config panel ----------
export function renderCfg(onChange) {
  const box = $('cfg');
  box.innerHTML = '';

  const modeBox = document.createElement('div');
  modeBox.className = 'role';
  modeBox.innerHTML = `
    <h3>Routing Mode</h3>
    <select
      id="routingMode"
      data-routing-mode
      aria-label="Routing mode"
    >
      <option value="auto">AUTO · GOAT adaptive</option>
      <option value="manual">MANUAL · tier override</option>
    </select>
    <div class="hint">
      ${
        store.routingMode === 'auto'
          ? 'GOAT memilih provider, model, dan effort berdasarkan domain + risk. Tier di bawah hanya preset/reference.'
          : 'Pilihan model dan effort per tier menjadi authoritative untuk runtime routing.'
      }
    </div>
  `;

  modeBox.querySelector('[data-routing-mode]').value =
    store.routingMode;

  box.appendChild(modeBox);

  const group = (vendor) => Object.entries(MODELS).filter(([, m]) => m.vendor === vendor)
    .map(([id, m]) => `<option value="${id}">${m.name}</option>`).join('');
  ROLES.forEach((r) => {
    const t = store.tiers[r.key];
    const v = MODELS[t.model].vendor;
    let hint = r.desc, warn = false;
    if (r.key === 'review' && v === vendorOf('deep')) { hint = 'sebaiknya beda vendor dari Deep biar blind spot-nya beda'; warn = true; }
    if (r.key === 'esc' && MODELS[t.model].base <= MODELS[store.tiers.deep.model].base) { hint = 'harus lebih kuat dari Deep'; warn = true; }
    const el = document.createElement('div');
    el.className = 'role';
    el.style.setProperty('--vc', CSSVAR[v]);
    el.innerHTML = `<h3>${r.title}<small>≈${tierCost(r.key)} unit</small></h3>
      <select id="m-${r.key}" aria-label="Model ${r.title}" data-r="${r.key}" data-f="model">
        ${r.key === 'triage' ? '<option value="rules">Aturan keyword (0 token)</option>' : ''}
        <optgroup label="Claude Pro">${group('claude')}</optgroup>
        <optgroup label="ChatGPT Plus · Codex">${group('codex')}</optgroup>
      </select>
      ${t.model === 'rules' ? '' : `<div class="eff"><label for="e-${r.key}">effort</label><select id="e-${r.key}" data-r="${r.key}" data-f="effort">${EFFORTS.map((e) => `<option>${e}</option>`).join('')}</select></div>`}
      <div class="hint${warn ? ' w' : ''}">${hint}</div>`;
    el.querySelector('[data-f="model"]').value = t.model;
    const es = el.querySelector('[data-f="effort"]');
    if (es) es.value = t.effort;
    box.appendChild(el);
  });
  box.querySelectorAll('select').forEach((x) => {
    if (x.dataset.routingMode !== undefined) {
      x.disabled = store.running;
      return;
    }

    x.disabled =
      store.running
      || store.routingMode === 'auto';
  });
  box.onchange = (e) => {
    const s = e.target;

    if (store.running) return;

    if (s.dataset.routingMode !== undefined) {
      store.routingMode = s.value === 'manual'
        ? 'manual'
        : 'auto';

      renderCfg(onChange);
      onChange?.();
      return;
    }

    if (!s.dataset.r) return;

    if (store.routingMode === 'auto') return;

    store.tiers[s.dataset.r][s.dataset.f] = s.value;
    renderCfg(onChange);
    onChange?.();
  };
}

// ---------- animated numbers ----------
const shown = {};
function tween(id, to, fmt) {
  const el = $(id); if (!el) return;
  const from = shown[id] ?? 0; shown[id] = to;
  if (isFast() || from === to) { el.textContent = fmt(to); return; }
  const t0 = performance.now(), d = 700;
  (function f(t) {
    const p = Math.min(1, (t - t0) / d), e = 1 - Math.pow(1 - p, 3);
    el.textContent = fmt(Math.round(from + (to - from) * e));
    if (p < 1) requestAnimationFrame(f);
  })(t0);
}

export function renderSimGauges() {
  const s = store.sim;
  tween('qc', s.claude, (v) => `${v} / 100`); tween('qx', s.codex, (v) => `${v} / 100`);
  $('fc').style.width = `${Math.min(100, s.claude)}%`; $('fxq').style.width = `${Math.min(100, s.codex)}%`;
  tween('cR', s.router, (v) => `${v} unit`); tween('cN', s.naive, (v) => `${v} unit`);
  const mx = Math.max(s.naive, s.router, 1);
  $('bR').style.width = `${(s.router / mx) * 100}%`; $('bN').style.width = `${(s.naive / mx) * 100}%`;
  tween('sTask', s.tasks, (v) => v);
  $('sEsc').textContent = s.tasks ? `${Math.round((s.esc / s.tasks) * 100)}%` : '0%';
  tween('sRev', s.reviews, (v) => v); tween('sSave', s.saved, (v) => v);
}

export function popRatio() {
  const s = store.sim; if (!s.naive || !s.router) return;
  const r = $('ratio');
  r.innerHTML = `${(s.naive / s.router).toFixed(1)}× lebih hemat<small>dibanding model teratas + effort tertinggi untuk semua task</small>`;
  r.classList.remove('pop'); void r.offsetWidth; r.classList.add('pop');
}

export function addMemory(text) {
  const li = document.createElement('li');
  li.className = 'new';
  li.textContent = text;
  $('mem').appendChild(li);
}

// ---------- ledger ----------
export function setLedger(columns, emptyText) {
  $('ledgerHead').innerHTML = `<tr>${columns.map((c) => `<th>${c}</th>`).join('')}</tr>`;
  $('ledger').innerHTML = '';
  const tr = document.createElement('tr'); tr.className = 'empty';
  const td = document.createElement('td'); td.colSpan = columns.length; td.textContent = emptyText;
  tr.appendChild(td); $('ledger').appendChild(tr);
}

// cells: array of string | { pill, cls } | { text, cls }
export function addLedgerRow(cells, { prepend = true, animate = true } = {}) {
  const tb = $('ledger');
  tb.querySelector('.empty')?.remove();
  const tr = document.createElement('tr');
  if (animate) tr.className = 'new';
  cells.forEach((c) => {
    const td = document.createElement('td');
    if (c && typeof c === 'object' && 'pill' in c) {
      const p = document.createElement('span'); p.className = `pill ${c.cls ?? ''}`; p.textContent = c.pill; td.appendChild(p);
    } else if (c && typeof c === 'object') {
      td.textContent = c.text; td.className = c.cls ?? '';
    } else td.textContent = c ?? '';
    tr.appendChild(td);
  });
  prepend ? tb.prepend(tr) : tb.appendChild(tr);
  return tr;
}

// ---------- approval / action bar ----------
export function showBar(text, actions = []) {
  const bar = $('approve');
  bar.innerHTML = '';
  const p = document.createElement('p'); p.textContent = text; bar.appendChild(p);
  actions.forEach((a) => {
    const b = document.createElement('button');
    b.type = 'button'; b.className = `go${a.primary ? ' primary' : ''}`; b.textContent = a.label;
    if (a.lock) b.dataset.lock = '';
    b.addEventListener('click', () => a.onClick(b));
    bar.appendChild(b);
  });
  bar.hidden = false;
}
export const hideBar = () => { $('approve').hidden = true; };

export async function copyText(text, btn) {
  const prev = btn.textContent;
  try { await navigator.clipboard.writeText(text); btn.textContent = 'Tersalin'; }
  catch { btn.textContent = 'Salin manual'; window.prompt?.('Salin perintah:', text); }
  setTimeout(() => { btn.textContent = prev; }, 1500);
}
