// Run one workflow under one condition: node run_one.mjs <workflow> <delivery> <seed> [outdir]
import path from 'node:path';
import {Run} from './lib/run.mjs';

const [workflow, delivery, seed = '1', out] = process.argv.slice(2);
const cond = {id: delivery, delivery, broadcast: 'lifecycle+cp', data: 'publish', wake: 'code'};
const dir = out || path.resolve('runs', 'pilot', `${workflow}-${delivery}-s${seed}`);
const run = new Run({workflow, cond, seed: +seed, dir});
const summary = await run.start();
console.log(JSON.stringify({dir, ...summary, answer: summary.answer && summary.answer.slice(0, 600)}, null, 1));
process.exit(0);
