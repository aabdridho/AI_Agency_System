import assert from 'node:assert/strict';
import test from 'node:test';

import {
  belongsToExecution,
  selectRuntimeAgents,
} from '../src/agent_scope.js';


test(
  'matching project and run belongs to active execution',
  () => {
    assert.equal(
      belongsToExecution(
        {
          project: 'demo',
          run_id: 'run-a',
        },
        'demo',
        'run-a',
      ),
      true,
    );
  },
);


test(
  'agent from another run cannot claim current project map',
  () => {
    assert.equal(
      belongsToExecution(
        {
          project: 'demo',
          run_id: 'run-old',
        },
        'demo',
        'run-new',
      ),
      false,
    );
  },
);


test(
  'agent from another project cannot claim current run',
  () => {
    assert.equal(
      belongsToExecution(
        {
          project: 'other',
          run_id: 'run-a',
        },
        'demo',
        'run-a',
      ),
      false,
    );
  },
);


test(
  'unscoped agent never belongs to selected project',
  () => {
    assert.equal(
      belongsToExecution(
        {
          project: null,
          run_id: null,
        },
        'demo',
        'run-a',
      ),
      false,
    );
  },
);


test(
  'legacy project keeps project-level compatibility',
  () => {
    assert.equal(
      belongsToExecution(
        {
          project: 'demo',
          run_id: null,
        },
        'demo',
        '',
      ),
      true,
    );
  },
);


test(
  'no selected project cannot accept runtime agent',
  () => {
    assert.equal(
      belongsToExecution(
        {
          project: 'demo',
          run_id: 'run-a',
        },
        '',
        'run-a',
      ),
      false,
    );
  },
);

test(
  'running agent wins over waiting agent in same execution',
  () => {
    const selected = selectRuntimeAgents(
      [
        {
          id: 'deterministic-qa',
          project: 'demo',
          run_id: 'run-a',
          status: 'waiting',
        },
        {
          id: 'codex',
          project: 'demo',
          run_id: 'run-a',
          status: 'running',
        },
      ],
      'demo',
      'run-a',
    );

    assert.equal(selected.length, 1);
    assert.equal(selected[0].id, 'codex');
    assert.equal(selected[0].status, 'running');
  },
);


test(
  'waiting agent represents execution when nothing is running',
  () => {
    const selected = selectRuntimeAgents(
      [
        {
          id: 'deterministic-qa',
          project: 'demo',
          run_id: 'run-a',
          status: 'waiting',
        },
      ],
      'demo',
      'run-a',
    );

    assert.equal(selected.length, 1);
    assert.equal(selected[0].status, 'waiting');
  },
);


test(
  'error offline and idle agents do not override history',
  () => {
    const selected = selectRuntimeAgents(
      [
        {
          id: 'codex',
          project: 'demo',
          run_id: 'run-a',
          status: 'error',
        },
        {
          id: 'claude-code',
          project: 'demo',
          run_id: 'run-a',
          status: 'offline',
        },
        {
          id: 'deterministic-qa',
          project: 'demo',
          run_id: 'run-a',
          status: 'idle',
        },
      ],
      'demo',
      'run-a',
    );

    assert.deepEqual(selected, []);
  },
);


test(
  'running agent from stale run cannot beat current waiting agent',
  () => {
    const selected = selectRuntimeAgents(
      [
        {
          id: 'codex',
          project: 'demo',
          run_id: 'run-old',
          status: 'running',
        },
        {
          id: 'deterministic-qa',
          project: 'demo',
          run_id: 'run-new',
          status: 'waiting',
        },
      ],
      'demo',
      'run-new',
    );

    assert.equal(selected.length, 1);
    assert.equal(
      selected[0].id,
      'deterministic-qa',
    );
  },
);

