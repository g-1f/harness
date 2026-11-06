// Automatic checks computed from a run's state.json: what the logs can prove.

const LIVE_KINDS = new Set(['open', 'join', 'reuse', 'cp', 'result', 'close', 'cancel', 'fail', 'reopen']);

export function branches(state) {
  const by = Object.fromEntries(state.nodes.map(n => [n.id, n]));
  const top = state.nodes.filter(n => n.opener === 'n1').map(n => n.id).slice(0, 8);
  const memo = {n1: 'root'};
  const of = id => {
    if (memo[id]) return memo[id];
    const n = by[id];
    if (!n) return 'root';
    memo[id] = top.includes(id) ? id : of(n.opener || 'n1');
    return memo[id];
  };
  for (const n of state.nodes) of(n.id);
  return {of, top};
}

function textsOf(state, ids, kind = 'result') {
  return Object.entries(state.artifacts).filter(([, a]) => ids.includes(a.node) && a.kind === kind).map(([, a]) => a.content).join('\n\n');
}

function delivered(state, delivery) {
  // Lines each node received while open, under the run's delivery rule.
  const out = {};
  for (const n of state.nodes) {
    const start = n.states[0][0];
    const end = n.states.at(-1)[1] === 'completed' || n.states.at(-1)[1] === 'cancelled' || n.states.at(-1)[1] === 'failed' ? n.states.at(-1)[0] : Infinity;
    const held = new Set(state.edges.filter(e => e.kind === 'call' && e.disp !== 'reused' && e.from === n.id).map(e => e.to));
    for (const r of state.nodes.filter(x => (x.holdersEver || []).includes(n.id))) held.add(r.id);
    out[n.id] = state.lines.filter(l => {
      if (l.t < start || l.t > end) return false;
      const producer = l.by || l.subj;
      if (producer === n.id && l.kind !== 'reopen') return false;
      if (delivery === 'broadcast') return true;
      return l.to === n.id || held.has(l.subj) || (l.subj === n.id && l.by && l.by !== n.id);
    }).length;
  }
  return out;
}

export function score(state, summary) {
  const {of, top} = branches(state);
  const cross = (a, b) => of(a) !== of(b) && of(a) !== 'root' && of(b) !== 'root';
  const e = state.edges;
  const m = {
    status: summary.status, cost: summary.cost, wall: summary.wall, nodes: state.nodes.length,
    turns: state.nodes.reduce((s, n) => s + (n.turns || 0), 0), cells: state.cells.length,
    lines: state.lines.length, worldCalls: state.worldCalls.length, reads: state.reads.length,
    joins: e.filter(x => x.kind === 'call' && x.disp === 'joined').length,
    reuses: e.filter(x => x.kind === 'call' && x.disp === 'reused').length,
    forks: e.filter(x => x.kind === 'fork').length,
    msgs: e.filter(x => x.kind === 'msg').length,
    crossMsgs: e.filter(x => x.kind === 'msg' && cross(x.from, x.to)).length,
    reopens: state.lines.filter(l => l.kind === 'reopen').length,
    cancels: state.lines.filter(l => l.kind === 'cancel').length,
    fails: state.lines.filter(l => l.kind === 'fail').length,
    crossCites: e.filter(x => x.kind === 'cite' && cross(x.from, x.to)).length,
    crossReads: state.reads.filter(r => {
      const owner = r.ref.split('.')[0];
      return /^n\d+$/.test(owner) && cross(owner, r.node);
    }).length,
    invalidCites: Object.values(state.artifacts).reduce((s, a) => s + (a.invalid ? a.invalid.length : 0), 0),
    openedBeyondSplit: state.nodes.length - 1 - top.length,
    cps: Object.values(state.artifacts).filter(a => a.kind === 'cp').length,
    cellErrors: state.cells.filter(c => c.error).length,
    stalls: state.cells.filter(c => /timed out/.test(c.output || '')).length,
  };
  const d = delivered(state, summary.cond.delivery);
  m.linesDelivered = Object.values(d).reduce((s, x) => s + x, 0);
  m.linesPerNode = +(m.linesDelivered / Math.max(1, state.nodes.length)).toFixed(1);

  const calls = (fn, arg) => state.worldCalls.filter(c => c.fn === fn && !c.error && (!arg || (c.args || [])[0] === arg));
  const subtree = b => state.nodes.filter(n => of(n.id) === b).map(n => n.id);
  const wf = summary.workflow;
  const checks = {};
  if (wf === 'shared') {
    const fetchers = new Set(calls('series', 'cma_futures').map(c => c.node));
    checks.fetchedOnce = fetchers.size <= 1;
    m.futuresFetchers = fetchers.size;
    m.pathNodes = state.nodes.filter(n => !['n1', ...top].includes(n.id) && /cma|policy|rate path|rates path/i.test(n.request.task)).length;
    checks.reused = m.joins + m.reuses + m.crossCites + m.crossReads > 0;
  } else if (wf === 'conflict') {
    const [a, b] = top;
    const readers = new Set(calls('doc', 'halbrook-fire').map(c => c.node));
    m.fireReaders = readers.size;
    const bText = textsOf(state, subtree(b));
    checks.shipmentsBranchExplained = /halbrook|fire|outage|plant (was )?offline|offline/i.test(bText);
    checks.branchesTalked = e.some(x => (x.kind === 'msg' || x.kind === 'cite') && cross(x.from, x.to) &&
      [of(x.from), of(x.to)].sort().join() === [a, b].sort().join());
  } else if (wf === 'cross') {
    const [a, b] = top;
    const readers = new Set(calls('doc', 'pellham-offering').map(c => c.node));
    m.offeringReaders = readers.size;
    const aText = textsOf(state, subtree(a));
    checks.demandBranchKnows = /pellham/i.test(aText) && /(40\s?%|withdr\w*[^.]{0,40}offering|cut\w*[^.]{0,40}2027 transformer orders)/i.test(aText);
    checks.findingCrossed = e.some(x => (x.kind === 'cite' || x.kind === 'msg') && of(x.from) === b && of(x.to) === a) ||
      state.reads.some(r => of(r.node) === a && of(r.ref.split('.')[0]) === b);
  } else if (wf === 'noise') {
    checks.noCrossTraffic = m.crossMsgs === 0 && m.crossReads === 0;
  }
  m.checks = checks;
  return m;
}

export {LIVE_KINDS};
