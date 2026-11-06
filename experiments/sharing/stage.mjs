// Run a stage: every condition × workflow × seed, a few runs at a time, scored and graded, stopping at a budget cap.
// Usage: node stage.mjs <stage> [--cap 25] [--parallel 3]
// Resumable: a run whose summary.json exists is scored again but not re-run; a recorded row whose grade failed is graded again.
// A run touched by the plan's usage limit is void: it is logged to discarded.jsonl, deleted, and run again after the reset.

import fs from 'node:fs';
import path from 'node:path';
import {Run} from './lib/run.mjs';
import {score} from './lib/score.mjs';
import {grade} from './lib/grade.mjs';
import {runHitLimit, waitForReset} from './lib/limit.mjs';
import {STAGES} from './lib/stages.mjs';

const argv = process.argv.slice(2);
const stage = argv[0];
const opt = (k, d) => { const i = argv.indexOf(k); return i >= 0 ? +argv[i + 1] : d; };
const CAP = opt('--cap', 25);
const PAR = opt('--parallel', 3);
const S = STAGES[stage];
if (!S) { console.log(`unknown stage ${stage}; stages: ${Object.keys(STAGES).join(', ')}`); process.exit(1); }
const root = path.resolve('runs', stage);
fs.mkdirSync(root, {recursive: true});
const resultsFile = path.join(root, 'results.jsonl');
const discardFile = path.join(root, 'discarded.jsonl');

const jobs = [];
for (const seed of S.seeds) for (const wf of S.workflows) for (const c of S.conds) jobs.push({wf, cond: c, seed});
const keyOf = (wf, id, seed) => `${wf}|${id}|${seed}`;

let spent = 0;
const done = new Map();
function discard(dir, summary, why) {
  fs.appendFileSync(discardFile, JSON.stringify({dir: path.relative(root, dir), why, cost: (summary && summary.cost) || 0, t: new Date().toISOString()}) + '\n');
  fs.rmSync(dir, {recursive: true, force: true});
}
if (fs.existsSync(discardFile)) {
  for (const l of fs.readFileSync(discardFile, 'utf8').split('\n').filter(Boolean)) spent += JSON.parse(l).cost || 0;
}
// Imports: an earlier stage's runs of an identical condition count as this stage's runs, copied with the condition renamed.
for (const imp of S.imports || []) {
  const srcRoot = path.resolve('runs', imp.stage);
  const as = S.conds.find(c => c.id === imp.as);
  const have = new Set(fs.existsSync(resultsFile) ? fs.readFileSync(resultsFile, 'utf8').split('\n').filter(Boolean).map(l => { const r = JSON.parse(l); return keyOf(r.workflow, r.cond.id, r.seed); }) : []);
  for (const l of fs.readFileSync(path.join(srcRoot, 'results.jsonl'), 'utf8').split('\n').filter(Boolean)) {
    const r = JSON.parse(l);
    if (r.cond.id !== imp.from || !S.workflows.includes(r.workflow) || !S.seeds.includes(r.seed)) continue;
    if (have.has(keyOf(r.workflow, as.id, r.seed))) continue;
    const dir = `${r.workflow}-${as.id}-s${r.seed}`;
    fs.cpSync(path.join(srcRoot, r.dir), path.join(root, dir), {recursive: true});
    fs.appendFileSync(resultsFile, JSON.stringify({...r, cond: as, dir, imported: imp.stage}) + '\n');
    console.log(`imported ${imp.stage}/${r.dir} as ${dir}`);
  }
}

const toRegrade = [];
if (fs.existsSync(resultsFile)) {
  const kept = [];
  for (const l of fs.readFileSync(resultsFile, 'utf8').split('\n').filter(Boolean)) {
    const r = JSON.parse(l);
    const dir = path.join(root, r.dir);
    if (r.status === 'usage limit' || runHitLimit(dir)) { discard(dir, r, 'usage limit'); console.log(`dropped ${r.dir}: usage limit`); continue; }
    kept.push(r);
    if (r.status === 'answered' && (!r.grade || r.grade.score == null)) toRegrade.push(r);
  }
  for (const r of toRegrade) {
    const summary = JSON.parse(fs.readFileSync(path.join(root, r.dir, 'summary.json')));
    r.grade = await grade(r.workflow, summary.answer);
    console.log(`regraded ${r.dir}: ${r.grade.score}/${r.grade.max}`);
  }
  fs.writeFileSync(resultsFile, kept.map(r => JSON.stringify(r) + '\n').join(''));
  for (const r of kept) {
    done.set(keyOf(r.workflow, r.cond.id, r.seed), r);
    spent += (r.cost || 0) + ((r.grade && r.grade.cost) || 0);
  }
}
console.log(`${stage}: ${jobs.length} runs, ${done.size} already done, $${spent.toFixed(2)} spent, cap $${CAP}`);

let pause = null;
function pauseUntil(until) {
  if (!pause) pause = waitForReset(until).then(() => { pause = null; });
  return pause;
}

async function one(job) {
  const key = keyOf(job.wf, job.cond.id, job.seed);
  if (done.has(key) || spent >= CAP) return true;
  while (pause) await pause;
  const dir = path.join(root, `${job.wf}-${job.cond.id}-s${job.seed}`);
  let summary;
  if (fs.existsSync(path.join(dir, 'summary.json'))) summary = JSON.parse(fs.readFileSync(path.join(dir, 'summary.json')));
  else {
    fs.rmSync(dir, {recursive: true, force: true});
    const t0 = Date.now();
    summary = await new Run({workflow: job.wf, cond: job.cond, seed: job.seed, dir}).start();
    console.log(`ran ${key} in ${Math.round((Date.now() - t0) / 1000)}s, $${summary.cost}, ${summary.status}`);
  }
  if (summary.status === 'usage limit' || runHitLimit(dir)) {
    spent += summary.cost || 0;
    discard(dir, summary, 'usage limit');
    console.log(`voided ${key}: usage limit; it runs again after the reset`);
    pauseUntil(summary.limitUntil || Date.now() + 20 * 60 * 1000);
    return false;
  }
  const state = JSON.parse(fs.readFileSync(path.join(dir, 'state.json')));
  const m = score(state, summary);
  const g = await grade(job.wf, summary.answer);
  const rec = {workflow: job.wf, cond: job.cond, seed: job.seed, dir: path.relative(root, dir), ...m, grade: g};
  spent += (summary.cost || 0) + (g.cost || 0);
  fs.appendFileSync(resultsFile, JSON.stringify(rec) + '\n');
  done.set(key, rec);
  console.log(`scored ${key}: grade ${g.score}/${g.max}, checks ${JSON.stringify(m.checks)}, total spent $${spent.toFixed(2)}`);
  return true;
}

const queue = [...jobs];
await Promise.all(Array.from({length: PAR}, async () => {
  while (queue.length) {
    const job = queue.shift();
    let ok = true;
    try { ok = await one(job); } catch (e) { console.log(`error ${keyOf(job.wf, job.cond.id, job.seed)}: ${e.message}`); }
    if (!ok) queue.unshift(job);
  }
}));
console.log(`${stage} finished: $${spent.toFixed(2)} spent`);
process.exit(0);
