// Run one workflow under one condition: node run_one.mjs <workflow> <condition> <seed> [outdir]
// The condition is a condition id from any stage (base, identity, guided, tree, broadcast, ...).
import path from 'node:path';
import {Run} from './lib/run.mjs';
import {STAGES} from './lib/stages.mjs';

const [workflow, id, seed = '1', out] = process.argv.slice(2);
const cond = Object.values(STAGES).flatMap(s => s.conds).find(c => c.id === id);
if (!cond) { console.log(`unknown condition ${id}`); process.exit(1); }
const dir = path.resolve(out || path.join('runs', 'try', `${workflow}-${id}-s${seed}`));
const run = new Run({workflow, cond, seed: +seed, dir});
const summary = await run.start();
console.log(JSON.stringify({dir, ...summary, answer: summary.answer && summary.answer.slice(0, 600)}, null, 1));
process.exit(0);
