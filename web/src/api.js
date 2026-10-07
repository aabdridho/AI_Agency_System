// Thin client for api.py. Every call fails soft so the page still works
// (in Simulasi mode) when the backend is not running.
const BASE = import.meta.env.VITE_API_BASE ?? '';

async function req(path, opts = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  });
  if (!res.ok) {
    let msg = `${res.status}`;
    try { msg = (await res.json()).detail ?? msg; } catch { /* body not JSON */ }
    throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
  }
  return res.json();
}

export async function ping() {
  try {
    const r = await req('/health');
    return r.status === 'ok';
  } catch {
    return false;
  }
}

export const listProjects = () => req('/api/projects');
export const getProject = (name) => req(`/api/projects/${encodeURIComponent(name)}`);
export const saveRouting = (name) => req(`/api/projects/${encodeURIComponent(name)}/route`, { method: 'POST' });
export const getConfig = () => req('/api/config');
export const putConfig = (tiers) => req('/api/config', { method: 'PUT', body: JSON.stringify({ tiers }) });
