// Delta trace on a saved run, with no model calls.
// Usage: node trace.mjs <run dir> [delta name ...]   (default: every preset delta)
//
// Pass 1, trace: which stored calls a delta changes, which cells made them, which results and thesis parts rest on them.
// Pass 2, replay: each node's cells are run again against the changed world, and the output the model was shown is
// compared with the same replay against the unchanged world. A node is woken only if a shown output changed.

import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import {CORPUS, World} from '../sharing/lib/world.mjs';

const dir = process.argv[2];
const state = JSON.parse(fs.readFileSync(path.join(dir, 'state.json')));
const summary = JSON.parse(fs.readFileSync(path.join(dir, 'summary.json')));
const WF = summary.workflow;

// Preset deltas: each edits a copy of the world's corpus.
export const DELTAS = {
  duplicate: {what: 'A release that repeats what is already stored', apply: () => {}},
  'unrelated-doc': {what: 'A new document on a topic no node searched for', apply: c => c.docs.push({id: 'port-strike', title: 'Harbour strike at Ostmere',
    body: 'Dock workers at Ostmere began a strike on Monday.', keys: ['harbour', 'strike', 'ostmere']})},
  'series-unit': {what: 'The implied-vol history series has its unit label corrected', apply: c => { c.series.vltx_iv_history.unit = 'implied vol, annualised'; }},
  'spreads-revised': {what: 'Utility bond spreads for 2026Q3 revised from 165bp to 190bp', apply: c => { c.series.utility_spreads.points = c.series.utility_spreads.points.map(p => (p[0] === '2026Q3' ? ['2026Q3', 190] : p)); }},
  'new-debt-doc': {what: 'A new document: Pellham prices a bond (matches an earlier debt search)', apply: c => c.docs.unshift({id: 'pellham-bond', title: 'Pellham Power prices C$1.5B bond',
    body: 'Pellham Power priced a C$1.5B ten-year bond on 3 November at 180bp over, and said the proceeds restore its 2027 transformer orders to plan.', keys: ['debt', 'financing', 'bond', 'pellham']})},
};

const clone = c => ({...c, docs: c.docs.map(d => ({...d})), series: Object.fromEntries(Object.entries(c.series).map(([k, s]) => [k, {...s, points: s.points.map(p => [...p])}]))});
function worldFor(delta) {
  const w = new World(WF, summary.seed, {instant: true});
  w.corpus = clone(CORPUS[WF]);
  if (delta) delta.apply(w.corpus);
  return w;
}

const first = (s, n) => { const l = String(s).split('\n').find(x => x.trim()) || ''; return l.length > n ? l.slice(0, n - 1) + '…' : l; };
const show = v => { if (v === undefined) return '(no return value)'; try { return typeof v === 'string' ? v : JSON.stringify(v, null, 1); } catch { return String(v); } };

// Replay one node's cells in order. World calls go to the given world; node calls answer from the saved run.
async function replay(nodeId, world) {
  const mine = state.cells.filter(c => c.node === nodeId);
  const recorded = state.worldCalls.filter(c => c.node === nodeId);
  let current = null;
  const call = async (op, a) => {
    if (op === 'world') {
      const rec = recorded.find(c => c.fn === a.fn && JSON.stringify(c.args) === JSON.stringify(a.args));
      current.calls.push({fn: a.fn, id: String(a.args[0]), ref: rec ? rec.ref : null, unseen: !rec});
      const v = await world[a.fn](nodeId, ...a.args);
      if (!rec) return {...v, ref: 'new'};
      return rec.shared ? {...v, ref: rec.ref, from: rec.from, [rec.shared]: true} : {...v, ref: rec.ref};
    }
    if (op === 'openNode') {
      const t = state.nodes.find(n => n.request.task === a.request.task && n.id !== nodeId);
      if (!t) throw new Error('replay: this request was not opened in the saved run');
      return {node: t.id, disp: 'started', versions: 0};
    }
    if (op === 'await' || op === 'versions') {
      const refs = Object.keys(state.artifacts).filter(r => r.startsWith(a.node + '.r'));
      if (op === 'versions') return {node: a.node, versions: refs.length, state: 'completed', held: true};
      const ref = refs.at(-1);
      return {node: a.node, ref, line: first(state.artifacts[ref].content, 160), status: 'completed'};
    }
    if (op === 'read') {
      const art = state.artifacts[a.ref];
      if (!art) throw new Error(`no ref ${a.ref}`);
      current.reads.push(a.ref);
      // A stored call output is read as the changed world would now return it.
      const text = art.kind === 'data' ? JSON.stringify(await world[art.fn](nodeId, ...art.args)) : art.content;
      const off = a.offset || 0, lim = a.limit || 4000;
      return {text: text.slice(off, off + lim), next_offset: Math.min(text.length, off + lim), total_chars: text.length};
    }
    // A wait on the stream depends on what other nodes did, not on data: it is not replayed, and the cell times out.
    if (op === 'next' || op === 'nextAbout') { current.waits = true; return new Promise(() => {}); }
    if (op === 'close') return {node: a.node, state: 'completed'};
    if (op === 'publish') return {ref: 'replayed'};
    throw new Error(`replay: no op ${op}`);
  };
  let logs = [];
  const ctx = vm.createContext({console: {log: (...a) => logs.push(a.map(x => (typeof x === 'string' ? x : JSON.stringify(x))).join(' '))},
    __call: call, setTimeout, clearTimeout, Promise, JSON, Math, Date, Array, Object, String, Number, Boolean, RegExp, Map, Set, Error});
  vm.runInContext(BINDINGS, ctx);
  const out = [];
  for (const [i, c] of mine.entries()) {
    current = {node: nodeId, i: i + 1, calls: [], reads: [], output: ''};
    logs = [];
    try {
      let timer;
      const v = await Promise.race([vm.runInContext(`(async () => {\n${c.code}\n})`, ctx)(),
        new Promise((_, rej) => (timer = setTimeout(() => rej(new Error('not replayable: the cell waits on the stream')), 1500)))]);
      clearTimeout(timer);
      current.output = show(v);
    } catch (e) { current.output = `Error: ${e.message}`; if (/not replayable/.test(e.message)) current.unreplayable = true; }
    if (logs.length) current.output = `console:\n${logs.join('\n')}\n\nreturned:\n${current.output}`;
    current.recorded = c.output;
    out.push(current);
  }
  return out;
}

// The node bindings, as in ptc_server.mjs.
const BINDINGS = `
const call = (op, args) => __call(op, args);
globalThis.world = {search: q => call('world', {fn: 'search', args: [q]}), doc: id => call('world', {fn: 'doc', args: [id]}), series: n => call('world', {fn: 'series', args: [n]})};
globalThis.tools = {openNode: ({request} = {}) => call('openNode', {request}), nextNodeEvent: (a = {}) => call('next', a), closeNode: ({handle} = {}) => call('close', {node: handle}),
  publishCheckpoint: ({content, to} = {}) => call('publish', {content, to}), readArtifact: ({ref, offset, limit} = {}) => call('read', {ref, offset, limit})};
class Op { constructor(r) { this.node = r.node; this.disp = r.disp; this._r = r; }
  async result() { return call('await', {node: this.node, after: this._r.versions || 0}); }
  next() { return call('nextAbout', {node: this.node}); } close() { return call('close', {node: this.node}); } }
function pendingOp(promise) { const p = Promise.resolve(promise).then(r => new Op(r));
  return {then: (a, b) => p.then(a, b), catch: b => p.catch(b), result: () => p.then(o => o.result()), next: () => p.then(o => o.next()), close: () => p.then(o => o.close())}; }
globalThis.nodes = {open: request => pendingOp(tools.openNode({request})), run: request => pendingOp(tools.openNode({request})).result(),
  with: async (request, fn) => { const op = await nodes.open(request); try { return await fn(op); } finally { try { await op.close(); } catch (e) {} } },
  handle: id => pendingOp(call('versions', {node: id}).then(v => ({node: id, disp: 'held', versions: 0}))), next: () => tools.nextNodeEvent({})};
globalThis.read = async ref => { let text = '', offset = 0; for (;;) { const p = await tools.readArtifact({ref, offset, limit: 8000}); text += p.text; if (p.next_offset >= p.total_chars) return text; offset = p.next_offset; } };
globalThis.inspect = async ref => JSON.parse(await read(ref)); globalThis.load = async ref => JSON.parse(await read(ref));
`;

// Who rests on whom: a node rests on the nodes it opened or joined and on those whose results it read.
const restsOn = new Map(state.nodes.map(n => [n.id, new Set()]));
for (const e of state.edges) if (e.kind === 'call') restsOn.get(e.from).add(e.to);
for (const r of state.reads) { const o = r.ref.split('.')[0]; if (restsOn.has(o) && o !== r.node) restsOn.get(r.node).add(o); }
const upstreamOf = id => { const seen = new Set(), go = x => { for (const y of restsOn.get(x) || []) if (!seen.has(y)) { seen.add(y); go(y); } }; go(id); return seen; };

// Claims: each bullet or paragraph line of a result. A claim names a source by ref, document id or series name.
const results = Object.entries(state.artifacts).filter(([, a]) => a.kind === 'result');
const claimsOf = text => text.split('\n').map(l => l.trim()).filter(l => l.length > 20);
// The root's thesis parts: its top-level bullets, each with the lines beneath it.
function thesisParts() {
  const root = results.filter(([, a]) => a.node === 'n1').at(-1);
  const parts = [];
  for (const l of root[1].content.split('\n')) {
    if (/^- \*\*/.test(l)) parts.push({label: (l.match(/^- \*\*(.+?)\*\*/) || [, l])[1].replace(/:$/, ''), text: l});
    else if (parts.length && /^\s+\S/.test(l)) parts.at(-1).text += '\n' + l;
  }
  return parts;
}

const base = {};
for (const n of state.nodes) base[n.id] = await replay(n.id, worldFor(null));
const fidelity = Object.values(base).flat();
const exact = fidelity.filter(c => c.output === c.recorded).length;
const waits = fidelity.filter(c => c.unreplayable).length;

export async function impact(name) {
  const delta = DELTAS[name];
  const w0 = worldFor(null), w1 = worldFor(delta);
  // Stored calls whose output the delta changes.
  const data = Object.entries(state.artifacts).filter(([, a]) => a.kind === 'data');
  const moved = [];
  for (const [ref, a] of data) {
    const get = async w => { try { return JSON.stringify(await w[a.fn]('x', ...a.args)); } catch (e) { return `error ${e.message}`; } };
    if (await get(w0) !== await get(w1)) moved.push({ref, fn: a.fn, id: String(a.args[0])});
  }
  const movedRefs = new Set(moved.map(m => m.ref));
  const cells = [], woken = new Set(), exposed = new Set();
  for (const n of state.nodes) {
    const after = await replay(n.id, worldFor(delta));
    for (const [i, c] of after.entries()) {
      const b = base[n.id][i];
      const touched = [...c.calls.map(x => x.ref), ...c.reads].filter(r => movedRefs.has(r));
      const unseen = c.calls.filter(x => x.unseen);
      if (!touched.length && !unseen.length && c.output === b.output) continue;
      // A cell that cannot be replayed and touched moved data counts as changed.
      const changed = c.output !== b.output || (c.unreplayable && touched.length > 0);
      cells.push({cell: `${n.id}#${c.i}`, touched: [...new Set(touched)], changed, unseen: unseen.map(x => `${x.fn} ${x.id}`)});
      (changed || unseen.length ? woken : exposed).add(n.id);
    }
  }
  for (const id of woken) exposed.delete(id);
  // Results downstream of a woken node, and the claims that name a moved source.
  const downstream = state.nodes.map(n => n.id).filter(id => !woken.has(id) && [...upstreamOf(id)].some(u => woken.has(u)));
  const names = new Set(moved.flatMap(m => [m.ref, ...(m.fn === 'search' ? [] : [m.id])]));
  const named = [];
  for (const [ref, a] of results) for (const l of claimsOf(a.content)) if ([...names].some(x => l.includes(x))) named.push({ref, claim: first(l, 110)});
  const atRisk = new Set([...woken, ...downstream]);
  const parts = thesisParts().map(p => {
    const nodesIn = [...new Set(p.text.match(/\bn\d+\b/g) || [])];
    return {label: p.label, risk: nodesIn.some(x => atRisk.has(x) && x !== 'n1'), nodes: nodesIn};
  });
  return {name, what: delta.what, moved, cells, woken: [...woken], exposed: [...exposed], downstream, named, parts,
    untouched: state.nodes.map(n => n.id).filter(id => !woken.has(id) && !downstream.includes(id))};
}

if (process.argv[1] === new URL(import.meta.url).pathname) {
  const names = process.argv.slice(3).length ? process.argv.slice(3) : Object.keys(DELTAS);
  const lines = results.flatMap(([, a]) => claimsOf(a.content));
  const withRef = lines.filter(l => /\bn\d+(\.[drc]\d+)?\b/.test(l)).length;
  let md = `# Delta trace: ${path.basename(dir)}\n\n${state.nodes.length} nodes, ${state.cells.length} cells, ${Object.values(state.artifacts).filter(a => a.kind === 'data').length} stored calls. No model calls were made.\n\n`;
  md += `- Replay fidelity: ${exact} of ${fidelity.length} cells reproduce their recorded output exactly against the unchanged world; ${waits} wait on the stream and are not replayed.\n`;
  md += `- Citation coverage: ${withRef} of ${lines.length} result lines name a node or data ref.\n\n`;
  md += `| Delta | Stored calls moved | Cells touched | Cells whose shown output changed | Nodes woken | Downstream, wait for the child | Untouched | Thesis parts at risk |\n|---|---|---|---|---|---|---|---|\n`;
  const all = [];
  for (const n of names) {
    const r = await impact(n);
    all.push(r);
    md += `| ${r.what} | ${r.moved.length} | ${r.cells.length} | ${r.cells.filter(c => c.changed).length} | ${r.woken.join(', ') || '–'} | ${r.downstream.join(', ') || '–'} | ${r.untouched.length} of ${state.nodes.length} | ${r.parts.filter(p => p.risk).map(p => p.label).join('; ') || '–'} |\n`;
  }
  for (const r of all.filter(r => r.cells.length)) {
    md += `\n## ${r.what}\n\n- Moved: ${r.moved.map(m => `\`${m.ref}\` (${m.fn} ${first(m.id, 50)})`).join(', ') || 'no stored call'}\n`;
    for (const c of r.cells) md += `- Cell ${c.cell}: ${c.touched.length ? `read ${c.touched.join(', ')}; ` : ''}${c.unseen.length ? `made a call the saved run never made (${c.unseen.join(', ')}); ` : ''}shown output ${c.changed ? 'changed' : 'identical'}\n`;
    md += `- Exposed but output identical, not woken: ${r.exposed.join(', ') || 'none'}\n`;
    md += `- Claims that name a moved source: ${r.named.length ? '\n' + r.named.map(x => `  - \`${x.ref}\`: ${x.claim}`).join('\n') : 'none'}\n`;
    md += `- Thesis parts: ${r.parts.map(p => `${p.label} (${p.risk ? 'at risk' : 'holds'})`).join(', ')}\n`;
  }
  fs.writeFileSync(path.join(path.dirname(new URL(import.meta.url).pathname), `impact-${path.basename(dir)}.md`), md);
  console.log(md);
}
