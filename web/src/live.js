// Live mode: shows a real project from api.py and replays its routing plan and
// execution report on the node map. Read-only apart from saving a routing plan.
import { $, sleep } from './fx.js';
import { travel, nodeState, setNodeLabel, resetMap, burstAt, flash } from './map.js';
import { OWNER_NODE, OWNER_VENDOR, OWNER_LABEL } from './layouts.js';
import { line, working, hasLines } from './terminal.js';
import { setStages, setStage } from './stages.js';
import { store, setBusy, setLedger, addLedgerRow, showBar, hideBar, copyText } from './ui.js';
import * as api from './api.js';

export const LIVE_COLUMNS = [
  'ID',
  'Task',
  'Kategori',
  'Owner',
  'Fallback',
  'Status',
  'Tokens',
  'Catatan',
];

const STATUS_CLS = {
  success: 't-pass', skipped: 't-dim', dry_run: 't-warn', planned: 't-dim',
  failed: 't-fail', running: 't-codex', pending: 't-dim',
};

let current = null;

const recordsById = (d) => Object.fromEntries((d.execution?.records ?? []).map((r) => [r.task_id, r]));


const usageForTask = (d, taskId) =>
  (d.usage_records ?? []).filter(
    (row) => row.task_id === taskId,
  );

const usageSummary = (d, dec) => {
  if (dec.primary_owner === 'deterministic_qa') {
    return '0 · deterministic';
  }

  const rows = usageForTask(d, dec.task_id);

  if (!rows.length) return '—';

  let input = 0;
  let cached = 0;
  let cacheWrite = 0;
  let output = 0;
  let reasoning = 0;

  rows.forEach((row) => {
    const m = row.metrics ?? {};

    input += Number(m.input_tokens ?? 0);
    cached += Number(m.cached_input_tokens ?? 0);
    cacheWrite += Number(
      m.cache_write_input_tokens ?? 0
    );
    output += Number(m.output_tokens ?? 0);
    reasoning += Number(
      m.reasoning_output_tokens ?? 0
    );
  });

  const parts = [
    `in ${input.toLocaleString()}`,
  ];

  if (cached) {
    parts.push(
      `cache ${cached.toLocaleString()}`,
    );
  }

  if (cacheWrite) {
    parts.push(
      `write ${cacheWrite.toLocaleString()}`,
    );
  }

  parts.push(
    `out ${output.toLocaleString()}`,
  );

  /*
   * reasoning_output_tokens currently defaults to 0
   * in UsageMetrics when provider telemetry does not
   * distinguish "zero" from "not reported".
   *
   * Therefore do not display an invented zero.
   */
  if (reasoning > 0) {
    parts.push(
      `reason ${reasoning.toLocaleString()}`,
    );
  }

  return parts.join(' · ');
};

const usagePhaseNote = (d, taskId) => {
  const rows = usageForTask(d, taskId);

  if (!rows.length) return '';

  return rows.map((row) => {
    const m = row.metrics ?? {};

    const model =
      m.model
      ?? row.owner
      ?? 'unknown';

    return `${row.phase}: ${model}`;
  }).join(' → ');
};
const short = (s, n = 64) => (s && s.length > n ? `${s.slice(0, n - 1)}…` : s ?? '');

function note(rec, usageNote = '') {
  if (!rec && !usageNote) return '';
  const parts = [];
  if (rec.escalated) parts.push(`fallback → ${OWNER_LABEL[rec.escalation_owner] ?? rec.escalation_owner}`);
  if (rec.repair_attempted) parts.push(`repair ${rec.repair_succeeded ? '✓' : '✗'} (${OWNER_LABEL[rec.repair_owner] ?? rec.repair_owner ?? '-'})`);
  if (rec.qa_profile) parts.push(`profil ${rec.qa_profile}`);
  if (rec.status === 'failed' && rec.stderr) parts.push(short(rec.stderr.trim().split('\n').pop(), 60));
  if (usageNote) parts.push(usageNote);
  return parts.join(' · ');
}

// ---------- static render ----------
export function renderProject(d) {
  current = d;
  setStages(d.stages);
  renderLedger(d);
  renderSummary(d);
  renderEconomics(d.economics);
  renderBar(d);
}

const usd = (value) => {
  if (value === null || value === undefined) return 'UNKNOWN';
  const n = Number(value);
  if (!Number.isFinite(n)) return 'UNKNOWN';

  if (Math.abs(n) < 0.01 && n !== 0) {
    return `$${n.toFixed(6)}`;
  }

  return `$${n.toFixed(2)}`;
};

function renderEconomics(e) {
  const empty = $('econEmpty');
  const data = $('econData');

  if (!e?.available) {
    empty.hidden = false;
    data.hidden = true;
    empty.textContent = e?.reason ?? 'Belum ada telemetry usage untuk project ini.';
    return;
  }

  empty.hidden = true;
  data.hidden = false;

  const cost = e.cost ?? {};
  const savings = e.savings ?? {};
  const billing = e.billing ?? {};

  $('econAi').textContent = usd(
    cost.known_equivalent_cost_usd
  );

  $('econBaseline').textContent = usd(
    savings.baseline_known_equivalent_cost_usd
  );

  const savingUsd = usd(
    savings.estimated_equivalent_savings_usd
  );

  const savingPct =
    savings.estimated_savings_percent !== null &&
    savings.estimated_savings_percent !== undefined
      ? ` · ${savings.estimated_savings_percent}%`
      : '';

  $('econSavings').textContent =
    `${savingUsd}${savingPct}`;

  $('econActual').textContent =
    billing.actual_provider_cost_known
      ? usd(billing.actual_provider_cash_cost_usd)
      : 'UNKNOWN';

  $('econInfra').textContent =
    usd(billing.infrastructure_allocation_usd);

  $('econSubscription').textContent =
    usd(billing.subscription_allocation_usd);

  $('econEngineering').textContent =
    usd(billing.engineering_service_fee_usd);

  $('econQa').textContent =
    usd(billing.qa_risk_overhead_usd);

  $('econMargin').textContent =
    usd(billing.margin_usd);

  $('econClient').textContent =
    usd(billing.final_client_price_usd);

  $('econNote').textContent =
    `AI = equivalent/list reference · GOAT savings = estimated counterfactual · baseline ${savings.baseline_model ?? 'unknown'}`;
}

function renderLedger(d) {
  const decisions = d.routing?.decisions ?? [];
  setLedger(LIVE_COLUMNS, d.routing ? 'task.md belum punya checkbox task.' : 'Belum ada routing plan. Buat docs/task.md lewat discovery + documentation dulu.');
  const recs = recordsById(d);
  decisions.forEach((dec) => {
    const rec = recs[dec.task_id];
    const status = rec?.status ?? 'planned';
    addLedgerRow([
      { text: dec.task_id, cls: 'mono' },
      short(dec.task_text, 56),
      { pill: dec.category, cls: `p-cat-${dec.category}` },
      { text: OWNER_LABEL[dec.primary_owner] ?? dec.primary_owner, cls: `t-${OWNER_VENDOR[dec.primary_owner]}` },
      OWNER_LABEL[dec.fallback_owner] ?? dec.fallback_owner ?? '—',
      { text: status.replace('_', '-'), cls: `mono ${STATUS_CLS[status] ?? ''}` },
      {
        text: usageSummary(d, dec),
        cls: 'mono',
      },
      note(
        rec,
        usagePhaseNote(
          d,
          dec.task_id,
        ),
      ),
    ], { prepend: false, animate: false });
  });
}

function renderSummary(d) {
  const decisions = d.routing?.decisions ?? [];
  const recs = d.execution?.records ?? [];
  const count = (o) => decisions.filter((x) => x.primary_owner === o).length;
  $('lvTasks').textContent = decisions.length;
  $('lvClaude').textContent = count('claude_code');
  $('lvCodex').textContent = count('codex');
  $('lvQa').textContent = count('deterministic_qa');
  $('lvFail').textContent = recs.filter((r) => r.status === 'failed').length;
  $('lvEsc').textContent = recs.filter((r) => r.escalated || r.repair_attempted).length;
  $('lvMode').textContent = !d.execution ? 'belum dijalankan' : d.execution.dry_run ? 'dry-run' : 'real';

  const list = $('lvChecks');
  list.innerHTML = '';
  const checks = (d.delivery?.checks ?? []).filter((c) => c.status !== 'pass');
  if (!d.delivery) list.innerHTML = '<li class="t-dim">Delivery belum dicek (python prepare_delivery.py).</li>';
  else if (!checks.length) list.innerHTML = '<li class="t-pass">Semua delivery check lolos.</li>';
  checks.forEach((c) => {
    const li = document.createElement('li');
    li.className = c.status === 'blocker' ? 't-fail' : 't-warn';
    li.textContent = `${c.status === 'blocker' ? '✗' : '!'} ${c.title}${c.blocker_class ? ` · ${c.blocker_class.replaceAll('_', ' ').toLowerCase()}` : ''}`;
    list.appendChild(li);
  });

  const dep = d.deployment_result ?? d.deployment_plan;
  $('lvDeploy').textContent = dep
    ? `${dep.provider ?? d.deployment_plan?.provider ?? ''} · ${dep.status}${d.deployment_result?.deployment_url ? ` · ${d.deployment_result.deployment_url}` : ''}`
    : 'belum direncanakan';
}

function renderBar(d) {
  const st = Object.fromEntries(d.stages.map((s) => [s.key, s]));
  const cmd = (label, command) => ({ label, onClick: (b) => copyText(command, b) });

  if (d.routing_source === 'preview') {
    showBar('Routing plan ini masih preview dari docs/task.md dan belum disimpan.', [
      { label: 'Simpan routing plan', primary: true, lock: true, onClick: () => saveRouting(d.name) },
    ]);
  } else if (st.routing?.status === 'done' && st.execution?.status === 'todo') {
    showBar(
      'Routing siap. Execution akan menjalankan agent real dan membutuhkan approval eksplisit.',
      [
        {
          label: 'Approve & Run Execution',
          primary: true,
          lock: true,
          onClick: () => executeProject(d.name),
        },
      ],
    );
  } else if (st.execution?.status === 'wait') {
    showBar(
      'Execution menunggu approval atau masih memiliki state pending.',
      [
        {
          label: 'Approve & Run Execution',
          primary: true,
          lock: true,
          onClick: () => executeProject(d.name),
        },
      ],
    );
  } else if ((d.delivery?.checks ?? []).some((c) => c.blocker_class === 'CLIENT_INPUT_REQUIRED')) {
    showBar(`Butuh input klien. Kirim runtime_data/delivery/${d.name}/client_input_request.md ke klien.`, []);
  } else if (st.deployment?.status === 'wait') {
    showBar('Deploy menunggu approval kamu. Jalankan di terminal lalu ketik DEPLOY untuk konfirmasi.', [
      cmd('Salin perintah', 'python deploy_project.py'),
    ]);
  } else hideBar();
}

async function executeProject(name) {
  setBusy(true);

  try {
    await line(
      'execution',
      't-warn',
      `approval diterima · menjalankan pipeline ${name}`,
    );

    const state = await api.executeProject(name);

    await line(
      state.current_stage ?? 'pipeline',
      state.status === 'failed' ? 't-fail' : 't-pass',
      `pipeline berhenti pada ${state.status}` +
      `${state.waiting_for ? ` · ${state.waiting_for}` : ''}`,
    );

    const d = await api.getProject(name);

    try {
      d.economics = await api.getEconomics(name);
    } catch {
      d.economics = {
        available: false,
        reason: 'Economics belum tersedia.',
      };
    }

    renderProject(d);
  } catch (e) {
    await line(
      'execution',
      't-fail',
      `execution gagal: ${e.message}`,
    );

    try {
      const d = await api.getProject(name);

      try {
        d.economics = await api.getEconomics(name);
      } catch {
        d.economics = {
          available: false,
          reason: 'Economics belum tersedia.',
        };
      }

      renderProject(d);
    } catch {
      // Pertahankan tampilan lama jika refresh juga gagal.
    }
  } finally {
    setBusy(false);
  }
}


async function saveRouting(name) {
  setBusy(true);
  try {
    const d = await api.saveRouting(name);
    await line('routing', 't-pass', `routing plan disimpan · ${d.routing.decisions.length} task`);
    renderProject(d);
  } catch (e) {
    await line('routing', 't-fail', `gagal menyimpan: ${e.message}`);
  } finally {
    setBusy(false);
  }
}

// ---------- replay on the map ----------
async function replayTask(dec, rec) {
  const node = OWNER_NODE[dec.primary_owner] ?? 'codex';
  const vendor = OWNER_VENDOR[dec.primary_owner] ?? 'codex';
  const fbNode = OWNER_NODE[dec.fallback_owner];

  resetMap();
  nodeState('task', 'active'); setNodeLabel('task', dec.task_id);
  await sleep(150); nodeState('task', 'ok');
  await travel('task', 'triage', 'rule');
  nodeState('triage', 'active');
  await working('triage', dec.task_id, 't-rule', short(dec.task_text, 70), 350);
  await line('', 't-rule', `         → ${dec.category} (${Math.round(dec.confidence * 100)}%) · ${OWNER_LABEL[dec.primary_owner]}`);
  nodeState('triage', 'ok'); setNodeLabel('triage', dec.category);
  await travel('triage', node, vendor);

  const status = rec?.status ?? 'planned';
  nodeState(node, 'active', vendor);

  if (!rec) {
    setNodeLabel(node, 'planned');
    await line('plan', 't-dim', 'belum dieksekusi');
    nodeState(node, 'ok');
    return status;
  }

  if (status === 'dry_run') {
    setNodeLabel(node, 'dry-run');
    await working(node, 'dry-run', 't-warn', short(rec.command_preview, 80) || rec.branch, 500);
    nodeState(node, 'ok');
    await travel(node, node === 'qa' ? 'report' : 'integ', 'warn');
    return status;
  }

  if (status === 'skipped') {
    setNodeLabel(node, 'sudah merged');
    await line('skip', 't-dim', short(rec.command_preview || rec.stderr, 80));
    nodeState(node, 'ok');
    if (node !== 'qa') await travel(node, 'integ', 'pass');
    return status;
  }

  // Deterministic QA with optional repair loop.
  if (node === 'qa') {
    setNodeLabel('qa', rec.qa_profile ?? 'qa');
    await working('qa', 'qa', 't-rule', short(rec.command_preview, 80) || 'lint · test · build', 650);
    if (rec.initial_qa_failed) {
      nodeState('qa', 'fail');
      await line('', 't-fail', '         QA gagal');
      if (rec.repair_attempted) {
        const rv = OWNER_VENDOR[rec.repair_owner] ?? 'codex';
        await travel('qa', 'esc', 'fail');
        nodeState('esc', 'active', rv); setNodeLabel('esc', `repair · ${OWNER_LABEL[rec.repair_owner] ?? rec.repair_owner}`);
        await working('esc', rv, `t-${rv}`, `perbaiki di ${rec.repair_branch ?? 'branch repair'}`, 700);
        nodeState('esc', rec.repair_succeeded ? 'ok' : 'fail');
        await travel('esc', 'qa', rv);
        nodeState('qa', 'active');
        await working('qa', 'qa', 't-rule', 'jalankan ulang QA', 500);
      }
    }
    if (status === 'success') {
      nodeState('qa', 'ok'); await line('', 't-pass', '         QA ✓');
      await travel('qa', 'report', 'pass');
    } else {
      nodeState('qa', 'fail'); await line('', 't-fail', `         ${short(rec.stderr || rec.stdout || 'QA gagal', 90)}`);
    }
    return status;
  }

  // Implementation task (Claude Code / Codex) with bounded fallback.
  setNodeLabel(node, rec.branch ? short(rec.branch, 22) : OWNER_LABEL[dec.primary_owner]);
  await working(node, vendor, `t-${vendor}`, `${OWNER_LABEL[dec.primary_owner]} mengerjakan task`, 700);
  if (rec.escalated && fbNode) {
    const fv = OWNER_VENDOR[rec.escalation_owner ?? dec.fallback_owner];
    nodeState(node, 'fail');
    await line('', 't-fail', '         gagal di owner utama');
    await travel(node, 'esc', 'fail');
    nodeState('esc', 'active', fv); setNodeLabel('esc', `→ ${OWNER_LABEL[rec.escalation_owner ?? dec.fallback_owner]}`);
    await working('esc', fv, `t-${fv}`, `fallback ke ${OWNER_LABEL[rec.escalation_owner ?? dec.fallback_owner]}`, 700);
    if (status === 'success') {
      nodeState('esc', 'ok'); await travel('esc', 'integ', fv);
    } else {
      nodeState('esc', 'fail'); await line('', 't-fail', `         ${short(rec.stderr || 'fallback gagal', 90)}`);
      return status;
    }
  } else if (status === 'success') {
    nodeState(node, 'ok'); await travel(node, 'integ', vendor);
  } else {
    nodeState(node, 'fail'); await line('', 't-fail', `         ${short(rec.stderr || 'gagal', 90)}`);
    return status;
  }
  nodeState('integ', 'active'); await sleep(200); nodeState('integ', 'ok');
  await line('', 't-pass', '         merged ke integration');
  return status;
}

// ---------- event-driven execution replay ----------

const decisionForTask = (d, taskId) =>
  (d.routing?.decisions ?? []).find(
    (dec) => dec.task_id === taskId,
  );

const eventVendor = (owner) =>
  OWNER_VENDOR[owner] ?? (
    owner === 'internal_decision'
      ? 'rule'
      : 'warn'
  );

const eventOwnerNode = (owner) =>
  OWNER_NODE[owner] ?? null;

const usageRowsForEvent = (d, event) => {
  if (!event.task_id) return [];

  /*
   * UsageLedger currently records the primary model call
   * under "implementation", while lifecycle events call
   * that stage "primary".
   */
  const phaseMap = {
    primary: 'implementation',
    fallback: 'fallback',
    qa_repair: 'qa_repair',
  };

  const usagePhase =
    phaseMap[event.phase]
    ?? event.phase;

  return (d.usage_records ?? []).filter(
    (row) =>
      row.task_id === event.task_id
      && row.phase === usagePhase,
  );
};

const eventTokenSummary = (d, event) => {
  if (
    event.phase === 'triage'
    || event.phase === 'verify'
    || event.phase === 'integration'
    || event.phase === 'report'
    || event.phase === 'task'
  ) {
    return '0 token · deterministic';
  }

  const rows = usageRowsForEvent(d, event);

  if (!rows.length) return '';

  let input = 0;
  let cached = 0;
  let cacheWrite = 0;
  let output = 0;
  let reasoning = 0;

  rows.forEach((row) => {
    const m = row.metrics ?? {};

    input += Number(m.input_tokens ?? 0);
    cached += Number(
      m.cached_input_tokens ?? 0
    );
    cacheWrite += Number(
      m.cache_write_input_tokens ?? 0
    );
    output += Number(
      m.output_tokens ?? 0
    );
    reasoning += Number(
      m.reasoning_output_tokens ?? 0
    );
  });

  const parts = [
    `in ${input.toLocaleString()}`,
  ];

  if (cached) {
    parts.push(
      `cache ${cached.toLocaleString()}`,
    );
  }

  if (cacheWrite) {
    parts.push(
      `write ${cacheWrite.toLocaleString()}`,
    );
  }

  parts.push(
    `out ${output.toLocaleString()}`,
  );

  /*
   * Do not display zero reasoning tokens as an
   * authoritative provider value because the backend
   * currently cannot distinguish zero from unavailable.
   */
  if (reasoning > 0) {
    parts.push(
      `reason ${reasoning.toLocaleString()}`,
    );
  }

  return parts.join(' · ');
};

const eventStatusClass = (event) => {
  if (event.status === 'failed') {
    return 't-fail';
  }

  if (
    event.status === 'success'
    || event.status === 'info'
  ) {
    return 't-pass';
  }

  if (event.status === 'running') {
    return 't-codex';
  }

  return 't-dim';
};

const eventStatusNode = (status) => {
  if (status === 'failed') return 'fail';

  if (
    status === 'success'
    || status === 'info'
  ) {
    return 'ok';
  }

  return 'active';
};


export function renderExecutionSnapshot(d = current) {
  if (!d) {
    resetMap();
    return false;
  }

  const events = d.execution_events ?? [];

  if (!events.length) {
    resetMap();
    return false;
  }

  resetMap();

  const taskState = new Map();

  events.forEach((event) => {
    const taskId = event.task_id;

    let state = taskId
      ? taskState.get(taskId)
      : null;

    if (taskId && !state) {
      state = {
        primaryNode: null,
        fallbackUsed: false,
      };

      taskState.set(taskId, state);
    }


    if (event.event_type === 'task.created') {
      nodeState(
        'task',
        eventStatusNode(event.status),
        'rule',
      );

      setNodeLabel(
        'task',
        taskId ?? 'task',
      );

      return;
    }


    if (event.event_type === 'triage.completed') {
      const route =
        event.metadata?.route
        ?? event.metadata?.category
        ?? 'classified';

      const risk =
        event.metadata?.risk;

      nodeState(
        'triage',
        eventStatusNode(event.status),
        'rule',
      );

      setNodeLabel(
        'triage',
        risk
          ? `${route} · ${risk}`
          : route,
      );

      return;
    }


    if (
      event.event_type === 'primary.started'
      || event.event_type === 'primary.completed'
    ) {
      const dec =
        decisionForTask(
          d,
          taskId,
        );

      const node =
        eventOwnerNode(event.owner)
        ?? eventOwnerNode(
          dec?.primary_owner,
        );

      if (!node) return;

      const vendor =
        eventVendor(event.owner);

      nodeState(
        node,
        event.event_type === 'primary.started'
          ? 'active'
          : eventStatusNode(event.status),
        vendor,
      );

      const tokens =
        event.event_type === 'primary.completed'
          ? eventTokenSummary(d, event)
          : '';

      setNodeLabel(
        node,
        event.event_type === 'primary.started'
          ? (
            event.model
              ? `${event.model}${event.effort ? ` · ${event.effort}` : ''}`
              : 'running'
          )
          : (
            tokens
              ? `${event.status} · ${tokens}`
              : event.status
          ),
        vendor,
      );

      if (state) {
        state.primaryNode = node;
      }

      return;
    }


    if (
      event.event_type === 'fallback.started'
      || event.event_type === 'fallback.completed'
    ) {
      const vendor =
        eventVendor(event.owner);

      nodeState(
        'esc',
        event.event_type === 'fallback.started'
          ? 'active'
          : eventStatusNode(event.status),
        vendor,
      );

      const tokens =
        event.event_type === 'fallback.completed'
          ? eventTokenSummary(d, event)
          : '';

      setNodeLabel(
        'esc',
        event.event_type === 'fallback.started'
          ? (
            event.model
              ? `${event.model}${event.effort ? ` · ${event.effort}` : ''}`
              : 'fallback'
          )
          : (
            tokens
              ? `${event.status} · ${tokens}`
              : event.status
          ),
        vendor,
      );

      if (state) {
        state.fallbackUsed = true;
      }

      return;
    }


    if (
      event.event_type === 'verify.started'
      || event.event_type === 'verify.completed'
    ) {
      nodeState(
        'qa',
        event.event_type === 'verify.started'
          ? 'active'
          : eventStatusNode(event.status),
        'rule',
      );

      setNodeLabel(
        'qa',
        event.event_type === 'verify.started'
          ? (
            event.detail
            ?? 'deterministic'
          )
          : event.status,
      );

      return;
    }


    if (
      event.event_type ===
      'integration.completed'
    ) {
      nodeState(
        'integ',
        eventStatusNode(event.status),
        'pass',
      );

      setNodeLabel(
        'integ',
        event.metadata?.branch
          ?? event.status,
      );

      return;
    }


    if (
      event.event_type ===
      'report.completed'
    ) {
      const vendor =
        event.status === 'failed'
          ? 'fail'
          : 'pass';

      nodeState(
        'report',
        eventStatusNode(event.status),
        vendor,
      );

      setNodeLabel(
        'report',
        event.status,
      );
    }
  });

  return true;
}

async function replayExecutionEvents(d) {
  const events = d.execution_events ?? [];

  if (!events.length) return false;

  resetMap();

  const taskState = new Map();

  /*
   * events.jsonl is append-only and Dashboard preserves
   * file order. Do not re-sort it here: ledger order is
   * the authoritative execution order.
   */
  for (const event of events) {
    const taskId = event.task_id;
    const dec = taskId
      ? decisionForTask(d, taskId)
      : null;

    let state = taskId
      ? taskState.get(taskId)
      : null;

    if (taskId && !state) {
      state = {
        primaryNode: null,
        lastNode: null,
        fallbackUsed: false,
      };

      taskState.set(taskId, state);
    }

    const tokens =
      eventTokenSummary(d, event);

    if (event.event_type === 'task.created') {
      nodeState('task', 'active');
      setNodeLabel(
        'task',
        taskId ?? 'task',
      );

      await line(
        'task',
        't-rule',
        `${taskId ?? ''} · ${short(event.detail, 80)}`,
      );

      await sleep(100);

      nodeState('task', 'ok');

      if (state) {
        state.lastNode = 'task';
      }

      continue;
    }


    if (event.event_type === 'triage.completed') {
      if (state?.lastNode === 'task') {
        await travel(
          'task',
          'triage',
          'rule',
        );
      }

      nodeState(
        'triage',
        'active',
        'rule',
      );

      const route =
        event.metadata?.route
        ?? dec?.route
        ?? dec?.category
        ?? 'classified';

      const risk =
        event.metadata?.risk;

      setNodeLabel(
        'triage',
        risk
          ? `${route} · ${risk}`
          : route,
      );

      await line(
        'triage',
        't-rule',
        `${taskId ?? ''} → ${route}${risk ? ` · risk ${risk}` : ''} · ${tokens}`,
      );

      nodeState(
        'triage',
        eventStatusNode(event.status),
      );

      if (state) {
        state.lastNode = 'triage';
      }

      continue;
    }


    if (event.event_type === 'primary.started') {
      const node =
        eventOwnerNode(event.owner)
        ?? eventOwnerNode(
          dec?.primary_owner,
        );

      if (!node) {
        await line(
          'primary',
          't-warn',
          `${taskId ?? ''} · owner ${event.owner ?? 'unknown'} tidak punya map node`,
        );

        continue;
      }

      const vendor =
        eventVendor(event.owner);

      if (state?.lastNode === 'triage') {
        await travel(
          'triage',
          node,
          vendor,
        );
      }

      nodeState(
        node,
        'active',
        vendor,
      );

      setNodeLabel(
        node,
        event.model
          ? `${event.model}${event.effort ? ` · ${event.effort}` : ''}`
          : (OWNER_LABEL[event.owner] ?? event.owner ?? 'primary'),
        vendor,
      );

      await line(
        'primary',
        `t-${vendor}`,
        `${taskId ?? ''} · ${OWNER_LABEL[event.owner] ?? event.owner ?? 'owner'} mulai${event.model ? ` · ${event.model}` : ''}`,
      );

      if (state) {
        state.primaryNode = node;
        state.lastNode = node;
      }

      continue;
    }


    if (event.event_type === 'primary.completed') {
      const node =
        state?.primaryNode
        ?? eventOwnerNode(event.owner)
        ?? eventOwnerNode(
          dec?.primary_owner,
        );

      if (node) {
        nodeState(
          node,
          eventStatusNode(event.status),
          eventVendor(event.owner),
        );

        setNodeLabel(
          node,
          event.status,
        );
      }

      await line(
        'primary',
        eventStatusClass(event),
        `${taskId ?? ''} · ${event.status}${tokens ? ` · ${tokens}` : ''}`,
      );

      if (state && node) {
        state.lastNode = node;
      }

      continue;
    }


    if (event.event_type === 'fallback.started') {
      const source =
        state?.primaryNode;

      if (source) {
        await travel(
          source,
          'esc',
          'fail',
        );
      }

      const vendor =
        eventVendor(event.owner);

      nodeState(
        'esc',
        'active',
        vendor,
      );

      setNodeLabel(
        'esc',
        event.model
          ? `${event.model}${event.effort ? ` · ${event.effort}` : ''}`
          : `→ ${OWNER_LABEL[event.owner] ?? event.owner ?? 'fallback'}`,
        vendor,
      );

      await line(
        'fallback',
        `t-${vendor}`,
        `${taskId ?? ''} · fallback → ${OWNER_LABEL[event.owner] ?? event.owner ?? 'unknown'}`,
      );

      if (state) {
        state.fallbackUsed = true;
        state.lastNode = 'esc';
      }

      continue;
    }


    if (event.event_type === 'fallback.completed') {
      nodeState(
        'esc',
        eventStatusNode(event.status),
        eventVendor(event.owner),
      );

      setNodeLabel(
        'esc',
        event.status,
      );

      await line(
        'fallback',
        eventStatusClass(event),
        `${taskId ?? ''} · ${event.status}${tokens ? ` · ${tokens}` : ''}`,
      );

      if (state) {
        state.lastNode = 'esc';
      }

      continue;
    }


    if (event.event_type === 'verify.started') {
      if (state?.lastNode === 'triage') {
        await travel(
          'triage',
          'qa',
          'rule',
        );
      }

      nodeState(
        'qa',
        'active',
        'rule',
      );

      setNodeLabel(
        'qa',
        event.detail
          ?? 'deterministic',
      );

      await line(
        'verify',
        't-rule',
        `${taskId ?? ''} · deterministic QA mulai · ${tokens}`,
      );

      if (state) {
        state.lastNode = 'qa';
      }

      continue;
    }


    if (event.event_type === 'verify.completed') {
      nodeState(
        'qa',
        eventStatusNode(event.status),
        'rule',
      );

      setNodeLabel(
        'qa',
        event.status,
      );

      await line(
        'verify',
        eventStatusClass(event),
        `${taskId ?? ''} · ${event.status} · ${tokens}`,
      );

      if (state) {
        state.lastNode = 'qa';
      }

      continue;
    }


    if (
      event.event_type ===
      'integration.completed'
    ) {
      const source =
        state?.fallbackUsed
          ? 'esc'
          : state?.primaryNode;

      if (source) {
        await travel(
          source,
          'integ',
          'pass',
        );
      }

      nodeState(
        'integ',
        'active',
        'pass',
      );

      setNodeLabel(
        'integ',
        event.metadata?.branch
          ?? 'merged',
      );

      await sleep(120);

      nodeState(
        'integ',
        'ok',
      );

      await line(
        'integration',
        't-pass',
        `${taskId ?? ''} · merged · ${tokens}`,
      );

      if (state) {
        state.lastNode = 'integ';
      }

      continue;
    }


    if (
      event.event_type ===
      'report.completed'
    ) {
      /*
       * Report is project-wide. We do not fabricate an
       * edge from every task into report. Animate only
       * the actual report node.
       */
      nodeState(
        'report',
        'active',
        event.status === 'failed'
          ? 'fail'
          : 'pass',
      );

      setNodeLabel(
        'report',
        event.status,
      );

      await line(
        'report',
        eventStatusClass(event),
        `${event.status} · ${event.metadata?.record_count ?? 0} records · ${tokens}`,
      );

      burstAt(
        'report',
        event.status === 'failed'
          ? 'fail'
          : 'pass',
        18,
      );

      flash(
        event.status !== 'failed',
      );

      nodeState(
        'report',
        eventStatusNode(event.status),
      );

      continue;
    }


    await line(
      'event',
      't-dim',
      `${event.event_type} · ${event.phase} · ${event.status}`,
    );
  }

  return true;
}


export async function replay() {
  const d = current;

  if (
    !d
    || store.running
    || !d.routing
  ) {
    return;
  }

  setBusy(true);

  try {
    if (hasLines()) {
      await line(
        '',
        't-dim',
        '─'.repeat(52),
      );
    }

    const events =
      d.execution_events ?? [];

    if (events.length) {
      await line(
        '$',
        't-pass',
        ` replay ${d.name} · ${events.length} real execution events`,
      );

      setStage(
        'execution',
        'active',
      );

      await replayExecutionEvents(d);

      await line(
        'done',
        't-pass',
        `✓ event replay selesai · ${events.length} event`,
      );

      setStages(d.stages);
      return;
    }

    /*
     * Compatibility path for projects created before
     * execution event ledger existed.
     */
    await line(
      '$',
      't-warn',
      ` replay ${d.name} · legacy execution report`,
    );

    setStage(
      'execution',
      'active',
    );

    const recs =
      recordsById(d);

    const rows = [
      ...$('ledger').querySelectorAll('tr'),
    ];

    const tally = {};

    for (
      const [i, dec]
      of d.routing.decisions.entries()
    ) {
      rows.forEach(
        (r) => r.classList.remove('cur'),
      );

      rows[i]?.classList.add('cur');

      const status =
        await replayTask(
          dec,
          recs[dec.task_id],
        );

      tally[status] =
        (tally[status] ?? 0) + 1;
    }

    rows.forEach(
      (r) => r.classList.remove('cur'),
    );

    nodeState(
      'report',
      'active',
    );

    burstAt(
      'report',
      tally.failed
        ? 'fail'
        : 'pass',
      18,
    );

    flash(
      !tally.failed,
    );

    nodeState(
      'report',
      tally.failed
        ? 'fail'
        : 'ok',
    );

    await line(
      'done',
      tally.failed
        ? 't-fail'
        : 't-pass',
      `✓ legacy replay selesai · ${
        Object.entries(tally)
          .map(
            ([k, v]) =>
              `${v} ${k.replace('_', '-')}`,
          )
          .join(' · ')
      }`,
    );

    setStages(d.stages);
  } finally {
    setBusy(false);
  }
}

export const currentProject = () => current;
