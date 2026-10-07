// Typed terminal log.
import { $, isFast, getSpeed } from './fx.js';
import { nodeBusy } from './map.js';

const out = () => $('out');

export async function line(tag, cls, text) {
  const o = out();
  const s = document.createElement('span'); s.className = 'l';
  if (tag) { const t = document.createElement('span'); t.className = `tag ${cls}`; t.textContent = tag; s.appendChild(t); }
  const b = document.createElement('span'); b.className = tag ? 't-fg' : cls; s.appendChild(b);
  o.appendChild(s);
  if (isFast()) { b.textContent = text; o.scrollTop = o.scrollHeight; return; }
  const cur = document.createElement('span'); cur.className = 'cursor'; cur.textContent = ' '; s.appendChild(cur);
  const step = Math.max(1, Math.round(text.length / 40));
  for (let i = 0; i < text.length; i += step) {
    b.textContent = text.slice(0, i + step);
    o.scrollTop = o.scrollHeight;
    await new Promise((r) => setTimeout(r, 14 * getSpeed()));
  }
  cur.remove();
}

// A line with a spinner while the node's progress bar fills.
export async function working(node, tag, cls, text, ms) {
  const o = out();
  const s = document.createElement('span'); s.className = 'l';
  const t = document.createElement('span'); t.className = `tag ${cls}`; t.textContent = tag; s.appendChild(t);
  const b = document.createElement('span'); b.className = 't-fg spin'; b.textContent = text; s.appendChild(b);
  o.appendChild(s); o.scrollTop = o.scrollHeight;
  await nodeBusy(node, ms);
  b.classList.remove('spin');
}

export const hasLines = () => out().childElementCount > 0;
