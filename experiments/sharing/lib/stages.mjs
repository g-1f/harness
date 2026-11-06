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
};
