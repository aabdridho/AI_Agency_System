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
