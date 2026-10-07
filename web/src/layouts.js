// Node-map layouts. Coordinates are in the SVG viewBox (900 × 300).
// W/H = node box size, used by the custom path helpers.
const W = 122, H = 44;

const curve = (A, B) => {
  const x1 = A.x + W / 2, y1 = A.y, x2 = B.x - W / 2, y2 = B.y, m = (x1 + x2) / 2;
  return `M${x1},${y1} C${m},${y1} ${m},${y2} ${x2},${y2}`;
};
const down = (A, B) => `M${A.x},${A.y + H / 2} L${B.x},${B.y - H / 2}`;
const up = (A, B) => `M${A.x},${A.y - H / 2} L${B.x},${B.y + H / 2}`;

// GOAT tiers — used by Simulasi mode.
export const GOAT = {
  name: 'goat',
  label: 'Peta alur GOAT: task, triage, quick, build, deep, kreatif, cek otomatis, verifier, eskalasi, memory',
  nodes: {
    task:   { x: 62,  y: 150, title: 'TASK',         sub: 'brief klien',          vendor: 'rule' },
    triage: { x: 195, y: 150, title: 'TRIAGE',       sub: 'aturan · 0 token',     vendor: 'rule' },
    quick:  { x: 355, y: 45,  title: 'QUICK',        sub: '',                     vendor: 'codex' },
    build:  { x: 355, y: 115, title: 'BUILD',        sub: '',                     vendor: 'codex' },
    deep:   { x: 355, y: 185, title: 'DEEP',         sub: '',                     vendor: 'claude' },
    create: { x: 355, y: 255, title: 'KREATIF',      sub: '',                     vendor: 'claude' },
    check:  { x: 525, y: 150, title: 'CEK OTOMATIS', sub: 'test · lint · script', vendor: 'rule' },
    review: { x: 680, y: 60,  title: 'VERIFIER',     sub: '',                     vendor: 'codex' },
    esc:    { x: 680, y: 240, title: 'ESKALASI',     sub: '',                     vendor: 'codex' },
    mem:    { x: 838, y: 150, title: 'MEMORY',       sub: '+ log',                vendor: 'pass' },
  },
  edges: [
    ['task', 'triage'], ['triage', 'quick'], ['triage', 'build'], ['triage', 'deep'], ['triage', 'create'],
    ['quick', 'check'], ['build', 'check'], ['deep', 'check'], ['create', 'check'],
    ['check', 'review'], ['check', 'mem'], ['review', 'mem'], ['check', 'esc'], ['review', 'esc'],
    ['esc', 'check'], ['esc', 'build'], ['esc', 'mem'],
  ],
  path(a, b, A, B) {
    if (a === 'review' && b === 'esc') return down(A, B);
    if (a === 'esc' && b === 'build') return `M${A.x - W / 2},${A.y + 8} C${A.x - 150},${A.y + 40} ${B.x + 150},${B.y + 40} ${B.x + W / 2},${B.y + 10}`;
    if (a === 'esc' && b === 'check') return `M${A.x - 30},${A.y - H / 2} C${A.x - 30},${A.y - 55} ${B.x + 30},${B.y + 60} ${B.x + 30},${B.y + H / 2}`;
    if (a === 'check' && b === 'esc') return `M${A.x + W / 2},${A.y + 12} C${A.x + 90},${A.y + 12} ${B.x - 100},${B.y - 4} ${B.x - W / 2},${B.y - 4}`;
    return curve(A, B);
  },
};

// Real backend flow (app/routing + app/execution) — used by Live mode.
export const LIVE = {
  name: 'live',
  label: 'Peta alur eksekusi: task.md, classifier, Claude Code, Codex, deterministic QA, integration, fallback, report',
  nodes: {
    task:   { x: 62,  y: 150, title: 'TASK.MD',          sub: 'docs/task.md',          vendor: 'rule' },
    triage: { x: 200, y: 150, title: 'CLASSIFIER',       sub: 'kategori · 0 token',    vendor: 'rule' },
    claude: { x: 370, y: 55,  title: 'CLAUDE CODE',      sub: 'frontend · arsitektur', vendor: 'claude' },
    codex:  { x: 370, y: 150, title: 'CODEX',            sub: 'backend · setup',       vendor: 'codex' },
    qa:     { x: 370, y: 245, title: 'DETERMINISTIC QA', sub: 'lint · test · build',   vendor: 'rule' },
    integ:  { x: 580, y: 85,  title: 'INTEGRATION',      sub: 'ai/integration/*',      vendor: 'pass' },
    esc:    { x: 580, y: 215, title: 'FALLBACK',         sub: 'maks 1× · owner lain',  vendor: 'warn' },
    report: { x: 830, y: 150, title: 'REPORT',           sub: 'execution_report.json', vendor: 'pass' },
  },
  edges: [
    ['task', 'triage'], ['triage', 'claude'], ['triage', 'codex'], ['triage', 'qa'],
    ['claude', 'integ'], ['codex', 'integ'], ['claude', 'esc'], ['codex', 'esc'],
    ['esc', 'integ'], ['qa', 'esc'], ['esc', 'qa'], ['qa', 'report'], ['integ', 'report'],
  ],
  path(a, b, A, B) {
    if (a === 'esc' && b === 'integ') return up(A, B);
    if (a === 'esc' && b === 'qa') return `M${A.x - 20},${A.y + H / 2} C${A.x - 20},292 ${B.x + 20},292 ${B.x + 20},${B.y + H / 2}`;
    if (a === 'qa' && b === 'report') return `M${A.x + W / 2},${A.y + 10} C${A.x + 300},${A.y + 40} ${B.x - 80},${B.y + 40} ${B.x - W / 2},${B.y + 10}`;
    return curve(A, B);
  },
};

export const OWNER_NODE = { claude_code: 'claude', codex: 'codex', deterministic_qa: 'qa' };
export const OWNER_VENDOR = { claude_code: 'claude', codex: 'codex', deterministic_qa: 'rule', internal_decision: 'rule' };
export const OWNER_LABEL = { claude_code: 'Claude Code', codex: 'Codex', deterministic_qa: 'Deterministic QA', internal_decision: 'Internal' };
export const BOX = { W, H };
