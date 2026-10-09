import assert from 'node:assert/strict';
import test from 'node:test';

import {
  belongsToExecution,
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
