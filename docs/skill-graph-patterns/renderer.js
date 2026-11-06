(() => {
  'use strict';
  const DATA = JSON.parse(document.getElementById('data').textContent);
  const $ = (s, el = document) => el.querySelector(s);
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const NS = 'http://www.w3.org/2000/svg';
  const REDUCED = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const TITLES = Object.fromEntries(DATA.patterns.map(p => [p.id, p.title]));
  const R = 15;

  /* ---------- code highlighting ---------- */
  const PRIMS = [
    [/^tools\.readNode$/, 'readNode'],
    [/^tools\.readArtifact$|^read$|^inspect$/, 'readArtifact'],
    [/^nodes\.run$/, 'openNode nextNodeEvent'],
    [/^nodes\.open$|^nodes\.with$|^tools\.openNode$/, 'openNode'],
    [/^nodes\.next$|^tools\.nextNodeEvent$|\.next$|\.result$/, 'nextNodeEvent'],
    [/^tools\.closeNode$|\.close$/, 'closeNode'],
    [/^tools\.publishCheckpoint$/, 'publishCheckpoint'],
  ];
  const TOKEN = /(\/\/[^\n]*)|('(?:\\.|[^'\\\n])*'|"(?:\\.|[^"\\\n])*"|`(?:\\.|[^`\\])*`)|(\b\d+(?:\.\d+)?\b)|(\b(?:const|let|var|await|async|for|of|if|else|return|try|catch|throw|new|function|null|true|false)\b)|(\b(?:tools|nodes)\.\w+|\b(?:read|inspect)\b(?=\()|\b\w+\.(?:next|result|close)\b(?=\())/g;
  function highlight(code) {
    let out = '', last = 0, m;
    TOKEN.lastIndex = 0;
    while ((m = TOKEN.exec(code))) {
      out += esc(code.slice(last, m.index));
      const [tok, com, str, num, kw, host] = m;
      if (com) out += `<span class="tok-com">${esc(com)}</span>`;
      else if (str) out += `<span class="tok-str">${esc(str)}</span>`;
      else if (num) out += `<span class="tok-num">${esc(num)}</span>`;
      else if (kw) out += `<span class="tok-kw">${esc(kw)}</span>`;
      else if (host) {
        const hit = PRIMS.find(([re]) => re.test(host));
        out += hit ? `<span class="tok-host" data-prim="${hit[1]}">${esc(host)}</span>` : esc(host);
      }
      last = m.index + tok.length;
    }
    return out + esc(code.slice(last));
  }
  function codeBlock(code, label) {
    const div = document.createElement('div');
    div.className = 'code';
    div.innerHTML = (label ? `<div class="cell-label">${esc(label)}</div>` : '') + `<pre><code>${highlight(code)}</code></pre>`;
    return div;
  }
  $('#wrapper-code').appendChild(codeBlock(
`const r  = await nodes.run(request)   // open, then wait: {node, ref, line}
const op = await nodes.open(request)  // {node, disp}: started, joined or reused
await op.next()                       // the next line about that node
await op.result()                     // wait for its result
await op.close()                      // release this hold
await nodes.with(request, async op => {})   // scoped, always released
await nodes.next()                    // the next batch of this node's stream

// request: {task, node?, inputs?, refs?, from?, key?}
// refs:    n7 · n7.c3 · n7.r2 · n7.trail · you.m1 · run`));
  $('#helpers-code').appendChild(codeBlock(
`// Application code, not built-ins: whole-artifact reads over readArtifact slices.
async function read(ref) {
  let text = '', offset = 0;
  for (;;) {
    const part = await tools.readArtifact({ref, offset, limit: 4000});
    text += part.text;
    if (part.next_offset >= part.total_chars) return text;
    offset = part.next_offset;
  }
}
const inspect = async ref => JSON.parse(await read(ref));   // a node record: {request, state, holders, refs}`));

  /* ---------- geometry ---------- */
  const trim = (p, cx, cy, r) => { const dx = cx - p.x, dy = cy - p.y, d = Math.hypot(dx, dy) || 1; return {x: p.x + dx / d * r, y: p.y + dy / d * r}; };
  function callPath(a, b, below = R + 1) {
    const dy = b.y - a.y;
    if (dy > 12) {
      const sy = a.y + below, k = Math.max(18, (b.y - R - sy) * 0.5);
      return `M${a.x} ${sy}C${a.x} ${sy + k} ${b.x} ${b.y - R - k} ${b.x} ${b.y - R - 3}`;
    }
    if (dy < -12) {
      const side = b.x >= a.x ? -1 : 1;
      return `M${a.x} ${a.y - R - 1}C${a.x} ${a.y - R - 50} ${b.x + side * 60} ${b.y} ${b.x + side * (R + 3)} ${b.y}`;
    }
    const s = b.x > a.x ? 1 : -1, lift = Math.min(30 + Math.abs(b.x - a.x) * 0.16, a.y - R - 8);
    return `M${a.x + s * R * 0.75} ${a.y - R * 0.66}Q${(a.x + b.x) / 2} ${a.y - R - lift} ${b.x - s * R * 0.75} ${b.y - R * 0.66}`;
  }
  function forkPath(a, b) {
    if (Math.abs(b.y - a.y) <= 12) {
      const s = b.x > a.x ? 1 : -1, lift = Math.min(52 + Math.abs(b.x - a.x) * 0.2, a.y - R - 8);
      return `M${a.x + s * R * 0.35} ${a.y - R}Q${(a.x + b.x) / 2} ${a.y - R - lift} ${b.x - s * R * 0.35} ${b.y - R - 3}`;
    }
    const s = b.x >= a.x ? 1 : -1;
    return `M${a.x + s * (R + 2)} ${a.y}C${a.x + s * 80} ${a.y} ${b.x - s * 80} ${b.y} ${b.x - s * (R + 4)} ${b.y}`;
  }
  function citePath(a, b) {
    const dy = b.y - a.y;
    if (dy > 12) {
      const ox = a.x + R + 1, oy = a.y;
      return `M${ox} ${oy}C${ox + 58} ${oy + 10} ${b.x + 56} ${b.y - dy * 0.45} ${b.x + R * 0.72} ${b.y - R * 0.72}`;
    }
    if (dy < -12) {
      return `M${a.x + R * 0.7} ${a.y - R}C${a.x + 40} ${a.y - 60} ${b.x + 60} ${b.y + 40} ${b.x + R * 0.8} ${b.y + R * 0.6}`;
    }
    const s = b.x > a.x ? 1 : -1, lift = Math.min(44 + Math.abs(b.x - a.x) * 0.2, a.y - R - 8);
    return `M${a.x + s * R * 0.3} ${a.y - R}Q${(a.x + b.x) / 2} ${a.y - R - lift} ${b.x - s * R * 0.3} ${b.y - R - 3}`;
  }
  function msgPath(a, b, sign) {
    const dx = b.x - a.x, dy = b.y - a.y, d = Math.hypot(dx, dy) || 1;
    const nx = -dy / d, ny = dx / d, bulge = (0.2 * d + 18) * sign;
    const cx = (a.x + b.x) / 2 + nx * bulge, cy = Math.max(8, (a.y + b.y) / 2 + ny * bulge);
    const ta = trim(a, cx, cy, R + 3), tb = trim(b, cx, cy, R + 6);
    return `M${ta.x} ${ta.y}Q${cx} ${cy} ${tb.x} ${tb.y}`;
  }
  function readPath(a, b) {
    const ta = trim(a, b.x, b.y, R + 4), tb = trim(b, a.x, a.y, R + 6);
    return `M${ta.x} ${ta.y}L${tb.x} ${tb.y}`;
  }
  const keyOf = id => id === 'you' ? -1 : id.startsWith('n') ? +id.slice(1) : 999;

  const el = (tag, attrs = {}, parent) => {
    const n = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
    if (parent) parent.appendChild(n);
    return n;
  };
  const ease = u => 1 - Math.pow(1 - Math.min(1, Math.max(0, u)), 3);
  const at = (list, t, dflt) => { let v = dflt; for (const [tt, s] of list) { if (tt <= t) v = s; else break; } return v; };
  const STATE_WORD = {running: 'working', waiting: 'idle', completed: 'done', failed: 'failed', cancelled: 'cancelled'};
  const STATE_TONE = {running: 'run', waiting: 'run', completed: 'good', failed: 'bad', cancelled: 'warn'};

  /* ---------- player ---------- */
  const players = [];
  function makePlayer(p, mount, opts = {}) {
    const byId = new Map(p.nodes.map(n => [n.id, n]));
    const pos = id => ({x: p.pos[id][0], y: p.pos[id][1]});
    const name = id => id === 'you' ? 'you' : (byId.get(id) || {}).name || id;
    const svg = el('svg', {viewBox: `0 0 ${p.width} ${p.height}`, role: 'img',
      'aria-label': `${p.title}: ${p.nodes.length} nodes over ${p.T} steps`});
    svg.style.maxWidth = Math.round(p.width * (opts.wide ? 1.15 : 1.3)) + 'px';
    svg.style.minWidth = Math.min(Math.round(p.width * 0.8), 640) + 'px';
    const defs = el('defs', {}, svg);
    for (const [k, color] of [['started', 'var(--edge)'], ['joined', 'var(--cobalt)'], ['reused', 'var(--pine)'],
      ['fork', 'var(--edge)'], ['cite', 'var(--ochre)'], ['msg', 'var(--plum)'], ['read', 'var(--muted)']]) {
      const m = el('marker', {id: `${p.id}-m-${k}`, viewBox: '0 0 10 10', refX: '8', refY: '5', markerWidth: '9', markerHeight: '9',
        orient: 'auto-start-reverse', markerUnits: 'userSpaceOnUse'}, defs);
      el('path', {d: 'M0 1L9 5L0 9z', style: `fill:${color}`}, m);
    }
    const gEdges = el('g', {}, svg), gRip = el('g', {}, svg), gNodes = el('g', {}, svg), gDots = el('g', {}, svg);

    const below = id => id === 'you' ? R + 22 : R + 35;
    const edges = p.edges.map((e, i) => {
      const a = pos(e.from), b = pos(e.to);
      let d, cls, marker, dotColor;
      if (e.kind === 'call') { d = callPath(a, b, below(e.from)); cls = e.disp; marker = e.disp; dotColor = e.disp === 'joined' ? 'var(--cobalt)' : e.disp === 'reused' ? 'var(--pine)' : 'var(--edge)'; }
      else if (e.kind === 'fork') { d = forkPath(a, b); cls = 'fork'; marker = 'fork'; dotColor = 'var(--edge)'; }
      else if (e.kind === 'cite') { d = citePath(a, b); cls = 'cite'; marker = 'cite'; dotColor = 'var(--ochre)'; }
      else if (e.kind === 'msg') { d = msgPath(a, b, 1); cls = 'msg'; marker = 'msg'; dotColor = 'var(--plum)'; }
      else if (e.kind === 'read') { d = readPath(a, b); cls = 'readx'; marker = 'read'; dotColor = 'var(--muted)'; }
      else { d = callPath(a, b, below(e.from)); cls = e.gkind === 'read' ? 'read' : 'link'; marker = e.gkind === 'read' ? 'read' : null; dotColor = 'var(--muted)'; }
      const path = el('path', {d, class: `g-edge ${cls}`, 'marker-end': marker ? `url(#${p.id}-m-${marker})` : ''}, gEdges);
      const dot = el('circle', {r: e.kind === 'msg' ? 4.6 : 3.6, class: 'g-dot', style: `fill:${dotColor}`}, gDots);
      return {e, i, path, dot, len: 0};
    });
    edges.forEach(x => { x.len = x.path.getTotalLength ? x.path.getTotalLength() : 0; });

    const ripples = p.ripples.map(([t, id]) => {
      const {x, y} = pos(id);
      return {t, c: el('circle', {cx: x, cy: y, r: R, class: 'g-ripple'}, gRip)};
    });

    const nodes = new Map();
    for (const n of p.nodes) {
      const {x, y} = pos(n.id);
      const outer = el('g', {transform: `translate(${x} ${y})`}, gNodes);
      const g = el('g', {class: 'g-node', tabindex: '0', role: 'button', 'aria-label': `${n.id} ${n.name}: ${n.task}`}, outer);
      el('circle', {class: 'hit', r: R + 10}, g);
      el('circle', {class: 'ring', r: R + 4.5}, g);
      el('circle', {class: 'core', r: R}, g);
      el('path', {class: 'glyph ok', d: 'M-6 0.5L-2 4.5L6.5-4'}, g);
      el('path', {class: 'glyph x', d: 'M-5-5L5 5M5-5L-5 5'}, g);
      el('path', {class: 'glyph slash', d: 'M-8 8L8-8'}, g);
      const cps = n.cps.slice(0, 4).map((c, i) => el('path', {class: 'g-cp', d: 'M0-6L6 0 0 6-6 0Z', transform: `translate(${-R * 0.95 - i * 5} ${-R * 0.95})`}, g));
      const t1 = el('text', {class: 'name', x: 0, y: R + 16, 'text-anchor': 'middle'}, g); t1.textContent = n.name;
      const sub = el('text', {class: 'sub', x: 0, y: R + 29, 'text-anchor': 'middle'}, g);
      nodes.set(n.id, {n, outer, g, cps, sub});
      g.addEventListener('click', () => select(n.id));
      g.addEventListener('keydown', ev => { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); select(n.id); } });
    }
    let user = null;
    if (p.user) {
      const {x, y} = pos('you');
      const outer = el('g', {transform: `translate(${x} ${y})`}, gNodes);
      const g = el('g', {class: 'g-user', tabindex: '0', role: 'button', 'aria-label': 'you, the person'}, outer);
      el('rect', {class: 'hit', x: -R - 8, y: -R - 8, width: 2 * R + 16, height: 2 * R + 16}, g);
      el('rect', {class: 'core', x: -R, y: -R, width: 2 * R, height: 2 * R, rx: 8}, g);
      const t1 = el('text', {class: 'name', x: 0, y: R + 16, 'text-anchor': 'middle'}, g); t1.textContent = 'you';
      user = {outer, g};
      g.addEventListener('click', () => select('you'));
      g.addEventListener('keydown', ev => { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); select('you'); } });
    }
    const ghosts = p.ghosts.map(gh => {
      const {x, y} = pos(gh.id);
      const outer = el('g', {transform: `translate(${x} ${y})`}, gNodes);
      const g = el('g', {class: `g-ghost ${gh.kind}`}, outer);
      el('circle', {class: 'core', r: R - 2}, g);
      const t1 = el('text', {class: 'name', x: 0, y: R + 15, 'text-anchor': 'middle'}, g); t1.textContent = gh.skill;
      const t2 = el('text', {class: 'sub', x: 0, y: R + 28, 'text-anchor': 'middle'}, g); t2.textContent = gh.kind === 'read' ? 'read, not run' : 'not followed';
      return {outer, gh};
    });

    /* panels */
    const card = document.createElement('div'); card.className = 'stage-card';
    const graph = document.createElement('div'); graph.className = 'graph'; graph.appendChild(svg);
    const transport = document.createElement('div'); transport.className = 'transport';
    const play = document.createElement('button'); play.className = 'play'; play.type = 'button';
    const prev = document.createElement('button'); prev.className = 'stepbtn'; prev.type = 'button'; prev.textContent = '‹'; prev.setAttribute('aria-label', 'Previous step');
    const next = document.createElement('button'); next.className = 'stepbtn'; next.type = 'button'; next.textContent = '›'; next.setAttribute('aria-label', 'Next step');
    const range = document.createElement('input'); range.type = 'range'; range.min = '0'; range.max = '1000'; range.step = '1';
    range.setAttribute('aria-label', `Position in ${p.title}`);
    const clock = document.createElement('span'); clock.className = 'clock';
    transport.append(play, prev, next, range, clock);
    const narration = document.createElement('div'); narration.className = 'narration';
    const doing = document.createElement('ul'); doing.className = 'doing';
    const counts = document.createElement('div'); counts.className = 'counts';
    const C = {joined: 0, reused: 0, fork: 0, msg: 0, reopen: 0};
    p.edges.forEach(e => { if (e.kind === 'call' && C[e.disp] != null) C[e.disp]++; if (e.kind === 'fork') C.fork++; if (e.kind === 'msg') C.msg++; });
    p.lines.forEach(l => { if (l.kind === 'reopen') C.reopen++; });
    const bits = [`${p.nodes.length} nodes`];
    if (C.joined) bits.push(`${C.joined} joined`);
    if (C.reused) bits.push(`${C.reused} reused`);
    if (C.fork) bits.push(`${C.fork} forked`);
    if (C.msg) bits.push(`${C.msg} addressed`);
    if (C.reopen) bits.push(`${C.reopen} reopened`);
    counts.textContent = `${bits.join(', ')}. ${p.T} steps, ${p.lines.length} lines.`;
    const details = document.createElement('div'); details.className = 'details';
    if (opts.wide) {
      const left = document.createElement('div'); left.className = 'walk-left';
      card.append(graph, transport, narration, counts);
      const lower = document.createElement('div'); lower.className = 'walk-grid';
      const steps = document.createElement('div'); steps.className = 'details walk-steps';
      const h = document.createElement('div'); h.className = 'panel-title'; h.textContent = 'What each node is doing at this step';
      steps.append(h, doing);
      lower.append(steps, details);
      mount.append(card, lower);
    } else {
      card.append(graph, transport, narration, doing, counts);
      mount.append(card, details);
    }

    const T = p.T;
    const stepMs = opts.wide ? 2600 : 1900;
    const trans = 0.22;
    const state = {t: T, playing: false, last: null, selected: null};
    const DIM = new Set();
    const stepOf = t => Math.min(T - 1, Math.max(0, Math.floor(t)));

    function holdersAt(id, t) {
      return p.edges.filter(e => e.kind === 'call' && e.disp !== 'reused' && e.to === id && e.t0 <= t && (e.t1 == null || t < e.t1)).map(e => e.from);
    }
    function render() {
      const t = state.t;
      for (const [id, x] of nodes) {
        const s = t < x.n.t0 ? 'hidden' : at(x.n.states, t, 'running');
        x.g.setAttribute('class', `g-node ${s === 'hidden' ? '' : s}${state.selected === id ? ' selected' : ''}`);
        const u = s === 'hidden' ? 0 : ease((t - x.n.t0) / trans);
        x.outer.style.opacity = s === 'hidden' ? 0 : Math.max(0.001, u);
        const {x: px, y: py} = pos(id);
        x.outer.setAttribute('transform', `translate(${px} ${py}) scale(${0.72 + 0.28 * u})`);
        x.cps.forEach((cp, i) => { cp.style.opacity = t >= x.n.cps[i] ? 1 : 0; });
        x.sub.textContent = at(x.n.subs, t, id);
        x.outer.classList.toggle('dimmed', DIM.size > 0 && !DIM.has(id));
      }
      if (user) user.g.setAttribute('class', `g-user${state.selected === 'you' ? ' selected' : ''}`);
      ghosts.forEach(({outer, gh}) => {
        outer.style.opacity = t >= gh.t ? ease((t - gh.t) / trans) : 0;
        outer.classList.toggle('dimmed', DIM.size > 0);
      });
      for (const x of edges) {
        const e = x.e;
        const u = t >= e.t0 ? (t - e.t0) / trans : -1;
        let op = 0, width = 1.5;
        if (u >= 0) {
          if (e.kind === 'call') { const live = e.t1 == null || t < e.t1; op = Math.min(1, u * 1.4); width = e.disp === 'reused' ? 1.6 : live ? 2.8 : 1.4; }
          else if (e.kind === 'msg') { const age = t - e.t0; op = age < 0.9 ? 0.95 : e.trace ? 0.42 : Math.max(0, 0.95 - (age - 0.9) * 3); width = 1.7; }
          else if (e.kind === 'read') { const fade = t > e.t1 ? Math.max(0, 1 - (t - e.t1) / 0.25) : 1; op = Math.min(1, u * 1.6) * fade * 0.9; width = 1.4; }
          else if (e.kind === 'fork') { op = Math.min(1, u * 1.4); width = 1.8; }
          else if (e.kind === 'cite') { op = Math.min(1, u * 1.4) * 0.9; width = 1.4; }
          else { op = Math.min(1, u * 1.4) * 0.9; width = 1.4; }
        }
        x.path.style.opacity = op;
        x.path.style.strokeWidth = width;
        const travel = e.kind === 'msg' ? (t - e.t0) / 0.45 : u;
        if (u >= 0 && travel < 1 && x.len) {
          const pt = x.path.getPointAtLength(x.len * ease(travel));
          x.dot.setAttribute('cx', pt.x); x.dot.setAttribute('cy', pt.y); x.dot.style.opacity = 1;
        } else x.dot.style.opacity = 0;
        const dim = DIM.size > 0 && !(DIM.has(e.from) && DIM.has(e.to));
        x.path.classList.toggle('dimmed', dim);
      }
      for (const r of ripples) {
        const v = (t - r.t) / 0.5;
        if (v >= 0 && v < 1) { r.c.setAttribute('r', R + 3 + 24 * v); r.c.style.opacity = 0.42 * (1 - v); }
        else r.c.style.opacity = 0;
      }
      range.value = String(Math.round(1000 * t / T));
      const k = stepOf(t);
      clock.textContent = `step ${k + 1} of ${T}`;
      const st = p.steps[k];
      narration.textContent = st.say;
      const noted = new Map(st.doing);
      const rows = st.doing.map(([id, text]) => [id, text, false]);
      if (opts.wide) {
        // Every opened node gets a row: the authored note if there is one, otherwise what its state implies.
        for (const n of p.nodes) {
          if (noted.has(n.id) || t < n.t0) continue;
          const s = at(n.states, t, 'running');
          const holds = p.edges.filter(e => e.kind === 'call' && e.disp !== 'reused' && e.from === n.id && e.t0 <= t && (e.t1 == null || t < e.t1)).map(e => e.to);
          const sub = at(n.subs, t, n.id).split(' · ')[1];
          const text = s === 'waiting' ? (holds.length ? `Idle, holding ${holds.join(', ')}; its stream keeps arriving.` : 'Idle until a line arrives.')
            : s === 'completed' ? `Done${sub ? ': ' + n.id + '.' + sub.split(' ')[0] : ''}. Still visible; reopens only if addressed.`
            : s === 'running' ? (holds.length ? `Working on its own task while holding ${holds.join(', ')}.` : 'Working on its own task.')
            : s === 'cancelled' ? 'Cancelled.' : 'Failed.';
          rows.push([n.id, text, true]);
        }
      }
      doing.innerHTML = rows.map(([id, text, auto]) => {
        const s = id === 'you' ? null : at((byId.get(id) || {states: []}).states, t, 'running');
        const pill = s && !opts.compact ? `<span class="pill ${STATE_TONE[s]}">${STATE_WORD[s]}</span>` : '';
        return `<li class="${auto ? 'auto' : ''}"><span class="nid">${esc(id)}</span><span><b>${esc(name(id))}</b> ${pill} ${esc(text)}</span></li>`;
      }).join('');
      play.textContent = state.playing ? '❚❚ Pause' : (t >= T ? '↺ Replay' : '▶ Play');
      play.setAttribute('aria-label', state.playing ? `Pause ${p.title}` : `Play ${p.title}`);
      renderDetails();
    }
    function lineHtml(l, mark) {
      const now = l.t >= stepOf(state.t) ? ' now' : '';
      return `<li class="${mark ? 'mark ' + mark : ''}${now}"><span class="lt">${esc(l.text)}</span>${mark === 'to' ? '<span class="tag">to this node</span>' : mark === 'held' ? '<span class="tag">held</span>' : ''}</li>`;
    }
    function renderDetails() {
      const t = state.t;
      const lines = p.lines.filter(l => l.t <= t);
      const left = `left: ${p.cap - p.nodes.filter(n => n.t0 <= t).length} of ${p.cap} nodes`;
      if (!state.selected) {
        details.innerHTML = `<div class="panel-title">Every node's stream so far <small>${lines.length} lines</small></div>
          <ul class="stream">${lines.slice(-9).map(l => lineHtml(l)).join('')}<li class="budget">${esc(left)}</li></ul>
          <p class="hint">Select a node to see its own stream, request and refs.</p>`;
        const s = details.querySelector('.stream'); if (s) s.scrollTop = s.scrollHeight;
        return;
      }
      if (state.selected === 'you') {
        const mine = lines.filter(l => l.to === 'you' || l.subj === 'you');
        details.innerHTML = `<h4>you <small>the person</small></h4>
          <p class="hint">You see every line, like any node. These are the ones addressed to you or sent by you.</p>
          <ul class="stream">${mine.map(l => lineHtml(l, l.to === 'you' ? 'to' : null)).join('') || '<li class="budget">nothing yet</li>'}</ul>`;
        return;
      }
      const n = byId.get(state.selected);
      if (t < n.t0) { details.innerHTML = `<h4>${esc(n.name)} <small>${esc(n.id)}</small></h4><p class="hint">Not opened yet at this step.</p>`; return; }
      const s = at(n.states, t, 'running');
      const held = new Set(p.edges.filter(e => e.kind === 'call' && e.from === n.id && e.disp !== 'reused' && e.t0 <= t).map(e => e.to));
      const mine = p.lines.slice(n.li).filter(l => l.t <= t);
      const arts = Object.entries(p.artifacts).filter(([, a]) => a.node === n.id && a.t <= t);
      const holders = holdersAt(n.id, t).map(h => h === 'you' ? 'you' : h);
      const reads = n.reads.filter(([rt]) => rt <= t).map(([, ref]) => ref);
      details.innerHTML = `<h4>${esc(n.name)} <small>${esc(n.id)}${n.skill ? ', skill ' + esc(n.skill) : ', no skill'}${n.frm ? ', forked from ' + esc(n.frm) : ''}</small> <span class="pill ${STATE_TONE[s]}">${STATE_WORD[s]}</span></h4>
        <dl>
          <dt>Request</dt><dd><code>${esc(JSON.stringify(n.request))}</code></dd>
          <dt>Opened by</dt><dd>${esc(n.by || 'the launcher')}</dd>
          ${holders.length ? `<dt>Held by</dt><dd>${esc(holders.join(', '))}</dd>` : ''}
          ${arts.length ? `<dt>Published</dt><dd>${arts.map(([ref, a]) => `<code>${esc(ref)}</code>${a.to ? ' → ' + esc(a.to) : ''} ${esc(a.text)}`).join('<br>')}</dd>` : ''}
          ${reads.length ? `<dt>Read</dt><dd>${reads.map(r => `<code>${esc(r)}</code>`).join(', ')}</dd>` : ''}
        </dl>
        <div class="panel-title">What ${esc(n.id)} sees <small>${n.index.length ? 'starting index, then ' : ''}${mine.length} lines</small></div>
        <ul class="stream">${n.index.map(x => `<li class="idx"><span class="lt">${esc(x)}</span><span class="tag">index</span></li>`).join('')}${mine.map(l => lineHtml(l, l.to === n.id ? 'to' : (held.has(l.subj) && l.subj !== n.id) ? 'held' : null)).join('')}<li class="budget">${esc(left)}</li></ul>`;
      const ul = details.querySelector('.stream'); if (ul) ul.scrollTop = ul.scrollHeight;
    }
    function select(id) {
      state.selected = state.selected === id ? null : id;
      render();
    }
    const player = {
      p, state, render,
      start() { if (state.t >= T) state.t = 0; state.playing = true; state.last = null; render(); },
      pause() { state.playing = false; render(); },
      tick(now) {
        if (!state.playing) return;
        if (state.last != null) state.t = Math.min(T, state.t + (now - state.last) / stepMs);
        state.last = now;
        if (state.t >= T) state.playing = false;
        render();
      },
      go(t) { state.playing = false; state.t = Math.max(0, Math.min(T, t)); render(); },
      highlight(ids) { DIM.clear(); (ids || []).forEach(id => DIM.add(id)); render(); },
      seen: false,
    };
    play.addEventListener('click', () => (state.playing ? player.pause() : player.start()));
    next.addEventListener('click', () => {
      const k = stepOf(state.t);
      player.go(state.t < k + 0.99 ? k + 0.999 : Math.min(T - 0.001, k + 1.999));
    });
    prev.addEventListener('click', () => {
      const k = stepOf(state.t);
      player.go(k === 0 ? 0 : (k - 1) + 0.999);
    });
    range.addEventListener('input', () => player.go(T * (+range.value / 1000)));
    render();
    players.push({player, card});
    return player;
  }

  /* ---------- pattern rows ---------- */
  function codeArea(p) {
    const wrap = document.createElement('div'); wrap.className = 'code-wrap';
    const panes = p.code.map(tab => {
      const pane = document.createElement('div'); pane.className = 'pane';
      tab.cells.forEach((c, i) => pane.appendChild(codeBlock(c, tab.cells.length > 1 ? `cell ${i + 1}` : '')));
      if (tab.final) {
        const f = document.createElement('div'); f.className = 'final';
        f.innerHTML = `<div class="cell-label">final message${tab.final_ref ? ' → ' + esc(tab.final_ref) : ''}</div><p>${esc(tab.final)}</p>`;
        pane.appendChild(f);
      }
      return pane;
    });
    if (p.code.length > 1) {
      const tabs = document.createElement('div'); tabs.className = 'tabs'; tabs.setAttribute('role', 'tablist');
      p.code.forEach((tab, i) => {
        const b = document.createElement('button'); b.type = 'button'; b.setAttribute('role', 'tab');
        b.textContent = tab.name; b.setAttribute('aria-selected', String(i === 0));
        b.addEventListener('click', () => {
          tabs.querySelectorAll('button').forEach((x, j) => x.setAttribute('aria-selected', String(j === i)));
          panes.forEach((pn, j) => { pn.hidden = j !== i; });
        });
        tabs.appendChild(b);
      });
      wrap.appendChild(tabs);
    } else {
      const fl = document.createElement('div'); fl.className = 'filelabel'; fl.textContent = p.code[0].name;
      wrap.appendChild(fl);
    }
    panes.forEach((pn, i) => { pn.hidden = i !== 0; wrap.appendChild(pn); });
    return {wrap, panes};
  }
  function primChips(p, panes) {
    const chips = document.createElement('div'); chips.className = 'chips';
    chips.innerHTML = `<span class="lab">Primitives</span>` + p.uses.map(u => `<button type="button" class="chip prim-chip" data-prim="${u}">${u}</button>`).join('');
    chips.querySelectorAll('.prim-chip').forEach(btn => {
      const blocks = () => panes.flatMap(pn => [...pn.querySelectorAll('.code')]);
      const on = () => blocks().forEach(b => b.setAttribute('data-hl', btn.dataset.prim));
      const off = () => blocks().forEach(b => b.removeAttribute('data-hl'));
      btn.addEventListener('mouseenter', on); btn.addEventListener('focus', on);
      btn.addEventListener('mouseleave', off); btn.addEventListener('blur', off);
      btn.addEventListener('click', on);
    });
    return chips;
  }
  const groups = {traversal: '#traversal-list', coordination: '#coordination-list', validation: '#validation-list', composition: '#composition-list'};
  for (const p of DATA.patterns) {
    const row = document.createElement('article');
    row.className = 'pattern' + (p.big ? ' big' : '');
    row.id = p.id;
    row.setAttribute('aria-labelledby', `${p.id}-h`);
    const text = document.createElement('div'); text.className = 'p-text';
    text.innerHTML = `<h3 id="${p.id}-h">${esc(p.title)}</h3>
      <p class="summary">${esc(p.summary)}</p>
      <p class="p-task">Run: <q>${esc(p.run)}</q></p>`;
    const {wrap, panes} = codeArea(p);
    text.appendChild(primChips(p, panes));
    let built = null;
    if (p.built && Object.keys(p.built).length) {
      built = document.createElement('div'); built.className = 'chips';
      built.innerHTML = `<span class="lab">Built from</span>` + Object.keys(p.built).map(k => `<button type="button" class="chip" aria-pressed="false" data-tag="${k}">${esc(TITLES[k] || k)}</button>`).join('');
      text.appendChild(built);
    }
    text.appendChild(wrap);
    const stage = document.createElement('div'); stage.className = 'p-stage';
    row.append(text, stage);
    $(groups[p.group]).appendChild(row);
    const player = makePlayer(p, stage, {compact: true});
    if (built) {
      let pinned = null;
      built.querySelectorAll('[data-tag]').forEach(btn => {
        const tag = btn.dataset.tag;
        btn.addEventListener('mouseenter', () => { if (!pinned) player.highlight(p.built[tag]); });
        btn.addEventListener('mouseleave', () => { if (!pinned) player.highlight(null); });
        btn.addEventListener('click', () => {
          pinned = pinned === tag ? null : tag;
          built.querySelectorAll('[data-tag]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.tag === pinned)));
          player.highlight(pinned ? p.built[pinned] : null);
        });
      });
    }
  }

  /* ---------- walkthrough ---------- */
  {
    const w = DATA.walk;
    const mount = $('#walk-stage');
    const player = makePlayer(w, mount, {wide: true});
    player.go(0.999);
    const {wrap, panes} = codeArea(w);
    const codeMount = $('#walk-code');
    codeMount.appendChild(primChips(w, panes));
    codeMount.appendChild(wrap);
  }

  /* ---------- playback loop and autoplay ---------- */
  function loop(now) {
    for (const {player} of players) player.tick(now);
    requestAnimationFrame(loop);
  }
  requestAnimationFrame(loop);
  if (!REDUCED && 'IntersectionObserver' in window) {
    const io = new IntersectionObserver(entries => {
      for (const entry of entries) {
        const hit = players.find(x => x.card === entry.target);
        if (hit && entry.isIntersecting && !hit.player.seen) { hit.player.seen = true; hit.player.start(); }
      }
    }, {threshold: 0.55});
    players.forEach(({card}) => io.observe(card));
  }
})();
