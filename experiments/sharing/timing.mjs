// When things happened in a stage's runs: the facts behind "could a line have arrived in time?"
// Usage: node timing.mjs <stage>   (writes runs/<stage>/timing.md)
import fs from 'node:fs';
import path from 'node:path';
import {branches} from './lib/score.mjs';

const stage = process.argv[2];
const root = path.resolve('runs', stage);
const runs = fs.readdirSync(root).filter(d => fs.existsSync(path.join(root, d, 'state.json'))).sort().map(d => ({
  d, st: JSON.parse(fs.readFileSync(path.join(root, d, 'state.json'))), sm: JSON.parse(fs.readFileSync(path.join(root, d, 'summary.json'))),
}));
const fin = n => (n.states.find(([, s]) => ['completed', 'cancelled', 'failed'].includes(s)) || [null])[0];
const median = xs => { const v = [...xs].sort((a, b) => a - b); return v.length % 2 ? v[(v.length - 1) / 2] : (v[v.length / 2 - 1] + v[v.length / 2]) / 2; };
const subtreeEnd = (st, of, b) => Math.max(...st.nodes.filter(n => of(n.id) === b).map(n => fin(n) || 0));
let md = `# ${stage}: timing\n\nTimes are seconds from the start of the run.\n\n`;

// 1. Duplicate slow fetches: did the second start before the first returned?
md += `## Shared need: the slow series, fetched twice\n\n| Run | Fetches (start–end, node) | Second started |\n|---|---|---|\n`;
let overlap = 0, pairs = 0;
for (const {d, st} of runs.filter(r => r.sm.workflow === 'shared')) {
  const f = st.worldCalls.filter(c => c.fn === 'series' && c.args[0] === 'cma_futures').map(c => ({s: c.t - c.ms / 1000, e: c.t, node: c.node})).sort((a, b) => a.s - b.s);
  let note = '–';
  if (f.length > 1) { pairs++; const o = f[1].s < f[0].e; overlap += o; note = o ? `${(f[1].s - f[0].s).toFixed(1)}s after the first, while it was in flight` : `${(f[1].s - f[0].e).toFixed(1)}s after the first returned`; }
  md += `| ${d} | ${f.map(x => `${x.s.toFixed(1)}–${x.e.toFixed(1)} ${x.node}`).join(', ')} | ${note} |\n`;
}
md += `\nIn flight: ${overlap} of ${pairs} duplicate fetches.\n`;

// 2. Evidence windows: was the branch that needed the finding still running when another branch found it?
const windows = (wf, docId, needIdx) => {
  let t = `| Run | Found by, at | Branch that needs it ended | Window |\n|---|---|---|---|\n`, open = 0, n = 0;
  for (const {d, st} of runs.filter(r => r.sm.workflow === wf)) {
    const {of, top} = branches(st);
    const need = top[needIdx];
    const found = st.worldCalls.filter(c => c.fn === 'doc' && c.args[0] === docId && of(c.node) !== need).sort((a, b) => a.t - b.t)[0];
    const end = subtreeEnd(st, of, need);
    n++;
    const w = found && found.t < end;
    open += w;
    t += `| ${d} | ${found ? `${found.node}, ${found.t.toFixed(1)}` : '–'} | ${end.toFixed(1)} | ${found ? (w ? `open ${(end - found.t).toFixed(1)}s` : `closed ${(found.t - end).toFixed(1)}s before`) : '–'} |\n`;
  }
  return {t, open, n};
};
const present = w => runs.some(r => r.sm.workflow === w);
for (const wf of ['conflict', 'conflict-long'].filter(present)) {
  const c = windows(wf, 'halbrook-fire', 1);
  md += `\n## ${wf}: the fire release, found by the disclosures branch\n\n${c.t}\nThe shipments branch was still running in ${c.open} of ${c.n} runs.\n`;
}
for (const wf of ['cross', 'cross-long'].filter(present)) {
  const x = windows(wf, 'pellham-offering', 0);
  md += `\n## ${wf}: the offering release, found by the financing branch\n\n${x.t}\nThe demand branch was still running in ${x.open} of ${x.n} runs.\n`;
}

// 3. Did the finding ever appear in a line, and when?
md += `\n## Cross-branch finding: lines that mention it\n\n| Run | First line naming Pellham, the offering or the cut |\n|---|---|\n`;
for (const {d, st} of runs.filter(r => r.sm.workflow.startsWith('cross'))) {
  const l = st.lines.find(l => /pellham|offering|withdr|40\s?%/i.test(l.text));
  md += `| ${d} | ${l ? `${l.t.toFixed(1)}s: ${l.text.replace(/\|/g, '/').slice(0, 90)}` : 'none'} |\n`;
}

// 4. Shape of the work: cells per leaf, and how close sibling branches finish.
const leafCells = [], spread = [];
for (const {st} of runs) {
  const openers = new Set(st.nodes.map(n => n.opener));
  for (const n of st.nodes) if (!openers.has(n.id)) leafCells.push(st.cells.filter(c => c.node === n.id).length);
  const ends = st.nodes.filter(n => n.opener === 'n1').map(fin).filter(v => v != null);
  if (ends.length > 1) spread.push(Math.max(...ends) - Math.min(...ends));
}
md += `\n## Shape of the work\n\n- Cells per leaf node: median ${median(leafCells)}, max ${Math.max(...leafCells)} (${leafCells.length} leaves).\n`;
for (const kind of ['short', 'long']) {
  const lc = [];
  for (const {st, sm} of runs.filter(r => (r.sm.workflow.endsWith('-long') ? 'long' : 'short') === kind)) {
    const openers = new Set(st.nodes.map(n => n.opener));
    for (const n of st.nodes) if (!openers.has(n.id)) lc.push(st.cells.filter(c => c.node === n.id).length);
  }
  if (lc.length) md += `- ${kind} workflows: median ${median(lc)} cells per leaf (${lc.length} leaves).\n`;
}
md += `- First-level branches finish within ${median(spread).toFixed(1)}s of each other (median).\n`;
md += `- Reads of the run index: ${runs.reduce((s, r) => s + r.st.reads.filter(x => x.ref === 'run').length, 0)}. Reads of another branch's artifacts: ${runs.reduce((s, {st}) => { const {of} = branches(st); return s + st.reads.filter(x => /^n\d+/.test(x.ref) && of(x.ref.split('.')[0]) !== of(x.node) && of(x.ref.split('.')[0]) !== 'root' && of(x.node) !== 'root').length; }, 0)}.\n`;
md += `- Cells that wait on the stream, by node kind: ${(() => { let p = 0, l = 0; for (const {st} of runs) { const openers = new Set(st.nodes.map(n => n.opener)); for (const c of st.cells) if (/nodes\.next\(|nextNodeEvent|\.result\(\)/.test(c.code)) openers.has(c.node) ? p++ : l++; } return `${p} in nodes that opened children, ${l} in leaves`; })()}.\n`;
fs.writeFileSync(path.join(root, 'timing.md'), md);
console.log(md);
