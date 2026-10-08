import './styles.css';
import { $, setSpeed } from './fx.js';
import { PRESETS, MODELS, ROLES } from './config.js';
import { GOAT, LIVE } from './layouts.js';
import { initMap, resetMap } from './map.js';
import { line } from './terminal.js';
import { initStages, resetStages } from './stages.js';
import * as api from './api.js';
import {
  store, renderCfg, renderSimGauges, setLedger, hideBar, resetTiers,
} from './ui.js';
import { runSim, runDemo, tierLabels, SIM_COLUMNS } from './sim.js';
import { renderProject, replay, LIVE_COLUMNS } from './live.js';
import { startAgentMonitor } from './agents.js';

let online = false;
let mode = 'sim';
let saveTimer = null;

// ---------- tier config persistence (api.py → runtime_data/config/tiers.json) ----------
function applyServerTiers(tiers) {
  if (!tiers) return;
  Object.entries(tiers).forEach(([role, t]) => {
    if (store.tiers[role] && MODELS[t.model]) store.tiers[role] = { model: t.model, effort: t.effort };
  });
}

function onTiersChanged() {
  if (mode === 'sim') resetMap(tierLabels());
  if (!online) { $('cfgState').textContent = 'tersimpan di tab ini saja (api.py offline)'; return; }
  clearTimeout(saveTimer);
  $('cfgState').textContent = 'menyimpan…';
  saveTimer = setTimeout(async () => {
    try {
      await api.putConfig(store.tiers);
      $('cfgState').textContent = 'tersimpan ke runtime_data/config/tiers.json';
    } catch (e) {
      $('cfgState').textContent = `gagal menyimpan: ${e.message}`;
    }
  }, 400);
}

// ---------- modes ----------
function setConn(isOnline) {
  online = isOnline;
  const c = $('conn');
  c.classList.toggle('live', isOnline);
  c.textContent = isOnline ? 'api.py terhubung' : 'api.py offline';
  $('modeLive').disabled = !isOnline;
  $('modeLive').title = isOnline ? '' : 'Jalankan: uvicorn api:app --reload';
}

function showMode(next) {
  mode = next;
  document.body.dataset.mode = next;
  $('modeLive').setAttribute('aria-pressed', String(next === 'live'));
  $('modeSim').setAttribute('aria-pressed', String(next === 'sim'));
  document.querySelectorAll('[data-show]').forEach((el) => { el.hidden = el.dataset.show !== next; });
}

async function enterSim() {
  showMode('sim');
  hideBar();
  initMap(GOAT);
  resetMap(tierLabels());
  resetStages();
  setLedger(SIM_COLUMNS, 'Belum ada task. Klik "Demo otomatis" atau pilih contoh.');
  renderSimGauges();
}

async function enterLive() {
  if (!online) return;
  showMode('live');
  initMap(LIVE);
  setLedger(LIVE_COLUMNS, 'Memuat project…');
  let projects = [];
  try { projects = await api.listProjects(); } catch (e) { await line('api', 't-fail', e.message); }
  const sel = $('project');
  sel.innerHTML = '';
  if (!projects.length) {
    sel.innerHTML = '<option value="">Belum ada project</option>';
    setLedger(LIVE_COLUMNS, 'Belum ada project di AI_Output atau runtime_data. Mulai dari python main.py (discovery).');
    resetStages(); hideBar();
    $('replay').disabled = true;
    return;
  }
  projects.forEach((p) => {
    const o = document.createElement('option');
    o.value = p.name;
    const last = [...p.stages].reverse().find((s) => s.status !== 'todo');
    o.textContent = `${p.name}${last ? ` · ${last.key} ${last.status}` : ''}`;
    sel.appendChild(o);
  });
  await loadProject(sel.value);
}

async function loadProject(name) {
  if (!name) return;
  try {
    const d = await api.getProject(name);
    initMap(LIVE);
    renderProject(d);
    $('replay').disabled = !d.routing;
    await line('api', 't-dim', `project ${d.name} dimuat · routing ${d.routing_source ?? 'belum ada'}`);
  } catch (e) {
    await line('api', 't-fail', `gagal memuat ${name}: ${e.message}`);
  }
}

// ---------- wiring ----------
function wire() {
  $('speed').addEventListener('change', (e) => setSpeed(e.target.value));
  $('modeSim').addEventListener('click', () => { if (!store.running && mode !== 'sim') enterSim(); });
  $('modeLive').addEventListener('click', () => { if (!store.running && mode !== 'live') enterLive(); });
  $('project').addEventListener('change', (e) => { if (!store.running) loadProject(e.target.value); });
  $('refresh').addEventListener('click', () => { if (!store.running) enterLive(); });
  $('replay').addEventListener('click', () => replay());

  $('presets').addEventListener('click', (e) => {
    const b = e.target.closest('button[data-p]');
    if (b) runSim(PRESETS[b.dataset.p], b.dataset.p);
  });
  $('auto').addEventListener('click', () => runDemo());
  $('form').addEventListener('submit', (e) => {
    e.preventDefault();
    const v = $('task').value; $('task').value = '';
    runSim(v, null);
  });
  $('cfgReset').addEventListener('click', () => {
    if (store.running) return;
    resetTiers(); renderCfg(onTiersChanged); onTiersChanged();
  });
}

async function boot() {
  initStages();
  wire();
  const isOnline = await api.ping();
  setConn(isOnline);
  if (isOnline) {
    try {
      const cfg = await api.getConfig();
      applyServerTiers(cfg.tiers);
      $('cfgState').textContent = cfg.source === 'saved' ? 'dimuat dari runtime_data/config/tiers.json' : 'default';
    } catch { /* keep defaults */ }
  } else {
    $('cfgState').textContent = 'default · api.py offline';
  }
  renderCfg(onTiersChanged);


  await line('', 't-dim', '# ai-agency · discovery → documentation → routing → execution → delivery → deployment');
  await line('', 't-dim', isOnline
    ? '# Live: pilih project lalu "Replay". Simulasi: coba GOAT tier dengan model pilihan.'
    : '# api.py belum jalan, jadi mode Simulasi. Jalankan: uvicorn api:app --reload');
  await line('', 't-dim', `# ${ROLES.length} tier GOAT bisa diatur di panel "Model per tingkat".`);
  if (isOnline) {
    await enterLive();

    startAgentMonitor({
      isLive: () => mode === 'live',
      selectedProject: () => $('project')?.value ?? '',
    });
  } else {
    await enterSim();
  }
}

boot();
