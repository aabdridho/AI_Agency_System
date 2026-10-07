// Timing helpers shared by every animated module.
const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
let speed = 1; // 0 = instant

export const setSpeed = (v) => { speed = Number(v); };
export const getSpeed = () => speed;
export const isFast = () => reduceMotion || speed === 0;
export const sleep = (ms) => (isFast() ? Promise.resolve() : new Promise((r) => setTimeout(r, ms * speed)));

export const HEX = {
  rule: '#aab6c0', codex: '#5ec5dd', claude: '#e9a45d',
  pass: '#71d391', fail: '#f26a6a', warn: '#ecd15c',
};
export const CSSVAR = Object.fromEntries(Object.keys(HEX).map((k) => [k, `var(--${k})`]));
export const $ = (id) => document.getElementById(id);
