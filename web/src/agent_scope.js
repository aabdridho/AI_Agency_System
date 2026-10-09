export function belongsToExecution(
  agent,
  selectedProject,
  selectedRunId,
) {
  if (!selectedProject) {
    return false;
  }

  if (!agent.project) {
    return false;
  }

  if (agent.project !== selectedProject) {
    return false;
  }

  /*
   * Legacy projects may not have execution_run_id yet.
   * In that case project-level matching remains the
   * compatibility behavior.
   */
  if (!selectedRunId) {
    return true;
  }

  return agent.run_id === selectedRunId;
}

export function selectRuntimeAgents(
  agents,
  selectedProject,
  selectedRunId,
) {
  const relevant = agents.filter(
    (agent) =>
      belongsToExecution(
        agent,
        selectedProject,
        selectedRunId,
      ),
  );

  const running = relevant.filter(
    (agent) => agent.status === 'running',
  );

  /*
   * Real running work has priority over waiting agents.
   * Example: deterministic QA waits while an engineering
   * repair owner is actively running.
   */
  if (running.length) {
    return running;
  }

  return relevant.filter(
    (agent) => agent.status === 'waiting',
  );
}

