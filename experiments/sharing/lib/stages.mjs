// Stage definitions: each stage varies one mechanism and holds the rest at the previous stage's winner.

const SHORT = ['shared', 'conflict', 'cross', 'noise'];
const LONG = ['conflict-long', 'cross-long'];
const cond = (id, over = {}) => ({id, delivery: 'tree', broadcast: 'lifecycle+cp', data: 'publish', wake: 'code', ...over});

export const STAGES = {
  stage1: {
    conds: ['tree', 'broadcast', 'scoped', 'index'].map(d => cond(d, {delivery: d})),
    workflows: SHORT,
    seeds: [101, 102, 103],
  },
  // Stage 2: data reuse under broadcast. base is Stage 1's broadcast; its runs for seeds 101-103 are imported, not rerun.
  stage2: {
    conds: [
      cond('base', {delivery: 'broadcast'}),
      cond('identity', {delivery: 'broadcast', data: 'identity'}),
      cond('guided', {delivery: 'broadcast', data: 'identity', guided: true}),
    ],
    workflows: [...SHORT, ...LONG],
    seeds: [101, 102, 103, 104, 105],
    imports: [{stage: 'stage1', from: 'broadcast', as: 'base'}],
  },
  // Stage 3: what a line carries. A 2x2 of data lines x the sharing paragraph, all with call identity under broadcast;
  // the two conditions without data lines are Stage 2's runs, imported.
  stage3: {
    conds: [
      cond('identity', {delivery: 'broadcast', data: 'identity'}),
      cond('guided', {delivery: 'broadcast', data: 'identity', guided: true}),
      cond('identity-data', {delivery: 'broadcast', data: 'identity', lines: 'data'}),
      cond('guided-data', {delivery: 'broadcast', data: 'identity', guided: true, lines: 'data'}),
    ],
    workflows: [...SHORT, ...LONG],
    seeds: [101, 102, 103, 104, 105],
    imports: [{stage: 'stage2', from: 'identity', as: 'identity'}, {stage: 'stage2', from: 'guided', as: 'guided'}],
  },
  // Follow-up: line content. Stage 3's winner, guided-data, against the same with each data line a one-line summary
  // written by a small model; guided-data's runs are imported from Stage 3.
  stage4: {
    conds: [
      cond('guided-data', {delivery: 'broadcast', data: 'identity', guided: true, lines: 'data'}),
      cond('guided-summary', {delivery: 'broadcast', data: 'identity', guided: true, lines: 'summary'}),
    ],
    workflows: [...SHORT, ...LONG],
    seeds: [101, 102, 103, 104, 105],
    imports: [{stage: 'stage3', from: 'guided-data', as: 'guided-data'}],
  },
};
