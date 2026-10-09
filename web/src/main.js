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
import {
  renderProject,
  renderExecutionSnapshot,
  replay,
  currentProject,
  LIVE_COLUMNS,
} from './live.js';
import { startAgentMonitor } from './agents.js';

let online = false;
let mode = 'sim';
let saveTimer = null;
let billingTimer = null;

// ---------- tier config persistence (api.py → runtime_data/config/tiers.json) ----------
function applyServerTiers(tiers) {
  if (!tiers) return;
  Object.entries(tiers).forEach(([role, t]) => {
    if (store.tiers[role] && MODELS[t.model]) store.tiers[role] = { model: t.model, effort: t.effort };
  });
}

function applyServerConfig(cfg) {
  store.routingMode =
    cfg?.mode === 'manual'
      ? 'manual'
      : 'auto';

  applyServerTiers(cfg?.tiers);
}

function onTiersChanged() {
  if (mode === 'sim') resetMap(tierLabels());
  if (!online) { $('cfgState').textContent = 'tersimpan di tab ini saja (api.py offline)'; return; }
  clearTimeout(saveTimer);
  $('cfgState').textContent = 'menyimpan…';
  saveTimer = setTimeout(async () => {
    try {
      await api.putConfig({
        mode: store.routingMode,
        tiers: store.tiers,
      });

      $('cfgState').textContent =
        `${store.routingMode.toUpperCase()} · tersimpan ke runtime_data/config/tiers.json`;
    } catch (e) {
      $('cfgState').textContent = `gagal menyimpan: ${e.message}`;
    }
  }, 400);
}

// ---------- billing policy persistence ----------

const BILLING_FIELDS = [
  'infrastructure_allocation_usd',
  'subscription_allocation_usd',
  'engineering_service_fee_usd',
  'qa_risk_overhead_percent',
  'margin_percent',
  'minimum_project_fee_usd',
];

function applyBillingConfig(cfg) {
  if (!cfg) return;

  BILLING_FIELDS.forEach((key) => {
    const el = document.querySelector(
      `[data-billing="${key}"]`
    );

    if (el) el.value = cfg[key] ?? '0';
  });
}

function currentBillingConfig() {
  const result = {
    currency: 'USD',
    pricing_basis: 'ai_compute_equivalent_list_reference',
  };

  BILLING_FIELDS.forEach((key) => {
    const el = document.querySelector(
      `[data-billing="${key}"]`
    );

    result[key] = el?.value || '0';
  });

  return result;
}

function onBillingChanged() {
  if (!online) {
    $('billingState').textContent =
      'api.py offline';
    return;
  }

  clearTimeout(billingTimer);

  $('billingState').textContent =
    'menyimpan…';

  billingTimer = setTimeout(async () => {
    try {
      await api.putBillingConfig(
        currentBillingConfig()
      );

      $('billingState').textContent =
        'tersimpan ke runtime_data/config/billing.json';

      const selected = $('project')?.value;
      if (selected && mode === 'live') {
        await loadProject(selected);
      }
    } catch (e) {
      $('billingState').textContent =
        `gagal menyimpan: ${e.message}`;
    }
  }, 400);
}

// ---------- local project intake ----------

let intakeDiscovery = null;
let intakeProjectName = '';

function blockingRequirements(result) {
  return [
    ...(result.inferred ?? []).filter((item) => item.blocking),
    ...(result.unknown ?? []).filter((item) => item.blocking),
  ];
}

function intakeReferences() {
  return $('intakeReferences').value
    .split(/\r?\n/)
    .map((value) => value.trim())
    .filter(Boolean);
}

function renderIntakeResult(payload) {
  const result = payload.discovery;
  const questions = result.questions ?? [];
  const blockers = blockingRequirements(result);

  intakeDiscovery = result;
  intakeProjectName = payload.project_name;

  $('intakeResult').hidden = false;

  const confirmedCount = result.confirmed?.length ?? 0;
  const unknownCount = result.unknown?.length ?? 0;

  $('intakeSummary').textContent =
    `${payload.project_name} · ${result.project_type} · ` +
    `${confirmedCount} confirmed · ${unknownCount} unknown · ` +
    (
      result.ready_for_final_approval
        ? 'ready for final approval'
        : 'butuh konfirmasi'
    );

  const wrap = $('intakeQuestionWrap');
  const list = $('intakeQuestions');
  const approval = $('intakeApprovalWrap');

  list.replaceChildren();

  blockers.forEach((item, index) => {
    const field = document.createElement('label');
    field.className = 'intakequestion';

    const title = document.createElement('span');
    title.textContent =
      questions[index] ??
      item.key.replaceAll('_', ' ');

    const input = document.createElement('textarea');
    input.rows = 2;
    input.dataset.requirementKey = item.key;
    input.placeholder = `Jawaban untuk ${item.key}`;

    if (
      item.value !== null &&
      item.value !== undefined
    ) {
      input.value = Array.isArray(item.value)
        ? item.value.join(', ')
        : String(item.value);
    }

    field.append(title, input);
    list.appendChild(field);
  });

  wrap.hidden =
    result.ready_for_final_approval ||
    blockers.length === 0;

  approval.hidden =
    !result.ready_for_final_approval;
}

async function confirmProjectIntake() {
  if (
    !online ||
    store.running ||
    !intakeDiscovery ||
    !intakeProjectName
  ) {
    return;
  }

  const inputs = [
    ...document.querySelectorAll(
      '#intakeQuestions [data-requirement-key]',
    ),
  ];

  const answers = {};

  for (const input of inputs) {
    const value = input.value.trim();

    if (!value) {
      input.focus();
      $('intakeState').textContent =
        'semua jawaban wajib diisi';
      return;
    }

    answers[input.dataset.requirementKey] = value;
  }

  $('intakeConfirm').disabled = true;
  $('intakeState').textContent =
    'menyimpan konfirmasi…';

  try {
    const payload = await api.confirmProjectIntake(
      intakeProjectName,
      intakeDiscovery,
      answers,
    );

    renderIntakeResult(payload);

    $('intakeState').textContent =
      payload.discovery.ready_for_final_approval
        ? 'discovery lengkap · menunggu approval'
        : 'masih membutuhkan konfirmasi';

    await line(
      'discovery',
      payload.discovery.ready_for_final_approval
        ? 't-pass'
        : 't-warn',
      payload.discovery.ready_for_final_approval
        ? 'semua blocker discovery selesai'
        : 'konfirmasi disimpan',
    );
  } catch (e) {
    $('intakeState').textContent =
      `gagal: ${e.message}`;

    await line(
      'discovery',
      't-fail',
      `konfirmasi gagal: ${e.message}`,
    );
  } finally {
    $('intakeConfirm').disabled = false;
  }
}


function renderIntakeLifecycleState(project) {
  const approval = $('intakeApprovalWrap');

  if (!approval || !project) return;

  const orchestration = project.orchestration ?? {};
  const stages = Object.fromEntries(
    (project.stages ?? []).map((stage) => [
      stage.key,
      stage,
    ]),
  );

  const documentationDone =
    stages.documentation?.status === 'done';

  const routingDone =
    stages.routing?.status === 'done';

  const waitingFor =
    orchestration.waiting_for ?? null;

  const lines = [];

  if (documentationDone) {
    lines.push('Requirement approved ✓');
    lines.push('Documentation complete ✓');
  }

  if (routingDone) {
    const decisions =
      project.routing?.decisions?.length ?? 0;

    lines.push(
      `Routing complete ✓ · ${decisions} task`
    );
  }

  if (
    waitingFor === 'real_execution_approval'
  ) {
    lines.push(
      'Menunggu approval untuk menjalankan agent real.'
    );

    approval.innerHTML = `
      <div class="intakelifecycle">
        <div class="intakelifecyclestate"></div>

        <button
          class="go primary"
          id="intakeExecute"
          type="button"
          data-lock
        >
          Approve & Run Execution
        </button>
      </div>
    `;

    const state = approval.querySelector(
      '.intakelifecyclestate'
    );

    if (state) {
      lines.forEach((text) => {
        const row = document.createElement('div');
        row.textContent = text;
        state.appendChild(row);
      });
    }

    approval.hidden = false;

    $('intakeExecute')?.addEventListener(
      'click',
      async () => {
        if (
          !online ||
          store.running ||
          !project.name
        ) {
          return;
        }

        const button = $('intakeExecute');

        if (button) {
          button.disabled = true;
        }

        $('intakeState').textContent =
          'menjalankan agent real…';

        try {
          await api.executeProject(project.name);

          const updated =
            await api.getProject(project.name);

          renderIntakeLifecycleState(updated);

          $('intakeState').textContent =
            'execution selesai / pipeline diperbarui';

          await enterLive(project.name);
        } catch (e) {
          $('intakeState').textContent =
            `execution gagal: ${e.message}`;

          if (button) {
            button.disabled = false;
          }
        }
      },
    );

    return;
  }

  if (lines.length) {
    approval.innerHTML = `
      <div class="intakelifecycle">
        <div class="intakelifecyclestate"></div>
      </div>
    `;

    const state = approval.querySelector(
      '.intakelifecyclestate'
    );

    if (state) {
      lines.forEach((text) => {
        const row = document.createElement('div');
        row.textContent = text;
        state.appendChild(row);
      });
    }

    approval.hidden = false;
  }
}


async function approveProjectIntake() {
  if (
    !online ||
    store.running ||
    !intakeDiscovery ||
    !intakeProjectName
  ) {
    return;
  }

  if (!intakeDiscovery.ready_for_final_approval) {
    $('intakeState').textContent =
      'discovery belum siap approval';
    return;
  }

  $('intakeApprove').disabled = true;
  $('intakeState').textContent =
    'membuat dokumentasi project…';

  try {
    const payload = await api.approveProjectIntake(
      intakeProjectName,
      intakeDiscovery,
    );

    intakeDiscovery = payload.discovery;

    $('intakeState').textContent =
      `approved · ${payload.generated_docs.length} dokumen dibuat`;

    await line(
      'documentation',
      't-pass',
      `project ${payload.project_name} dibuat · ` +
      `${payload.generated_docs.join(', ')}`,
    );

    const project =
      await api.getProject(payload.project_name);

    renderIntakeLifecycleState(project);

    await enterLive(payload.project_name);
  } catch (e) {
    $('intakeState').textContent =
      `gagal: ${e.message}`;

    await line(
      'documentation',
      't-fail',
      `approval gagal: ${e.message}`,
    );
  } finally {
    $('intakeApprove').disabled = false;
  }
}


async function submitProjectIntake(event) {
  event.preventDefault();

  if (!online || store.running) return;

  const projectName = $('intakeProject').value.trim();
  const brief = $('intakeBrief').value.trim();

  if (!projectName || !brief) return;

  $('intakeSubmit').disabled = true;
  $('intakeState').textContent = 'menganalisis brief…';

  try {
    const payload = await api.analyzeProjectIntake(
      projectName,
      brief,
      intakeReferences(),
    );

    renderIntakeResult(payload);

    $('intakeState').textContent =
      payload.discovery.ready_for_final_approval
        ? 'discovery siap untuk approval'
        : 'discovery membutuhkan konfirmasi';

    await line(
      'discovery',
      payload.discovery.ready_for_final_approval
        ? 't-pass'
        : 't-warn',
      `brief ${payload.project_name} selesai dianalisis`,
    );
  } catch (e) {
    $('intakeState').textContent = `gagal: ${e.message}`;

    await line(
      'discovery',
      't-fail',
      `intake gagal: ${e.message}`,
    );
  } finally {
    $('intakeSubmit').disabled = false;
  }
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

async function enterLive(preferredProject = '') {
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
    const last = [...p.stages].reverse().find(
      (stage) => stage.status !== 'todo',
    );
    o.textContent =
      `${p.name}${last ? ` · ${last.key} ${last.status}` : ''}`;
    sel.appendChild(o);
  });

  if (
    preferredProject &&
    projects.some((project) => project.name === preferredProject)
  ) {
    sel.value = preferredProject;
  }

  await loadProject(sel.value);
}

async function loadProject(name) {
  if (!name) return;
  try {
    const [d, economics] = await Promise.all([
      api.getProject(name),
      api.getEconomics(name),
    ]);

    d.economics = economics;

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

  $('intakeForm')?.addEventListener(
    'submit',
    submitProjectIntake,
  );

  $('intakeConfirm')?.addEventListener(
    'click',
    confirmProjectIntake,
  );

  $('intakeApprove')?.addEventListener(
    'click',
    approveProjectIntake,
  );
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

  $('billingCfg')?.addEventListener(
    'change',
    onBillingChanged,
  );
}

async function boot() {
  initStages();
  wire();
  const isOnline = await api.ping();
  setConn(isOnline);
  if (isOnline) {
    try {
      const cfg = await api.getConfig();
      applyServerConfig(cfg);

      $('cfgState').textContent =
        `${store.routingMode.toUpperCase()} · ${
          cfg.source === 'saved'
            ? 'dimuat dari runtime_data/config/tiers.json'
            : 'default'
        }`;

      const billing = await api.getBillingConfig();
      applyBillingConfig(billing);
      $('billingState').textContent =
        billing.source === 'saved'
          ? 'dimuat dari runtime_data/config/billing.json'
          : 'default';
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
      selectedRunId: () =>
        currentProject()?.execution_run_id ?? '',
      renderHistorical: () =>
        renderExecutionSnapshot(),
    });
  } else {
    await enterSim();
  }
}

boot();
