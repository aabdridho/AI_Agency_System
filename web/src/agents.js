import * as api from './api.js';
import {
  resetMap,
  nodeState,
  setNodeLabel,
} from './map.js';
import { store } from './ui.js';
import { selectRuntimeAgents } from './agent_scope.js';


const POLL_MS = 650;


const AGENT_META = {
  codex: {
    node: 'codex',
    vendor: 'codex',
  },

  'claude-code': {
    node: 'claude',
    vendor: 'claude',
  },

  'deterministic-qa': {
    node: 'qa',
    vendor: 'rule',
  },
};


let timer = null;


const short = (value, max = 24) => {
  const text = String(value ?? '');

  if (text.length <= max) {
    return text;
  }

  return `${text.slice(0, max - 1)}…`;
};


function applyAgent(agent) {
  const meta = AGENT_META[agent.id];

  if (!meta) {
    return;
  }

  const task = agent.current_task ?? '';

  if (agent.status === 'running') {
    nodeState(
      meta.node,
      'active',
      meta.vendor,
    );

    setNodeLabel(
      meta.node,
      short(
        task
          ? `${task} · running`
          : 'running',
      ),
    );

    return;
  }

  if (agent.status === 'waiting') {
    nodeState(
      meta.node,
      'active',
      meta.vendor,
    );

    setNodeLabel(
      meta.node,
      short(
        task
          ? `${task} · waiting`
          : 'waiting',
      ),
    );

    return;
  }

  if (agent.status === 'error') {
    nodeState(
      meta.node,
      'fail',
      meta.vendor,
    );

    setNodeLabel(
      meta.node,
      short(
        task
          ? `${task} · error`
          : 'error',
      ),
    );

    return;
  }

  if (agent.status === 'offline') {
    nodeState(
      meta.node,
      'fail',
      meta.vendor,
    );

    setNodeLabel(
      meta.node,
      'offline',
    );
  }
}


export function renderAgentRuntime(
  agents,
  selectedProject,
  selectedRunId,
  renderHistorical,
) {
  /*
   * Arbitration:
   *
   * Active runtime agent wins while real work is in
   * progress. Otherwise restore the latest persisted
   * execution-event snapshot for the selected project.
   */

  const active = selectRuntimeAgents(
    agents.filter(
      (agent) => AGENT_META[agent.id],
    ),
    selectedProject,
    selectedRunId,
  );

  if (!active.length) {
    if (renderHistorical?.()) {
      return;
    }

    resetMap();
    return;
  }

  resetMap();

  active.forEach(applyAgent);
}


async function poll(context) {
  if (!context.isLive()) {
    return;
  }

  /*
   * Replay owns the map while animation is running.
   * Runtime polling must not fight replayTask().
   */
  if (store.running) {
    return;
  }

  try {
    const agents = await api.listAgents();

    renderAgentRuntime(
      agents,
      context.selectedProject(),
      context.selectedRunId(),
      context.renderHistorical,
    );
  } catch {
    /*
     * Fail soft.
     * Connection state is already represented by the main
     * api.py connection indicator.
     */
  }
}


export function stopAgentMonitor() {
  if (timer !== null) {
    clearInterval(timer);
    timer = null;
  }
}


export function startAgentMonitor(context) {
  stopAgentMonitor();

  poll(context);

  timer = window.setInterval(
    () => poll(context),
    POLL_MS,
  );
}
