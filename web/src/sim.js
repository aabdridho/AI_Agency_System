// Simulasi mode: GOAT tiers with the models chosen in the tier panel.
// Unit costs are illustrative; nothing here calls Claude or Codex.
import { sleep } from './fx.js';
import { MODELS, ROLES, PRESETS, nextEffort } from './config.js';
import { travel, nodeState, setNodeLabel, resetMap, burstAt, flash, floatText } from './map.js';
import { line, working, hasLines } from './terminal.js';
import { setStage, resetStages } from './stages.js';
import {
  store, vendorOf, tierLabel, tierCost, setBusy, renderSimGauges, popRatio, addMemory, addLedgerRow,
} from './ui.js';

const INJECT = /(abaikan|ignore|termahal|most expensive|effort max|pakai opus|pakai fable|bypass)/i;

function triage(t) {
  const s = t.toLowerCase();
  if (/(payment|bayar|midtrans|checkout|auth|login|migrasi|database|keamanan|password)/.test(s)) return { route: 'deep', risk: 'high' };
  if (/(video|naskah|caption|reels|konten|copywriting|storyboard)/.test(s)) return { route: 'create', risk: 'low' };
  if (/(typo|teks|warna|font|judul|gambar|copy)/.test(s)) return { route: 'quick', risk: 'low' };
  return { route: 'build', risk: 'medium' };
}

export function tierLabels() {
  return Object.fromEntries(ROLES.map((r) => [r.key, { text: tierLabel(r.key), vendor: vendorOf(r.key) }]));
}

function spend(role, effort) {
  const t = store.tiers[role], m = MODELS[t.model], n = tierCost(role, effort);
  if (!n) return;
  store.sim[m.vendor] += n;
  store.sim.router += n;
  floatText(role, `+${n} ${m.short}`, m.vendor);
  renderSimGauges();
}

async function doRole(role, task, ms, who, effort) {
  const t = store.tiers[role], m = MODELS[t.model], e = effort ?? t.effort;
  nodeState(role, 'active', m.vendor);
  setNodeLabel(role, `${m.short} · ${e}`);
  await working(role, m.vendor, `t-${m.vendor}`, `${m.name} · ${e} · ${task}`, ms);
  spend(role, e);
  who.push(`${m.short} ${e}`);
}

export async function runSim(text, preset) {
  if (store.running || !text.trim()) return;
  setBusy(true);
  resetMap(tierLabels());
  resetStages();
  setStage('discovery', 'done', 'brief diterima');
  setStage('documentation', 'done', 'spec siap');
  setStage('routing', 'active');

  if (hasLines()) await line('', 't-dim', '─'.repeat(52));
  await line('$', 't-pass', ` goat-router "${text}"`);
  nodeState('task', 'active'); burstAt('task', 'rule'); await sleep(300); nodeState('task', 'ok');
  await travel('task', 'triage', 'rule');
  nodeState('triage', 'active', vendorOf('triage'));

  let clean = text;
  if (INJECT.test(text)) {
    await working('triage', 'triage', 't-rule', 'memindai input…', 600);
    nodeState('triage', 'fail');
    await line('', 't-warn', `         ⚠ "${(text.match(/abaikan.*|ignore.*/i) || [text])[0].trim()}"`);
    await line('', 't-dim', '         input = data, bukan perintah → diabaikan, route tetap dari aturan');
    clean = text.split(/\.\s*/)[0];
    await sleep(350);
    nodeState('triage', 'active', vendorOf('triage'));
  }

  const r = triage(clean);
  const row = { route: r.route === 'create' ? 'creative' : r.route, who: [], esc: 0, c0: store.sim.claude, x0: store.sim.codex };
  let review = false;

  if (store.tiers.triage.model === 'rules') {
    await working('triage', 'triage', 't-rule', 'mencocokkan aturan keyword…', 650);
    await line('', 't-rule', `         → ${JSON.stringify(r)}  (0 token)`);
  } else {
    await doRole('triage', 'klasifikasi task → JSON route', 700, row.who);
    await line('', 't-rule', `         → ${JSON.stringify(r)}`);
  }
  nodeState('triage', 'ok');
  setNodeLabel('triage', `${r.route} · risk ${r.risk}`);
  setStage('routing', 'done', `${r.route} · risk ${r.risk}`);
  setStage('execution', 'active');

  const tier = r.route;
  await travel('triage', tier, vendorOf(tier));

  if (tier === 'quick') {
    await doRole('quick', 'edit index.html, style.css', 1000, row.who);
    await line('', 't-dim', '         diff +4 −4'); nodeState('quick', 'ok');
    await travel('quick', 'check', 'rule'); nodeState('check', 'active');
    await working('check', 'check', 't-rule', 'lint · lighthouse', 750);
    await line('', 't-pass', '         lint ✓   lighthouse 96 ✓'); nodeState('check', 'ok');
    await line('verify', 't-dim', 'dilewati · risk low, cek otomatis sudah PASS');
    await travel('check', 'mem', 'pass');
  }

  if (tier === 'build') {
    await doRole('build', 'kerjakan fitur form kontak', 1100, row.who); nodeState('build', 'ok');
    await travel('build', 'check', 'rule'); nodeState('check', 'active');
    await working('check', 'check', 't-rule', 'npm test · lint', 850);
    if (preset === 'build') {
      nodeState('check', 'fail');
      await line('', 't-fail', '         tests ✗  2 gagal: validasi nomor WA tidak dipanggil');
      await travel('check', 'esc', 'fail');
      nodeState('esc', 'active', 'warn'); setNodeLabel('esc', 'putuskan: effort / model');
      await working('esc', 'esc', 't-warn', 'diagnosis kegagalan…', 600);
      const ne = nextEffort(store.tiers.build.effort);
      await line('', 't-warn', `         validation.js tidak disentuh → naik effort (${store.tiers.build.effort} → ${ne}), model tetap`);
      nodeState('esc', 'ok');
      await travel('esc', 'build', vendorOf('build'));
      await doRole('build', 'retry 1× · effort lebih tinggi', 1100, row.who, ne);
      row.esc = 1; nodeState('build', 'ok');
      await travel('build', 'check', 'rule'); nodeState('check', 'active');
      await working('check', 'check', 't-rule', 'npm test · lint', 750);
      await line('', 't-pass', '         tests ✓ 14/14   lint ✓'); nodeState('check', 'ok');
      await line('verify', 't-dim', 'dilewati · risk medium → sampling 1 dari 5');
      await travel('check', 'mem', 'pass'); nodeState('mem', 'active');
      await line('memory', 't-warn', `+ "form + validasi → build mulai di effort ${ne}"`);
      addMemory(`form + validasi → build effort ${ne}`);
    } else {
      await line('', 't-pass', '         tests ✓   lint ✓'); nodeState('check', 'ok');
      await line('verify', 't-dim', 'dilewati · risk medium → sampling 1 dari 5');
      await travel('check', 'mem', 'pass');
    }
  }

  if (tier === 'deep') {
    await doRole('deep', 'kerjakan payment sesuai spec + acceptance criteria', 1400, row.who); nodeState('deep', 'ok');
    await travel('deep', 'check', 'rule'); nodeState('check', 'active');
    await working('check', 'check', 't-rule', 'tests · typecheck · lint', 850);
    await line('', 't-pass', '         tests ✓ 22/22   typecheck ✓   lint ✓'); nodeState('check', 'ok');
    await travel('check', 'review', vendorOf('review'));
    await doRole('review', 'baca git diff + spec saja (±1 halaman)', 1050, row.who);
    review = true;
    if (preset === 'deep') {
      nodeState('review', 'fail');
      await line('', 't-fail', '         FAIL  signature webhook tidak diverifikasi (test tetap lolos)');
      await travel('review', 'esc', 'fail');
      await line('esc', 't-warn', `konteks lengkap tapi tetap salah → naik model (${MODELS[store.tiers.deep.model].short} → ${MODELS[store.tiers.esc.model].short})`);
      await doRole('esc', 'perbaiki + tambah test verifikasi signature', 1350, row.who);
      row.esc = 1; nodeState('esc', 'ok');
      await travel('esc', 'check', vendorOf('esc')); nodeState('check', 'active');
      await working('check', 'check', 't-rule', 'tests', 750);
      await line('', 't-pass', '         tests ✓ 23/23 (test signature baru)'); nodeState('check', 'ok');
      await line('verify', 't-dim', 'tidak diulang · maksimal 1 putaran, test baru menutup celahnya');
      await travel('check', 'mem', 'pass'); nodeState('mem', 'active');
      await line('memory', 't-warn', '+ "payment → test webhook wajib di spec"');
      addMemory('payment → test webhook wajib di spec');
    } else {
      await line('', 't-pass', '         PASS  sesuai acceptance criteria'); nodeState('review', 'ok');
      await travel('review', 'mem', 'pass');
    }
  }

  if (tier === 'create') {
    await doRole('create', 'naskah + caption dari brief.md', 1250, row.who); nodeState('create', 'ok');
    await travel('create', 'check', 'rule'); nodeState('check', 'active');
    await working('check', 'check', 't-rule', 'script checklist', 750);
    await line('', 't-pass', '         148 kata (≤150) ✓   hook ≤3 detik ✓   CTA ✓'); nodeState('check', 'ok');
    await line('verify', 't-dim', 'dilewati · lu yang approve akhir');
    await travel('check', 'mem', 'pass');
  }

  nodeState('mem', 'active'); nodeState('mem', 'ok'); burstAt('mem', 'pass', 18); flash(true);
  setStage('execution', 'done', row.esc ? `selesai · eskalasi ${row.esc}×` : 'selesai');
  setStage('delivery', 'done', 'checks lolos');
  setStage('deployment', 'wait', 'tunggu approval');

  const s = store.sim;
  s.tasks++; if (row.esc) s.esc++; if (review) s.reviews++;
  const reviewCost = review && vendorOf('review') === 'claude' ? tierCost('review') : 0;
  s.saved += Math.max(0, 6 - reviewCost);
  s.naive += 18;
  const c = s.claude - row.c0, x = s.codex - row.x0;
  renderSimGauges(); popRatio();
  await line('done', 't-pass', `✓ selesai · ${row.route} · eskalasi ${row.esc}× · Claude +${c} · Codex +${x}`);
  addLedgerRow([
    text.length > 48 ? `${text.slice(0, 46)}…` : text,
    { pill: row.route, cls: `p-${row.route}` },
    row.who.join(' → '),
    { text: 'PASS', cls: 'mono t-pass' },
    { text: `${row.esc}×`, cls: 'mono' },
    { text: `+${c}`, cls: 'mono' },
    { text: `+${x}`, cls: 'mono' },
  ]);
  setBusy(false);
}

export async function runDemo() {
  for (const p of ['quick', 'build', 'deep', 'creative', 'attack']) {
    await runSim(PRESETS[p], p);
    await sleep(800);
  }
}

export const SIM_COLUMNS = ['Task', 'Route', 'Dikerjakan oleh', 'Hasil', 'Eskalasi', 'Claude', 'Codex'];
