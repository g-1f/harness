// One experiment run: a v3 harness for a single workflow under one condition.
// Nodes are live claude -p sessions that act through PTC cells (ptc_server.mjs) calling this harness over HTTP.

import http from 'node:http';
import {spawn} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {World, WORKFLOWS} from './world.mjs';
import {systemPrompt, taskPrompt, forkPrompt, reopenPrompt, finishPrompt} from './prompts.mjs';
import {limitOf} from './limit.mjs';

const HERE = path.dirname(new URL(import.meta.url).pathname);
const SERVER = path.resolve(HERE, '..', 'ptc_server.mjs');
const REF = /\b(?:n\d+\.(?:c\d+|r\d+|d\d+|trail))\b/g;
const LIVE = new Set(['running', 'waiting']);

const first = (text, n = 90) => {
  const line = String(text || '').trim().split('\n', 1)[0].trim();
  return line.length <= n ? line : line.slice(0, n - 1).trimEnd() + '…';
};
const canon = v => JSON.stringify(v, Object.keys(v).sort());

export const DEFAULT_CAPS = {nodes: 16, turns: 40, cells: 30, wallMin: 16, cellMs: 9 * 60 * 1000, pollMs: 8.5 * 60 * 1000};

export class Run {
  constructor({workflow, cond, seed, dir, model = 'claude-sonnet-5-5', caps = {}}) {
    this.wf = WORKFLOWS[workflow];
    this.workflow = workflow;
    this.cond = cond;
    this.seed = seed;
    this.dir = path.resolve(dir);
    this.model = model;
    this.caps = {...DEFAULT_CAPS, ...caps};
    this.world = new World(workflow, seed);
    this.nodes = new Map();
    this.lines = [];
    this.artifacts = new Map();
    this.identities = new Map();
    this.waiters = [];
    this.reads = [];
    this.worldCalls = [];
    this.cells = [];
    this.edges = [];
    this.calls = new Map();
    this.cost = 0;
    this.usage = {input: 0, output: 0, cacheRead: 0, cacheWrite: 0};
    fs.mkdirSync(path.join(this.dir, 'nodes'), {recursive: true});
    this.logStream = fs.createWriteStream(path.join(this.dir, 'events.jsonl'));
  }

  now() { return +((Date.now() - this.t0) / 1000).toFixed(2); }
  log(ev) { this.logStream.write(JSON.stringify({t: this.now(), ...ev}) + '\n'); }

  /* ---------------- lifecycle ---------------- */
  async start() {
    this.t0 = Date.now();
    this.server = http.createServer((req, res) => this.handle(req, res));
    this.server.requestTimeout = 0;
    this.server.headersTimeout = 0;
    this.server.timeout = 0;
    this.server.keepAliveTimeout = 0;
    await new Promise(r => this.server.listen(0, '127.0.0.1', r));
    this.url = `http://127.0.0.1:${this.server.address().port}`;
    this.done = new Promise(r => (this.finish = r));
    this.log({ev: 'run', workflow: this.workflow, cond: this.cond, seed: this.seed, model: this.model});

    const root = this.create({task: this.wf.question}, null);
    const kids = this.wf.split.map(task => this.create({task}, root.id));
    this.spawn(root, 'fresh', taskPrompt(root, this, {children: kids}));
    for (const k of kids) this.spawn(k, 'fresh', taskPrompt(k, this, {index: this.startIndex(k)}));

    this.wallTimer = setTimeout(() => this.end('wall time cap'), this.caps.wallMin * 60 * 1000);
    return this.done;
  }

  end(status) {
    if (this.ended) return;
    this.ended = true;
    clearTimeout(this.wallTimer);
    for (const n of this.nodes.values()) {
      if (n.proc) try { n.proc.kill('SIGTERM'); } catch {}
      if (LIVE.has(n.state)) this.setState(n, 'cancelled');
    }
    for (const w of this.waiters) w.resolve({ended: true, lines: [], left: this.left()});
    this.waiters = [];
    this.server.close();
    const root = this.nodes.get('n1');
    const summary = {
      workflow: this.workflow, cond: this.cond, seed: this.seed, model: this.model, status,
      wall: this.now(), cost: +this.cost.toFixed(4), usage: this.usage,
      nodes: this.nodes.size, lines: this.lines.length, cells: this.cells.length,
      worldCalls: this.worldCalls.length, reads: this.reads.length,
      answer: root && root.results.length ? this.artifacts.get(root.results.at(-1)).content : null,
      ...(this.limit ? {limitUntil: this.limit.until, limitText: this.limit.text} : {}),
    };
    fs.writeFileSync(path.join(this.dir, 'summary.json'), JSON.stringify(summary, null, 1));
    fs.writeFileSync(path.join(this.dir, 'state.json'), JSON.stringify({
      nodes: [...this.nodes.values()].map(n => ({
        id: n.id, request: n.request, opener: n.opener, state: n.state, results: n.results, cps: n.cps,
        holdersEver: [...n.holdersEver], states: n.states, cost: n.cost, turns: n.turns, activations: n.activations,
        session: n.session, from: n.request.from || null,
      })),
      lines: this.lines, artifacts: Object.fromEntries(this.artifacts), edges: this.edges,
      reads: this.reads, worldCalls: this.worldCalls, cells: this.cells,
    }, null, 1));
    this.log({ev: 'end', status, cost: this.cost});
    this.logStream.end();
    this.finish(summary);
  }

  create(request, opener) {
    const id = `n${this.nodes.size + 1}`;
    const n = {
      id, request, opener, key: canon(request), holders: new Set(opener ? [opener] : []), holdersEver: new Set(opener ? [opener] : []),
      holding: new Set(), everHeld: new Set(), state: 'running', states: [[this.now(), 'running']], results: [], cps: [],
      cursor: this.lines.length, about: {}, session: null, proc: null, cost: 0, turns: 0, activations: 0, nudges: 0,
      cellCount: 0, indexSeen: {}, t0: this.now(), data: 0,
    };
    this.nodes.set(id, n);
    this.identities.set(n.key, id);
    if (opener) {
      const o = this.nodes.get(opener);
      o.holding.add(id); o.everHeld.add(id);
      this.edges.push({kind: 'call', disp: 'started', from: opener, to: id, t: this.now()});
    }
    if (request.from) this.edges.push({kind: 'fork', from: request.from, to: id, t: this.now()});
    this.addLine({text: `${opener || 'the run'} opened ${id}${request.from ? ' from ' + request.from : ''} · ${first(request.task, 80)}`, kind: 'open', subj: id, by: opener});
    n.cursor = this.lines.length;
    this.log({ev: 'node', id, request, opener});
    return n;
  }

  setState(n, s) {
    if (n.state === s) return;
    n.state = s;
    n.states.push([this.now(), s]);
  }

  /* ---------------- sessions ---------------- */
  mcpConfig(n) {
    const file = path.join(this.dir, 'nodes', `${n.id}.mcp.json`);
    fs.writeFileSync(file, JSON.stringify({mcpServers: {ptc: {command: 'node', args: [SERVER], env: {
      RUN_URL: this.url, NODE_ID: n.id, CELL_CAP: String(this.caps.cells), CELL_MS: String(this.caps.cellMs),
    }}}}));
    return file;
  }

  spawn(n, mode, prompt, src = null) {
    if (this.ended) return;
    const args = ['-p', '--model', this.model, '--output-format', 'json', '--mcp-config', this.mcpConfig(n), '--strict-mcp-config',
      '--tools', '', '--allowedTools', 'mcp__ptc__run_cell', '--system-prompt', systemPrompt(this.cond), '--setting-sources', '',
      '--max-turns', String(this.caps.turns)];
    if (mode === 'fresh') { n.session = crypto.randomUUID(); args.push('--session-id', n.session); }
    else if (mode === 'resume') args.push('--resume', n.session);
    else if (mode === 'fork') args.push('--resume', src.session, '--fork-session');
    n.activations++;
    fs.appendFileSync(path.join(this.dir, 'nodes', `${n.id}.prompts.txt`), `\n===== activation ${n.activations} (${mode}) at ${this.now()}s =====\n${prompt}\n`);
    const proc = spawn('claude', args, {cwd: this.dir, env: {...process.env, MCP_TOOL_TIMEOUT: '900000'}, stdio: ['pipe', 'pipe', 'pipe']});
    n.proc = proc;
    let out = '', err = '';
    proc.stdout.on('data', d => (out += d));
    proc.stderr.on('data', d => (err += d));
    proc.on('close', code => this.onExit(n, proc, code, out, err));
    proc.stdin.end(prompt);
    this.log({ev: 'spawn', id: n.id, mode});
  }

  onExit(n, proc, code, out, err) {
    if (n.proc === proc) n.proc = null;
    let d = null;
    try { d = JSON.parse(out.trim()); } catch {
      try { d = JSON.parse(out.trim().split('\n').filter(Boolean).at(-1)); } catch {}
    }
    for (const w of this.waiters.filter(w => w.node === n.id)) w.resolve({ended: true, lines: [], left: this.left()});
    if (d) {
      this.cost += d.total_cost_usd || 0;
      n.cost += d.total_cost_usd || 0;
      n.turns += d.num_turns || 0;
      const u = d.usage || {};
      this.usage.input += u.input_tokens || 0; this.usage.output += u.output_tokens || 0;
      this.usage.cacheRead += u.cache_read_input_tokens || 0; this.usage.cacheWrite += u.cache_creation_input_tokens || 0;
      if (d.session_id) n.session = d.session_id;
    }
    fs.appendFileSync(path.join(this.dir, 'nodes', `${n.id}.exits.jsonl`), JSON.stringify({t: this.now(), code, d, err: err.slice(-2000)}) + '\n');
    const lim = limitOf(d);
    if (lim && !this.ended) { this.limit = lim; return this.end('usage limit'); }
    if (this.ended || !LIVE.has(n.state)) return;
    if (code !== 0 || !d || d.is_error || !d.result) {
      return this.fail(n, d && d.result ? first(d.result, 120) : `session exited (${code}) ${first(err, 120)}`);
    }
    const open = [...n.holding].filter(c => LIVE.has(this.nodes.get(c).state));
    if (open.length && n.nudges < 2) {
      n.nudges++;
      this.log({ev: 'finish-rule', id: n.id, open});
      return this.spawn(n, 'resume', finishPrompt(open));
    }
    for (const c of open) { this.release(n.id, c); this.maybeCancel(this.nodes.get(c)); }
    this.publishResult(n, d.result);
  }

  /* ---------------- holds ---------------- */
  release(holder, target) {
    const t = this.nodes.get(target);
    if (!t || !t.holders.has(holder)) return;
    t.holders.delete(holder);
    const h = this.nodes.get(holder);
    if (h) h.holding.delete(target);
    const e = [...this.edges].reverse().find(e => e.kind === 'call' && e.from === holder && e.to === target && e.released == null);
    if (e) e.released = this.now();
  }
  maybeCancel(t) {
    if (LIVE.has(t.state) && t.holders.size === 0) this.cancel(t);
  }
  cancel(t) {
    this.setState(t, 'cancelled');
    if (t.proc) try { t.proc.kill('SIGTERM'); } catch {}
    this.addLine({text: `${t.id} cancelled · no holders left`, kind: 'cancel', subj: t.id});
    this.resolveAwaits(t);
    for (const c of [...t.holding]) { this.release(t.id, c); this.maybeCancel(this.nodes.get(c)); }
    this.checkEnd();
  }
  fail(t, reason) {
    this.setState(t, 'failed');
    this.addLine({text: `${t.id} failed · ${first(reason, 100)}`, kind: 'fail', subj: t.id});
    for (const h of [...t.holders]) this.release(h, t.id);
    this.resolveAwaits(t);
    for (const c of [...t.holding]) { this.release(t.id, c); this.maybeCancel(this.nodes.get(c)); }
    this.checkEnd();
  }

  /* ---------------- artifacts and lines ---------------- */
  cites(text, self) {
    const found = [...new Set(String(text).match(REF) || [])];
    const valid = [], invalid = [];
    for (const r of found) {
      const base = r.split('.')[0];
      const ok = r.endsWith('.trail') ? this.nodes.has(base) : this.artifacts.has(r);
      (ok ? valid : invalid).push(r);
    }
    return {valid: valid.filter(r => r.split('.')[0] !== self || !r.endsWith('.trail')), invalid};
  }
  lineText(text, refs) {
    let head = String(text).trim().split('\n', 1)[0];
    if (refs.length) head = head.replace(/\s*\((?:\s*n\d+\.(?:c\d+|r\d+|d\d+|trail)\s*,?)+\)\.?\s*$/, '').replace(/[ ;,]+$/, '');
    return first(head) + (refs.length ? ` · cites ${refs.join(', ')}` : '');
  }
  publishResult(n, text) {
    const ref = `${n.id}.r${n.results.length + 1}`;
    const {valid, invalid} = this.cites(text, n.id);
    this.artifacts.set(ref, {node: n.id, kind: 'result', content: text, cites: valid, invalid, t: this.now()});
    n.results.push(ref);
    this.setState(n, 'completed');
    for (const c of valid) this.edges.push({kind: 'cite', from: c.split('.')[0], to: n.id, ref, t: this.now()});
    this.addLine({text: `${ref} · ${this.lineText(text, valid)}`, kind: 'result', subj: n.id, ref});
    for (const h of [...n.holders]) this.release(h, n.id);
    this.resolveAwaits(n);
    // An addressed checkpoint that arrived while the node was finishing reopens it now.
    const unread = this.lines.slice(n.cursor).filter(l => l.to === n.id && l.kind === 'cp');
    if (unread.length) this.reopen(n, unread.at(-1).subj, unread);
    this.checkEnd();
  }
  addLine(l) {
    const line = {i: this.lines.length, t: this.now(), ...l};
    this.lines.push(line);
    this.log({ev: 'line', ...line});
    for (const w of [...this.waiters]) {
      const n = this.nodes.get(w.node);
      if (w.kind === 'stream' && this.inScope(n, line)) this.deliverStream(w);
      if (w.kind === 'about' && line.subj === w.target && line.by !== w.node) this.deliverAbout(w);
    }
    return line;
  }
  inScope(n, l) {
    const producer = l.by || l.subj;
    if (producer === n.id && l.kind !== 'reopen') return false;
    if (this.cond.delivery === 'broadcast') return true;
    return l.to === n.id || n.everHeld.has(l.subj) || (l.subj === n.id && l.by && l.by !== n.id);
  }
  left() {
    const min = Math.max(0, Math.round((this.caps.wallMin * 60 - this.now()) / 60));
    return `left: ${this.caps.nodes - this.nodes.size} of ${this.caps.nodes} nodes · ${min} min`;
  }
  indexLines(viewer) {
    return [...this.nodes.values()].map(x => {
      const latest = x.results.at(-1) || x.cps.at(-1);
      const word = {running: 'working', waiting: 'idle', completed: 'done', failed: 'failed', cancelled: 'cancelled'}[x.state];
      const sig = `${x.state}|${latest}`;
      const changed = viewer && viewer.indexSeen[x.id] !== sig;
      if (viewer) viewer.indexSeen[x.id] = sig;
      return `${changed ? '* ' : ''}${x.id} · ${first(x.request.task, 70)} · ${word}${latest ? ' · ' + latest : ''}`;
    });
  }
  startIndex(n) {
    if (!['broadcast', 'index'].includes(this.cond.delivery)) return null;
    return [...this.nodes.values()].filter(x => x.id !== n.id).map(x => `${x.id} · ${first(x.request.task, 70)} · ${x.state}`);
  }
  takeStream(n) {
    const batch = this.lines.slice(n.cursor).filter(l => this.inScope(n, l));
    n.cursor = this.lines.length;
    return batch.map(l => l.text + (l.to === n.id ? '   [addressed to you]' : ''));
  }

  /* ---------------- waiting ---------------- */
  wait(w) {
    const n = this.nodes.get(w.node);
    return new Promise(resolve => {
      w.resolve = v => {
        clearTimeout(w.timer);
        this.waiters = this.waiters.filter(x => x !== w);
        if (n.state === 'waiting' && !this.waiters.some(x => x.node === n.id)) this.setState(n, 'running');
        resolve(v);
      };
      w.timer = setTimeout(() => w.resolve({timeout: true, lines: [], left: this.left()}), this.caps.pollMs);
      this.waiters.push(w);
      if (n.state === 'running') this.setState(n, 'waiting');
    });
  }
  deliverStream(w) {
    const n = this.nodes.get(w.node);
    w.resolve({lines: this.takeStream(n), left: this.left()});
  }
  deliverAbout(w) {
    const lines = this.lines.slice(w.after).filter(l => l.subj === w.target && l.by !== w.node);
    w.resolve({lines: lines.map(l => l.text), next: this.lines.length});
  }
  resolveAwaits(t) {
    for (const w of [...this.waiters]) {
      if (w.kind !== 'result' || w.target !== t.id) continue;
      const r = this.resultView(t, w.after);
      if (r) w.resolve(r);
    }
  }
  resultView(t, after) {
    if (t.results.length > after) {
      const ref = t.results.at(-1);
      return {node: t.id, ref, line: first(this.artifacts.get(ref).content, 160), status: 'completed'};
    }
    if (t.state === 'failed' || t.state === 'cancelled') return {node: t.id, ref: null, status: t.state};
    return null;
  }

  /* ---------------- reopen and fork ---------------- */
  reopen(t, sender, addressed) {
    this.setState(t, 'running');
    if (sender && sender !== t.id) {
      t.holders.add(sender); t.holdersEver.add(sender);
      const s = this.nodes.get(sender);
      if (s) { s.holding.add(t.id); s.everHeld.add(t.id); }
    }
    this.addLine({text: `${t.id} reopened · held by ${sender}`, kind: 'reopen', subj: t.id, by: sender});
    const msgs = addressed.map(l => ({ref: l.ref, from: l.subj, content: this.artifacts.get(l.ref).content}));
    const lines = this.takeStream(t).filter(x => !x.endsWith('[addressed to you]'));
    this.spawn(t, 'resume', reopenPrompt(t, t.results.length + 1, msgs, lines));
  }

  /* ---------------- end of run ---------------- */
  checkEnd() {
    const root = this.nodes.get('n1');
    if (!root || LIVE.has(root.state)) return;
    if ([...this.nodes.values()].some(n => LIVE.has(n.state))) return;
    this.end(root.state === 'completed' ? 'answered' : `root ${root.state}`);
  }

  /* ---------------- HTTP API ---------------- */
  handle(req, res) {
    let body = '';
    req.on('data', d => (body += d));
    req.on('end', async () => {
      let msg;
      try { msg = JSON.parse(body); } catch { res.writeHead(400).end(); return; }
      try {
        const out = await this.op(msg.node, msg.op, msg.args || {});
        res.writeHead(200, {'content-type': 'application/json'}).end(JSON.stringify({ok: true, value: out}));
      } catch (e) {
        res.writeHead(200, {'content-type': 'application/json'}).end(JSON.stringify({ok: false, error: e.message}));
      }
    });
  }

  async op(id, op, a) {
    const n = this.nodes.get(id);
    if (!n) throw new Error(`unknown node ${id}`);
    if (this.ended) throw new Error('the run has ended');
    this.log({ev: 'op', node: id, op, args: op === 'cell' ? {chars: (a.code || '').length} : a});
    switch (op) {
      case 'context': return {node: id, children: [...n.holding]};
      case 'openNode': return this.openNode(n, a.request || {});
      case 'next': {
        const lines = this.takeStream(n);
        if (lines.length) return {lines, left: this.left()};
        return this.wait({node: id, kind: 'stream'});
      }
      case 'nextAbout': {
        const after = n.about[a.node] ?? n.cursor;
        const ready = this.lines.slice(after).filter(l => l.subj === a.node && l.by !== id);
        if (ready.length) { n.about[a.node] = this.lines.length; return {lines: ready.map(l => l.text)}; }
        const r = await this.wait({node: id, kind: 'about', target: a.node, after});
        n.about[a.node] = r.next ?? this.lines.length;
        return r;
      }
      case 'await': {
        const t = this.nodes.get(a.node);
        if (!t) throw new Error(`unknown node ${a.node}`);
        const after = a.after ?? 0;
        const r = this.resultView(t, after);
        if (r) return r;
        if (!t.holders.has(id)) throw new Error(`you do not hold ${a.node}`);
        return this.wait({node: id, kind: 'result', target: a.node, after});
      }
      case 'versions': {
        const t = this.nodes.get(a.node);
        if (!t) throw new Error(`unknown node ${a.node}`);
        return {node: t.id, versions: t.results.length, state: t.state, held: t.holders.has(id)};
      }
      case 'close': {
        const t = this.nodes.get(a.node);
        if (!t) throw new Error(`unknown node ${a.node}`);
        if (!t.holders.has(id)) {
          if (!LIVE.has(t.state)) return {node: t.id, state: t.state};
          throw new Error(`you do not hold ${a.node}`);
        }
        this.release(id, t.id);
        this.addLine({text: `${id} closed ${t.id}`, kind: 'close', subj: t.id, by: id});
        this.maybeCancel(t);
        return {node: t.id, state: t.state};
      }
      case 'publish': return this.publish(n, a);
      case 'read': return this.read(n, a);
      case 'world': return this.worldCall(n, a.fn, a.args || []);
      case 'pending': {
        const lines = this.takeStream(n);
        const out = {lines, left: this.left()};
        if (this.cond.delivery === 'index') out.index = this.indexLines(n);
        return out;
      }
      case 'cell': {
        n.cellCount++;
        this.cells.push({node: id, t: this.now(), code: a.code, output: a.output, ms: a.ms, error: a.error || null});
        return {count: n.cellCount};
      }
      default: throw new Error(`unknown op ${op}`);
    }
  }

  openNode(caller, request) {
    if (!request || typeof request.task !== 'string' || !request.task.trim()) throw new Error('request.task is required');
    const req = {task: request.task.trim()};
    for (const k of ['inputs', 'refs', 'from', 'key']) if (request[k] != null && request[k] !== '') req[k] = request[k];
    if (req.from && !this.nodes.has(req.from)) throw new Error(`no node ${req.from} to fork from`);
    const key = canon(req);
    const existing = this.identities.get(key);
    if (existing) {
      const e = this.nodes.get(existing);
      if (LIVE.has(e.state)) {
        if (!e.holders.has(caller.id)) {
          e.holders.add(caller.id); e.holdersEver.add(caller.id);
          caller.holding.add(e.id); caller.everHeld.add(e.id);
          this.edges.push({kind: 'call', disp: 'joined', from: caller.id, to: e.id, t: this.now()});
          this.addLine({text: `${caller.id} joined ${e.id}`, kind: 'join', subj: e.id, by: caller.id});
        }
        return {node: e.id, disp: 'joined', versions: e.results.length};
      }
      if (e.state === 'completed') {
        const ref = e.results.at(-1);
        this.edges.push({kind: 'call', disp: 'reused', from: caller.id, to: e.id, t: this.now(), released: this.now()});
        this.addLine({text: `${caller.id} reused ${ref}`, kind: 'reuse', subj: e.id, by: caller.id});
        return {node: e.id, disp: 'reused', ref, line: first(this.artifacts.get(ref).content, 160)};
      }
    }
    if (this.nodes.size >= this.caps.nodes) throw new Error(`node cap reached (${this.caps.nodes})`);
    const n = this.create(req, caller.id);
    if (req.from) {
      const src = this.nodes.get(req.from);
      this.spawn(n, 'fork', forkPrompt(n, src.id), src);
    } else {
      this.spawn(n, 'fresh', taskPrompt(n, this, {index: this.startIndex(n)}));
    }
    return {node: n.id, disp: 'started', versions: 0};
  }

  // A world call. With call identity, an identical call (same function and arguments, from any node) joins the one
  // still running or reuses its stored output, and a line records it; every output is stored as a ref nK.dJ.
  async worldCall(n, fn, args) {
    if (!['search', 'doc', 'series'].includes(fn)) throw new Error(`no world.${fn}`);
    const identity = this.cond.data === 'identity';
    const key = `${fn}:${JSON.stringify(args)}`;
    const t0 = Date.now();
    const known = identity && this.calls.get(key);
    if (known) {
      const disp = known.done ? 'reused' : 'joined';
      // A node repeating its own call shares nothing, so only calls first made by another node get a line.
      if (known.node !== n.id) {
        this.addLine({text: `${n.id} ${disp} ${known.ref} · ${fn} ${first(String(args[0]), 60)}`, kind: disp === 'joined' ? 'djoin' : 'dreuse',
          subj: known.node, by: n.id, ref: known.ref});
        this.edges.push({kind: 'data', disp, from: n.id, to: known.node, ref: known.ref, t: this.now()});
      }
      let v;
      try { v = await known.promise; } catch (e) {
        this.worldCalls.push({node: n.id, fn, args, ms: Date.now() - t0, t: this.now(), shared: disp, from: known.node, error: e.message});
        throw e;
      }
      this.worldCalls.push({node: n.id, fn, args, ms: Date.now() - t0, t: this.now(), shared: disp, ref: known.ref, from: known.node});
      return {...v, ref: known.ref, from: known.node, [disp]: true};
    }
    const dataLines = this.cond.lines === 'data';
    const entry = {ref: identity || dataLines ? `${n.id}.d${++n.data}` : null, node: n.id, done: false};
    entry.promise = this.world[fn](n.id, ...args);
    if (identity) this.calls.set(key, entry);
    try {
      const v = await entry.promise;
      entry.done = true;
      if (entry.ref) this.artifacts.set(entry.ref, {node: n.id, kind: 'data', fn, args, content: JSON.stringify(v), t: this.now()});
      // Data lines: each fetched document or series is one line. A document's line carries its title and first sentence;
      // a series' line carries its description and latest point.
      if (dataLines && fn !== 'search') {
        let head;
        if (fn === 'doc') {
          const m = String(v.body || '').match(/^(.*?[.!?])(?:\s|$)/s);
          head = `${v.title}: ${(m ? m[1] : String(v.body || '')).trim()}`;
        } else {
          const last = (v.points || []).at(-1);
          head = `${v.desc} (${v.unit})${last ? `: latest ${last[0]} ${last[1]}` : ''}`;
        }
        this.addLine({text: `${entry.ref} · ${fn} ${first(String(args[0]), 40)} · ${first(head, 160)}`, kind: 'data', subj: n.id, ref: entry.ref});
      }
      this.worldCalls.push({node: n.id, fn, args, ms: Date.now() - t0, t: this.now(), ...(entry.ref ? {ref: entry.ref} : {})});
      return entry.ref ? {...v, ref: entry.ref} : v;
    } catch (e) {
      if (identity) this.calls.delete(key);
      this.worldCalls.push({node: n.id, fn, args, ms: Date.now() - t0, t: this.now(), error: e.message});
      throw e;
    }
  }

  publish(n, {content, to}) {
    if (content == null) throw new Error('content is required');
    const text = typeof content === 'string' ? content : JSON.stringify(content);
    if (to != null && to !== '' && !this.nodes.has(to)) throw new Error(`no node ${to}`);
    const ref = `${n.id}.c${n.cps.length + 1}`;
    const {valid, invalid} = this.cites(text, n.id);
    this.artifacts.set(ref, {node: n.id, kind: 'cp', content: text, to: to || null, cites: valid, invalid, t: this.now()});
    n.cps.push(ref);
    for (const c of valid) this.edges.push({kind: 'cite', from: c.split('.')[0], to: n.id, ref, t: this.now()});
    if (to) this.edges.push({kind: 'msg', from: n.id, to, ref, t: this.now()});
    this.addLine({text: `${ref}${to ? ' → ' + to : ''} · ${this.lineText(text, valid)}`, kind: 'cp', subj: n.id, to: to || null, ref});
    let reopened = false;
    if (to) {
      const t = this.nodes.get(to);
      if (t.state === 'completed') {
        this.reopen(t, n.id, [this.lines.at(-1)]);
        reopened = true;
      } else if (t.state === 'failed' || t.state === 'cancelled') {
        throw new Error(`${to} is ${t.state}`);
      }
    }
    return {ref, reopened, versions: to ? this.nodes.get(to).results.length : undefined};
  }

  read(n, {ref, offset = 0, limit = 4000}) {
    let text;
    if (ref === 'run') {
      if (!['scoped', 'index', 'broadcast'].includes(this.cond.delivery)) throw new Error('the run index is not available in this run');
      text = this.indexLines(null).join('\n');
    } else if (/^n\d+$/.test(ref)) {
      const t = this.nodes.get(ref);
      if (!t) throw new Error(`no node ${ref}`);
      text = JSON.stringify({node: t.id, request: t.request, opener: t.opener, state: t.state, holders: [...t.holders],
        results: t.results, checkpoints: t.cps}, null, 1);
    } else if (/^n\d+\.trail$/.test(ref)) {
      const id = ref.split('.')[0];
      if (!this.nodes.has(id)) throw new Error(`no node ${id}`);
      text = this.cells.filter(c => c.node === id).map((c, i) => `--- cell ${i + 1} ---\n${c.code}\n--- output ---\n${c.output}`).join('\n\n') || '(no cells yet)';
    } else if (this.artifacts.has(ref)) {
      text = this.artifacts.get(ref).content;
    } else {
      throw new Error(`no ref ${ref}`);
    }
    this.reads.push({node: n.id, ref, t: this.now()});
    const total = text.length;
    const lim = Math.max(1, Math.min(+limit || 4000, 20000));
    const off = Math.max(0, +offset || 0);
    return {ref, text: text.slice(off, off + lim), total_chars: total, next_offset: Math.min(total, off + lim)};
  }
}
