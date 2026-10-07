// Animated GOAT node map (SVG): nodes, edges, travelling packets, bursts, floating costs.
import { $, HEX, CSSVAR, isFast, getSpeed } from './fx.js';
import { BOX } from './layouts.js';

const NS = 'http://www.w3.org/2000/svg';
const { W, H } = BOX;

// Active layout; NODES is a live binding other modules read (e.g. bursts at a node).
export let NODES = {};
let layout = null;
const edgeEl = {}, nodeEl = {};
const baseVendor = {};

const clear = (o) => Object.keys(o).forEach((k) => delete o[k]);

export function initMap(next) {
  layout = next;
  NODES = next.nodes;
  clear(edgeEl); clear(nodeEl); clear(baseVendor);
  ['edges', 'nodes', 'fx'].forEach((id) => { $(id).innerHTML = ''; });
  $('svg').setAttribute('aria-label', next.label);

  const reduce = isFast();
  next.edges.forEach(([a, b], i) => {
    const p = document.createElementNS(NS, 'path');
    p.setAttribute('d', next.path(a, b, NODES[a], NODES[b]));
    p.setAttribute('class', 'edge');
    $('edges').appendChild(p);
    edgeEl[`${a}-${b}`] = p;
    if (reduce) { p.classList.add('idle'); return; }
    const len = p.getTotalLength();
    p.style.strokeDasharray = len; p.style.strokeDashoffset = len;
    p.style.animationDelay = `${i * 70}ms`;
    p.classList.add('drawin');
    p.addEventListener('animationend', () => {
      p.classList.remove('drawin'); p.style.strokeDasharray = ''; p.style.strokeDashoffset = ''; p.style.animationDelay = '';
      p.classList.add('idle');
    }, { once: true });
  });

  Object.entries(NODES).forEach(([k, n], i) => {
    baseVendor[k] = n.vendor;
    const g = document.createElementNS(NS, 'g');
    g.setAttribute('class', 'node');
    g.style.setProperty('--nc', CSSVAR[n.vendor]);
    const x = n.x - W / 2, y = n.y - H / 2;
    g.innerHTML = `<rect class="ring" x="${x}" y="${y}" width="${W}" height="${H}" rx="10"/>
      <rect class="box" x="${x}" y="${y}" width="${W}" height="${H}" rx="10"/>
      <rect class="orbit" x="${x}" y="${y}" width="${W}" height="${H}" rx="10" pathLength="100"/>
      <rect class="prog" x="${x + 10}" y="${y + H - 7}" width="0" height="2" rx="1"/>
      <text x="${n.x}" y="${n.y - 4}" text-anchor="middle"></text>
      <text class="t2" x="${n.x}" y="${n.y + 11}" text-anchor="middle"></text>`;
    const [t1, t2] = g.querySelectorAll('text');
    t1.textContent = n.title; t2.textContent = n.sub;
    if (!reduce) {
      g.style.opacity = 0;
      const an = g.animate([{ opacity: 0, transform: 'translateY(8px)' }, { opacity: 1, transform: 'none' }],
        { duration: 500, delay: 200 + i * 80, fill: 'forwards', easing: 'ease-out' });
      an.onfinish = () => { g.style.opacity = 1; an.cancel(); };
    }
    $('nodes').appendChild(g);
    nodeEl[k] = g;
  });
}

export const currentLayout = () => layout?.name;

export function setNodeLabel(k, text, vendor) {
  const g = nodeEl[k]; if (!g) return;
  g.querySelector('.t2').textContent = text;
  if (vendor) { g.style.setProperty('--nc', CSSVAR[vendor]); baseVendor[k] = vendor; }
}

export function nodeState(k, state, vendor) {
  const g = nodeEl[k]; if (!g) return;
  if (vendor) g.style.setProperty('--nc', CSSVAR[vendor]);
  if (state === 'active') {
    Object.values(nodeEl).forEach((n) => n.classList.remove('on'));
    g.classList.remove('bad', 'ok');
    g.classList.add('on');
  } else if (state === 'ok') {
    g.classList.remove('on', 'busy', 'bad');
    g.classList.add('ok');
  } else if (state === 'fail') {
    g.classList.remove('on', 'ok', 'busy');
    void g.getBBox();
    g.classList.add('bad');
    flash(false);
    burst(NODES[k].x, NODES[k].y, 'fail', 14);
  }
}

export function nodeBusy(k, ms) {
  const g = nodeEl[k]; if (!g) return Promise.resolve();
  const pr = g.querySelector('.prog'), full = W - 20;
  g.classList.add('busy');
  if (isFast()) { pr.setAttribute('width', full); g.classList.remove('busy'); return Promise.resolve(); }
  const t0 = performance.now(), d = ms * getSpeed();
  return new Promise((res) => {
    (function f(t) {
      const p = Math.min(1, (t - t0) / d);
      pr.setAttribute('width', full * p);
      if (p < 1) requestAnimationFrame(f); else { g.classList.remove('busy'); res(); }
    })(t0);
  });
}

export function flash(good) {
  const f = $('flash');
  f.classList.toggle('ok', !!good);
  f.classList.remove('go'); void f.offsetWidth; f.classList.add('go');
}

export function burst(x, y, vendor, n = 9) {
  if (isFast()) return;
  const color = HEX[vendor];
  const ps = [...Array(n)].map((_, i) => {
    const d = document.createElementNS(NS, 'circle');
    d.setAttribute('r', 2 + Math.random() * 1.5);
    d.setAttribute('fill', color);
    d.style.filter = `drop-shadow(0 0 4px ${color})`;
    $('fx').appendChild(d);
    const a = (i / n) * Math.PI * 2 + Math.random() * 0.4;
    return { d, vx: Math.cos(a) * (1.2 + Math.random() * 1.4), vy: Math.sin(a) * (1.2 + Math.random() * 1.4) };
  });
  const t0 = performance.now();
  (function f(t) {
    const p = (t - t0) / 650;
    ps.forEach((o) => { const s = p * 22; o.d.setAttribute('cx', x + o.vx * s); o.d.setAttribute('cy', y + o.vy * s); o.d.style.opacity = 1 - p; });
    if (p < 1) requestAnimationFrame(f); else ps.forEach((o) => o.d.remove());
  })(t0);
}
export const burstAt = (k, vendor, n) => burst(NODES[k].x, NODES[k].y, vendor, n);

export function floatText(k, text, vendor, dy = 0) {
  if (isFast() || !NODES[k]) return;
  const n = NODES[k];
  const t = document.createElementNS(NS, 'text');
  t.setAttribute('x', n.x + W / 2 - 6);
  t.setAttribute('y', n.y - H / 2 - 4 - dy);
  t.setAttribute('text-anchor', 'end');
  t.setAttribute('class', 'float');
  t.setAttribute('fill', HEX[vendor]);
  t.textContent = text;
  $('fx').appendChild(t);
  setTimeout(() => t.remove(), 1400);
}

export function travel(a, b, vendor) {
  const e = edgeEl[`${a}-${b}`];
  if (!e) return Promise.resolve();
  if (e.classList.contains('drawin')) {
    e.classList.remove('drawin');
    e.style.strokeDasharray = ''; e.style.strokeDashoffset = '';
  }
  e.classList.remove('idle');
  e.style.setProperty('--ec', CSSVAR[vendor]);
  e.classList.add('hot');
  if (isFast()) { e.classList.remove('hot'); e.classList.add('used'); return Promise.resolve(); }
  const color = HEX[vendor];
  const len = e.getTotalLength(), dur = Math.max(420, len * 3.3) * getSpeed();
  const dots = [0, 1, 2, 3, 4].map((i) => {
    const d = document.createElementNS(NS, 'circle');
    d.setAttribute('r', i ? Math.max(1.2, 4 - i * 0.7) : 5.5);
    d.setAttribute('fill', i ? color : '#fff');
    d.style.filter = `drop-shadow(0 0 ${i ? 3 : 8}px ${color})`;
    d.style.opacity = i ? 1 - i * 0.18 : 1;
    $('fx').appendChild(d);
    return d;
  });
  return new Promise((res) => {
    const t0 = performance.now();
    (function f(t) {
      const p = Math.min(1, (t - t0) / dur), ease = p < 0.5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2;
      dots.forEach((d, i) => { const q = Math.max(0, ease - i * 0.035), pt = e.getPointAtLength(q * len); d.setAttribute('cx', pt.x); d.setAttribute('cy', pt.y); });
      if (p < 1) requestAnimationFrame(f);
      else {
        const end = e.getPointAtLength(len);
        dots.forEach((d) => d.remove());
        e.classList.remove('hot'); e.classList.add('used');
        burst(end.x, end.y, vendor);
        res();
      }
    })(t0);
  });
}

export function resetMap(labels) {
  Object.entries(nodeEl).forEach(([k, g]) => {
    g.classList.remove('on', 'ok', 'bad', 'busy');
    g.querySelector('.prog').setAttribute('width', 0);
    const l = labels?.[k];
    g.querySelector('.t2').textContent = l ? l.text : NODES[k].sub;
    g.style.setProperty('--nc', CSSVAR[l ? l.vendor : baseVendor[k]]);
  });
  Object.values(edgeEl).forEach((e) => {
    e.classList.remove('hot', 'used');
    if (!e.classList.contains('drawin')) e.classList.add('idle');
    e.style.removeProperty('--ec');
  });
}
