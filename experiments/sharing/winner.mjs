// The stage rule: the condition whose runs pass the most planted-situation checks wins; ties go to the lowest mean cost.
// Usage: node winner.mjs <stage>
import fs from 'node:fs';
import path from 'node:path';
import {score} from './lib/score.mjs';
import {fileURLToPath} from 'node:url';
const RUNS = path.join(path.dirname(fileURLToPath(import.meta.url)), 'runs');

const stage = process.argv[2];
const root = path.join(RUNS, stage);
const rows = fs.readFileSync(path.join(root, 'results.jsonl'), 'utf8').split('\n').filter(Boolean).map(l => JSON.parse(l)).map(r => {
  const dir = path.join(root, r.dir);
  return {...r, ...score(JSON.parse(fs.readFileSync(path.join(dir, 'state.json'))), JSON.parse(fs.readFileSync(path.join(dir, 'summary.json'))))};
});
const by = {};
for (const r of rows) {
  const c = (by[r.cond.id] ||= {cond: r.cond.id, runs: 0, passed: 0, checks: 0, cost: 0});
  c.runs++;
  c.cost += r.cost || 0;
  for (const v of Object.values(r.checks || {})) { c.checks++; if (v) c.passed++; }
}
const ranked = Object.values(by).map(c => ({...c, cost: +(c.cost / c.runs).toFixed(4)}))
  .sort((a, b) => b.passed - a.passed || a.cost - b.cost);
for (const c of ranked) console.log(`${c.cond.padEnd(10)} checks passed ${c.passed}/${c.checks} over ${c.runs} runs, mean cost $${c.cost}`);
console.log(`winner: ${ranked[0].cond}`);
