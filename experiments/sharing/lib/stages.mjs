// Stage definitions: each stage varies one mechanism and holds the rest at the previous stage's winner.

const ALL = ['shared', 'conflict', 'cross', 'noise'];
const SEEDS = [101, 102, 103];
const cond = (id, over = {}) => ({id, delivery: 'tree', broadcast: 'lifecycle+cp', data: 'publish', wake: 'code', ...over});

export const STAGES = {
  stage1: {
    conds: ['tree', 'broadcast', 'scoped', 'index'].map(d => cond(d, {delivery: d})),
    workflows: ALL,
    seeds: SEEDS,
  },
};
