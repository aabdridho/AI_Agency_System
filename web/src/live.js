// Live mode: shows a real project from api.py and replays its routing plan and
// execution report on the node map. Read-only apart from saving a routing plan.
import { $, sleep } from './fx.js';
import { travel, nodeState, setNodeLabel, resetMap, burstAt, flash } from './map.js';
import { OWNER_NODE, OWNER_VENDOR, OWNER_LABEL } from './layouts.js';
import { line, working, hasLines } from './terminal.js';
import { setStages, setStage } from './stages.js';
import { store, setBusy, setLedger, addLedgerRow, showBar, hideBar, copyText } from './ui.js';
import * as api from './api.js';

export const LIVE_COLUMNS = ['ID', 'Task', 'Kategori', 'Owner', 'Fallback', 'Status', 'Catatan'];

const STATUS_CLS = {
  success: 't-pass', skipped: 't-dim', dry_run: 't-warn', planned: 't-dim',
  failed: 't-fail', running: 't-codex', pending: 't-dim',
};

let current = null;

const recordsById = (d) => Object.fromEntries((d.execution?.records ?? []).map((r) => [r.task_id, r]));
const short = (s, n = 64) => (s && s.length > n ? `${s.slice(0, n - 1)}…` : s ?? '');

function note(rec) {
  if (!rec) return '';
  const parts = [];
  if (rec.escalated) parts.push(`fallback → ${OWNER_LABEL[rec.escalation_owner] ?? rec.escalation_owner}`);
  if (rec.repair_attempted) parts.push(`repair ${rec.repair_succeeded ? '✓' : '✗'} (${OWNER_LABEL[rec.repair_owner] ?? rec.repair_owner ?? '-'})`);
  if (rec.qa_profile) parts.push(`profil ${rec.qa_profile}`);
  if (rec.status === 'failed' && rec.stderr) parts.push(short(rec.stderr.trim().split('\n').pop(), 60));
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
      note(rec),
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
    showBar('Siap dieksekusi. Eksekusi menjalankan Claude Code & Codex di repo klien, jadi dijalankan dari terminal.', [
      cmd('Salin perintah', 'python execute_project.py'),
    ]);
  } else if (st.execution?.status === 'wait') {
    showBar('Eksekusi terakhir masih dry-run. Jalankan mode real dari terminal kalau owner & branch sudah benar.', [
      cmd('Salin perintah', 'python execute_project.py'),
    ]);
  } else if ((d.delivery?.checks ?? []).some((c) => c.blocker_class === 'CLIENT_INPUT_REQUIRED')) {
    showBar(`Butuh input klien. Kirim runtime_data/delivery/${d.name}/client_input_request.md ke klien.`, []);
  } else if (st.deployment?.status === 'wait') {
    showBar('Deploy menunggu approval kamu. Jalankan di terminal lalu ketik DEPLOY untuk konfirmasi.', [
      cmd('Salin perintah', 'python deploy_project.py'),
    ]);
  } else hideBar();
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

export async function replay() {
  const d = current;
  if (!d || store.running || !d.routing) return;
  setBusy(true);
  if (hasLines()) await line('', 't-dim', '─'.repeat(52));
  await line('$', 't-pass', ` replay ${d.name} · ${d.routing.decisions.length} task · ${d.execution ? (d.execution.dry_run ? 'dry-run' : 'real') : 'routing saja'}`);
  setStage('execution', 'active');
  const recs = recordsById(d);
  const rows = [...$('ledger').querySelectorAll('tr')];
  const tally = {};
  for (const [i, dec] of d.routing.decisions.entries()) {
    rows.forEach((r) => r.classList.remove('cur'));
    rows[i]?.classList.add('cur');
    const s = await replayTask(dec, recs[dec.task_id]);
    tally[s] = (tally[s] ?? 0) + 1;
  }
  rows.forEach((r) => r.classList.remove('cur'));
  nodeState('report', 'active'); burstAt('report', tally.failed ? 'fail' : 'pass', 18); flash(!tally.failed);
  nodeState('report', tally.failed ? 'fail' : 'ok');
  await line('done', tally.failed ? 't-fail' : 't-pass',
    `✓ replay selesai · ${Object.entries(tally).map(([k, v]) => `${v} ${k.replace('_', '-')}`).join(' · ')}`);
  setStages(d.stages);
  setBusy(false);
}

export const currentProject = () => current;
