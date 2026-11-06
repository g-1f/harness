// Aggregate a stage's results.jsonl into a markdown report: node report.mjs <stage>
import fs from 'node:fs';
import path from 'node:path';

const stage = process.argv[2];
const root = path.resolve('runs', stage);
import {score} from './lib/score.mjs';
// Re-score every run from its saved state so that scorer fixes apply to finished runs; grades are kept.
const rows = fs.readFileSync(path.join(root, 'results.jsonl'), 'utf8').split('\n').filter(Boolean).map(l => JSON.parse(l)).map(r => {
  const dir = path.join(root, r.dir);
  const state = JSON.parse(fs.readFileSync(path.join(dir, 'state.json')));
  const summary = JSON.parse(fs.readFileSync(path.join(dir, 'summary.json')));
  return {...r, ...score(state, summary), grade: r.grade};
});
const conds = [...new Set(rows.map(r => r.cond.id))];
const wfs = ['shared', 'conflict', 'cross', 'noise'].filter(w => rows.some(r => r.workflow === w));
const WF = {shared: 'Shared need', conflict: 'Contradiction', cross: 'Cross-branch finding', noise: 'Noise'};
const mean = xs => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : NaN);
const median = xs => { const v = [...xs].sort((a, b) => a - b); return v.length ? (v.length % 2 ? v[(v.length - 1) / 2] : (v[v.length / 2 - 1] + v[v.length / 2]) / 2) : NaN; };
const f = (x, d = 2) => (Number.isFinite(x) ? x.toFixed(d) : '–');
const pct = (k, n) => `${k}/${n}`;
const sel = (c, w) => rows.filter(r => r.cond.id === c && (!w || r.workflow === w));
const gradeOf = r => (r.grade && r.grade.score != null ? r.grade.score / r.grade.max : NaN);

let md = `# ${stage}: results\n\n${rows.length} runs. Grade is the share of rubric items met, judged blind by Opus 5.5.\n\n`;

md += `## Answer quality by design\n\n| Design | ${wfs.map(w => WF[w]).join(' | ')} | All |\n|---|${wfs.map(() => '---|').join('')}---|\n`;
for (const c of conds) {
  md += `| ${c} | ${wfs.map(w => f(mean(sel(c, w).map(gradeOf)))).join(' | ')} | ${f(mean(sel(c).map(gradeOf)))} |\n`;
}

const CHECK = {
  shared: [['fetchedOnce', 'series fetched by at most one node'], ['reused', 'any join, reuse, cross-branch cite or read']],
  conflict: [['branchesTalked', 'branches cited or messaged each other'], ['shipmentsBranchExplained', 'shipments branch explains the drop']],
  cross: [['findingCrossed', 'finding reached the demand branch'], ['demandBranchKnows', 'demand branch states the Pellham cut']],
  noise: [['noCrossTraffic', 'no cross-branch reads or messages']],
};
md += `\n## Planted-situation checks (runs passing)\n\n| Design | ${wfs.flatMap(w => CHECK[w].map(([, d]) => `${WF[w]}: ${d}`)).join(' | ')} |\n|---|${wfs.flatMap(w => CHECK[w]).map(() => '---|').join('')}\n`;
for (const c of conds) {
  md += `| ${c} | ${wfs.flatMap(w => CHECK[w].map(([k]) => { const rs = sel(c, w); return pct(rs.filter(r => r.checks && r.checks[k]).length, rs.length); })).join(' | ')} |\n`;
}

const M = [
  ['cost', 'Cost per run ($)', 3], ['wall', 'Wall time (s)', 0], ['nodes', 'Nodes', 1], ['openedBeyondSplit', 'Nodes opened below the split', 1],
  ['turns', 'Model turns', 1], ['worldCalls', 'World calls', 1], ['linesPerNode', 'Lines delivered per node', 1],
  ['joins', 'Joins', 2], ['reuses', 'Reuses', 2], ['crossCites', 'Cross-branch cites', 2], ['crossReads', 'Cross-branch reads', 2],
  ['msgs', 'Addressed checkpoints', 2],
];
md += `\n## Mechanics and cost (mean per run)\n\n| Measure | ${conds.join(' | ')} |\n|---|${conds.map(() => '---|').join('')}\n`;
for (const [k, label, d] of M) md += `| ${label} | ${conds.map(c => f(mean(sel(c).map(r => r[k] || 0)), d)).join(' | ')} |\n`;
md += `| Checkpoints published | ${conds.map(c => f(mean(sel(c).map(r => r.cps || 0)), 2)).join(' | ')} |\n`;
md += `| Median wall time (s) | ${conds.map(c => f(median(sel(c).map(r => r.wall || 0)), 0)).join(' | ')} |\n`;
md += `| Median cost per run ($) | ${conds.map(c => f(median(sel(c).map(r => r.cost || 0)), 3)).join(' | ')} |\n`;
md += `| Cells that errored (share) | ${conds.map(c => { const rs = sel(c); const e = rs.reduce((s, r) => s + (r.cellErrors || 0), 0), n = rs.reduce((s, r) => s + (r.cells || 0), 0); return f(100 * e / Math.max(1, n), 1) + '%'; }).join(' | ')} |\n`;
md += `| Cells that stalled to the 9-minute limit | ${conds.map(c => sel(c).reduce((s, r) => s + (r.stalls || 0), 0)).join(' | ')} |\n`;
md += `| Runs where a branch opened children | ${conds.map(c => { const rs = sel(c); return pct(rs.filter(r => r.openedBeyondSplit > 0).length, rs.length); }).join(' | ')} |\n`;

md += `\n## Shared need: fetchers of the slow series (mean)\n\n| Design | Nodes fetching cma_futures |\n|---|---|\n`;
for (const c of conds) md += `| ${c} | ${f(mean(sel(c, 'shared').map(r => r.futuresFetchers || 0)), 2)} |\n`;

const spent = rows.reduce((s, r) => s + (r.cost || 0) + ((r.grade && r.grade.cost) || 0), 0);
md += `\nTotal spent: $${spent.toFixed(2)} (runs $${rows.reduce((s, r) => s + (r.cost || 0), 0).toFixed(2)}, grading $${rows.reduce((s, r) => s + ((r.grade && r.grade.cost) || 0), 0).toFixed(2)}).\n`;
fs.writeFileSync(path.join(root, 'report.md'), md);
console.log(md);
