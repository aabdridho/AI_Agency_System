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

export const listAgents = () => req('/api/agents');

export const analyzeProjectIntake = (projectName, brief, references = []) =>
  req('/api/projects/intake', {
    method: 'POST',
    body: JSON.stringify({
      project_name: projectName,
      brief,
      references,
    }),
  });

export const confirmProjectIntake = (
  projectName,
  result,
  answers,
) =>
  req('/api/projects/intake/confirm', {
    method: 'POST',
    body: JSON.stringify({
      project_name: projectName,
      result,
      answers,
    }),
  });

export const approveProjectIntake = (
  projectName,
  result,
) =>
  req('/api/projects/intake/approve', {
    method: 'POST',
    body: JSON.stringify({
      project_name: projectName,
      result,
    }),
  });

export const listProjects = () => req('/api/projects');
export const getProject = (name) => req(`/api/projects/${encodeURIComponent(name)}`);
const executionRequests = new Map();

export const executeProject = (name) => {
  const projectName = String(name ?? '').trim();

  if (!projectName) {
    return Promise.reject(
      new Error('Project name wajib diisi.')
    );
  }

  const existing = executionRequests.get(projectName);

  if (existing) {
    return existing;
  }

  const request = req(
    `/api/projects/${encodeURIComponent(projectName)}/execute`,
    {
      method: 'POST',
    },
  );

  executionRequests.set(projectName, request);

  const cleanup = () => {
    if (executionRequests.get(projectName) === request) {
      executionRequests.delete(projectName);
    }
  };

  void request.then(cleanup, cleanup);


  return request;
};

export const saveRouting = (name) => req(`/api/projects/${encodeURIComponent(name)}/route`, { method: 'POST' });
export const getConfig = () => req('/api/config');
export const putConfig = (config) =>
  req('/api/config', {
    method: 'PUT',
    body: JSON.stringify(config),
  });

export const getEconomics = (name) =>
  req(`/api/projects/${encodeURIComponent(name)}/economics`);

export const getBillingConfig = () =>
  req('/api/billing/config');

export const putBillingConfig = (policy) =>
  req('/api/billing/config', {
    method: 'PUT',
    body: JSON.stringify(policy),
  });
