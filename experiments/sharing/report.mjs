// Aggregate a stage's results.jsonl into a markdown report: node report.mjs <stage>
import fs from 'node:fs';
import path from 'node:path';
import {score} from './lib/score.mjs';
import {WORKFLOWS} from './lib/world.mjs';

const stage = process.argv[2];
const root = path.resolve('runs', stage);
// Re-score every run from its saved state so that scorer fixes apply to finished runs; grades are kept.
const rows = fs.readFileSync(path.join(root, 'results.jsonl'), 'utf8').split('\n').filter(Boolean).map(l => JSON.parse(l)).map(r => {
  const dir = path.join(root, r.dir);
  const state = JSON.parse(fs.readFileSync(path.join(dir, 'state.json')));
  const summary = JSON.parse(fs.readFileSync(path.join(dir, 'summary.json')));
  return {...r, ...score(state, summary), grade: r.grade};
});
const conds = [...new Set(rows.map(r => r.cond.id))];
const wfs = ['shared', 'conflict', 'cross', 'noise', 'conflict-long', 'cross-long'].filter(w => rows.some(r => r.workflow === w));
const WF = {shared: 'Shared need', conflict: 'Contradiction', cross: 'Cross-branch finding', noise: 'Noise',
  'conflict-long': 'Contradiction, long', 'cross-long': 'Cross-branch, long'};
const mean = xs => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : NaN);
const median = xs => { const v = [...xs].sort((a, b) => a - b); return v.length ? (v.length % 2 ? v[(v.length - 1) / 2] : (v[v.length / 2 - 1] + v[v.length / 2]) / 2) : NaN; };
const f = (x, d = 2) => (Number.isFinite(x) ? x.toFixed(d) : '–');
const pct = (k, n) => `${k}/${n}`;
const sel = (c, w) => rows.filter(r => r.cond.id === c && (!w || r.workflow === w));
// Grades split: evidence items (facts and connections) and judgment items (the final call), by rubric index.
const part = (r, judged) => {
  if (!r.grade || r.grade.score == null || !r.grade.items || !r.grade.items.length) return NaN;
  const J = new Set(WORKFLOWS[r.workflow].judgment || []);
  const items = r.grade.items.filter(it => J.has(it.n - 1) === judged);
  return items.length ? items.filter(it => it.met === true).length / items.length : NaN;
};
const evidence = r => (r.grade && r.grade.note === 'no answer' ? 0 : part(r, false));
const judgment = r => part(r, true);

let md = `# ${stage}: results\n\n${rows.length} runs. Grades are the share of rubric items met, judged blind by Opus 5.5. Evidence items are the facts and connections; judgment items are the final call, which the world does not always force, and are reported apart.\n\n`;

md += `## Evidence grade by condition\n\n| Condition | ${wfs.map(w => WF[w]).join(' | ')} | All |\n|---|${wfs.map(() => '---|').join('')}---|\n`;
for (const c of conds) md += `| ${c} | ${wfs.map(w => f(mean(sel(c, w).map(evidence)))).join(' | ')} | ${f(mean(sel(c).map(evidence)))} |\n`;
md += `\n## Judgment items met\n\n| Condition | ${wfs.filter(w => (WORKFLOWS[w].judgment || []).length).map(w => WF[w]).join(' | ')} |\n|---|${wfs.filter(w => (WORKFLOWS[w].judgment || []).length).map(() => '---|').join('')}\n`;
for (const c of conds) md += `| ${c} | ${wfs.filter(w => (WORKFLOWS[w].judgment || []).length).map(w => { const rs = sel(c, w); return pct(rs.filter(r => judgment(r) === 1).length, rs.length); }).join(' | ')} |\n`;

const CHECK = {
  shared: [['fetchedOnce', 'series fetched by at most one node'], ['reused', 'any join, reuse, cross-branch cite or read']],
  conflict: [['branchesTalked', 'branches cited or messaged each other'], ['shipmentsBranchExplained', 'shipments branch explains the drop']],
  cross: [['findingCrossed', 'finding reached the demand branch'], ['demandBranchKnows', 'demand branch states the Pellham cut']],
  noise: [['noCrossTraffic', 'no cross-branch reads or messages']],
};
const checksOf = w => CHECK[w.replace(/-long$/, '')];
md += `\n## Planted-situation checks (runs passing)\n\n| Condition | ${wfs.flatMap(w => checksOf(w).map(([, d]) => `${WF[w]}: ${d}`)).join(' | ')} |\n|---|${wfs.flatMap(w => checksOf(w)).map(() => '---|').join('')}\n`;
for (const c of conds) {
  md += `| ${c} | ${wfs.flatMap(w => checksOf(w).map(([k]) => { const rs = sel(c, w); return pct(rs.filter(r => r.checks && r.checks[k]).length, rs.length); })).join(' | ')} |\n`;
}

const M = [
  ['cost', 'Cost per run ($)', 3], ['wall', 'Wall time (s)', 0], ['nodes', 'Nodes', 1], ['openedBeyondSplit', 'Nodes opened below the split', 1],
  ['turns', 'Model turns', 1], ['cells', 'Cells', 1], ['worldCalls', 'World calls', 1], ['duplicateFetches', 'Duplicate fetches', 2],
  ['dataJoins', 'Calls joined in flight', 2], ['dataReuses', 'Calls reused', 2], ['crossData', 'Calls shared across branches', 2],
  ['dataLines', 'Data lines', 1], ['linesPerNode', 'Lines delivered per node', 1], ['cps', 'Checkpoints published', 2], ['msgs', 'Addressed checkpoints', 2], ['reopens', 'Reopens', 2],
  ['joins', 'Node joins', 2], ['reuses', 'Node reuses', 2], ['crossCites', 'Cross-branch cites', 2], ['crossReads', 'Cross-branch reads', 2],
];
md += `\n## Mechanics and cost (mean per run)\n\n| Measure | ${conds.join(' | ')} |\n|---|${conds.map(() => '---|').join('')}\n`;
for (const [k, label, d] of M) md += `| ${label} | ${conds.map(c => f(mean(sel(c).map(r => r[k] || 0)), d)).join(' | ')} |\n`;
md += `| Median wall time (s) | ${conds.map(c => f(median(sel(c).map(r => r.wall || 0)), 0)).join(' | ')} |\n`;
md += `| Median cost per run ($) | ${conds.map(c => f(median(sel(c).map(r => r.cost || 0)), 3)).join(' | ')} |\n`;
md += `| Cells that errored (share) | ${conds.map(c => { const rs = sel(c); const e = rs.reduce((s, r) => s + (r.cellErrors || 0), 0), n = rs.reduce((s, r) => s + (r.cells || 0), 0); return f(100 * e / Math.max(1, n), 1) + '%'; }).join(' | ')} |\n`;
md += `| Cells that stalled to the 9-minute limit | ${conds.map(c => sel(c).reduce((s, r) => s + (r.stalls || 0), 0)).join(' | ')} |\n`;
md += `| Runs where a branch opened children | ${conds.map(c => { const rs = sel(c); return pct(rs.filter(r => r.openedBeyondSplit > 0).length, rs.length); }).join(' | ')} |\n`;
md += `| Runs that did not answer | ${conds.map(c => { const rs = sel(c); return pct(rs.filter(r => r.status !== 'answered').length, rs.length); }).join(' | ')} |\n`;

if (wfs.includes('shared')) {
  md += `\n## Shared need: nodes that fetched the slow series (mean)\n\n| Condition | Nodes fetching cma_futures |\n|---|---|\n`;
  for (const c of conds) md += `| ${c} | ${f(mean(sel(c, 'shared').map(r => r.futuresFetchers || 0)), 2)} |\n`;
}

md += `\n## Cost by workflow (mean per run, $)\n\n| Condition | ${wfs.map(w => WF[w]).join(' | ')} |\n|---|${wfs.map(() => '---|').join('')}\n`;
for (const c of conds) md += `| ${c} | ${wfs.map(w => f(mean(sel(c, w).map(r => r.cost || 0)), 3)).join(' | ')} |\n`;

const spent = rows.reduce((s, r) => s + (r.cost || 0) + ((r.grade && r.grade.cost) || 0), 0);
const imported = rows.filter(r => r.imported).reduce((s, r) => s + (r.cost || 0) + ((r.grade && r.grade.cost) || 0), 0);
md += `\nTotal: $${spent.toFixed(2)} (runs $${rows.reduce((s, r) => s + (r.cost || 0), 0).toFixed(2)}, grading $${rows.reduce((s, r) => s + ((r.grade && r.grade.cost) || 0), 0).toFixed(2)})${imported ? `, of which $${imported.toFixed(2)} was spent in an earlier stage on imported runs` : ''}.\n`;
fs.writeFileSync(path.join(root, 'report.md'), md);
console.log(md);
