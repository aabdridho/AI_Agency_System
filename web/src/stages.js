// Agency stage strip — one card per folder in app/.
import { $ } from './fx.js';
import { STAGES } from './config.js';

const el = {};

export function initStages() {
  const box = $('stages');
  box.innerHTML = '';
  STAGES.forEach((s) => {
    const d = document.createElement('div');
    d.className = 'stage';
    d.innerHTML = '<b></b><span></span><i></i>';
    d.querySelector('b').textContent = s.title;
    d.querySelector('span').textContent = s.desc;
    d.title = s.desc;
    box.appendChild(d);
    el[s.key] = d;
  });
}

// status: todo | active | wait | done | fail
export function setStage(key, status, detail) {
  const d = el[key]; if (!d) return;
  d.classList.remove('active', 'wait', 'done', 'fail');
  if (status && status !== 'todo') d.classList.add(status);
  const def = STAGES.find((s) => s.key === key)?.desc ?? '';
  const text = detail ?? def;
  d.querySelector('span').textContent = text;
  d.title = text;
}

export function setStages(list) {
  STAGES.forEach((s) => {
    const st = list?.find((x) => x.key === s.key);
    setStage(s.key, st?.status ?? 'todo', st?.detail);
  });
}

export const resetStages = () => STAGES.forEach((s) => setStage(s.key, 'todo'));
