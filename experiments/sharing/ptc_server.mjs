// One node's PTC cell server: an MCP stdio server with a single tool, run_cell.
// Cells run in a persistent vm context whose bindings call the run's harness over HTTP.
// After every cell, lines pending in the node's stream are appended to the output: the push at the turn boundary.

import vm from 'node:vm';
import http from 'node:http';
import readline from 'node:readline';

const URL_ = new URL(process.env.RUN_URL);
const NODE = process.env.NODE_ID;
const CELL_CAP = +(process.env.CELL_CAP || 30);
const CELL_MS = +(process.env.CELL_MS || 540000);
const MAX_OUT = 7000;
let cells = 0;

function post(op, args) {
  const body = JSON.stringify({node: NODE, op, args});
  return new Promise((resolve, reject) => {
    const req = http.request({hostname: URL_.hostname, port: URL_.port, path: '/call', method: 'POST',
      headers: {'content-type': 'application/json', 'content-length': Buffer.byteLength(body)}}, res => {
      let data = '';
      res.on('data', d => (data += d));
      res.on('end', () => {
        try {
          const m = JSON.parse(data);
          m.ok ? resolve(m.value) : reject(new Error(m.error));
        } catch (e) { reject(new Error('harness unreachable')); }
      });
    });
    req.setTimeout(0);
    req.on('error', () => reject(new Error('harness unreachable')));
    req.end(body);
  });
}

let logs = [];
const ctx = vm.createContext({
  console: {log: (...a) => logs.push(a.map(x => (typeof x === 'string' ? x : JSON.stringify(x))).join(' '))},
  __call: (op, args) => post(op, args),
  setTimeout, clearTimeout, Promise, JSON, Math, Date, Array, Object, String, Number, Boolean, RegExp, Map, Set, Error,
});
vm.runInContext(`
const call = (op, args) => __call(op, args);
globalThis.world = {
  search: q => call('world', {fn: 'search', args: [q]}),
  doc: id => call('world', {fn: 'doc', args: [id]}),
  series: name => call('world', {fn: 'series', args: [name]}),
};
globalThis.tools = {
  openNode: ({request} = {}) => call('openNode', {request}),
  nextNodeEvent: (a = {}) => call('next', a),
  closeNode: ({handle} = {}) => call('close', {node: handle}),
  publishCheckpoint: ({content, to} = {}) => call('publish', {content, to}),
  readArtifact: ({ref, offset, limit} = {}) => call('read', {ref, offset, limit}),
};
class Op {
  constructor(r) { this.node = r.node; this.disp = r.disp; this._r = r; }
  async result() {
    if (this._r.disp === 'reused') return {node: this.node, ref: this._r.ref, line: this._r.line, status: 'completed'};
    return call('await', {node: this.node, after: this._r.versions || 0});
  }
  next() { return call('nextAbout', {node: this.node}); }
  close() { return call('close', {node: this.node}); }
}
// An op is usable at once (op.result(), op.close(), op.next()), and await op gives op.node and op.disp.
function pendingOp(promise) {
  const p = Promise.resolve(promise).then(r => new Op(r));
  return {
    then: (a, b) => p.then(a, b),
    catch: b => p.catch(b),
    result: () => p.then(o => o.result()),
    next: () => p.then(o => o.next()),
    close: () => p.then(o => o.close()),
  };
}
globalThis.nodes = {
  open: request => pendingOp(tools.openNode({request})),
  run: request => pendingOp(tools.openNode({request})).result(),
  with: async (request, fn) => { const op = await nodes.open(request); try { return await fn(op); } finally { try { await op.close(); } catch (e) {} } },
  handle: id => pendingOp(call('versions', {node: id}).then(v => ({node: id, disp: 'held', versions: v.state === 'completed' ? v.versions - 1 : v.versions}))),
  next: () => tools.nextNodeEvent({}),
};
globalThis.read = async ref => {
  let text = '', offset = 0;
  for (;;) {
    const p = await tools.readArtifact({ref, offset, limit: 8000});
    text += p.text;
    if (p.next_offset >= p.total_chars) return text;
    offset = p.next_offset;
  }
};
globalThis.inspect = async ref => JSON.parse(await read(ref));
globalThis.load = async ref => JSON.parse(await read(ref));
`, ctx);

function show(v) {
  if (v === undefined) return '(no return value)';
  let s;
  try { s = typeof v === 'string' ? v : JSON.stringify(v, null, 1); } catch { s = String(v); }
  return s.length > MAX_OUT ? s.slice(0, MAX_OUT) + `\n… (${s.length - MAX_OUT} more characters)` : s;
}

async function runCell(code) {
  if (++cells > CELL_CAP) return {text: `Cell limit reached (${CELL_CAP}). Write your final message now.`, error: true};
  logs = [];
  const t0 = Date.now();
  let out, error = false;
  try {
    const fn = vm.runInContext(`(async () => {\n${code}\n})`, ctx, {filename: `cell-${cells}.js`});
    let timer;
    const v = await Promise.race([fn(), new Promise((_, rej) => (timer = setTimeout(() => rej(new Error(`cell timed out after ${Math.round(CELL_MS / 60000)} min`)), CELL_MS)))]);
    clearTimeout(timer);
    out = show(v);
  } catch (e) {
    error = true;
    out = `Error: ${e && e.message ? e.message : String(e)}`;
  }
  if (logs.length) out = `console:\n${logs.join('\n').slice(0, 3000)}\n\nreturned:\n${out}`;
  let pushed = '';
  try {
    const p = await post('pending', {});
    if (p.lines.length) pushed += `\n\n--- new lines in your stream ---\n${p.lines.join('\n')}`;
    if (p.index) pushed += `\n\n--- run index (* changed since your last cell) ---\n${p.index.join('\n')}`;
    pushed += `\n${p.left}`;
  } catch (e) { pushed = `\n\n(${e.message})`; }
  try { await post('cell', {code, output: out, ms: Date.now() - t0, error}); } catch {}
  return {text: out + pushed, error};
}

const send = m => process.stdout.write(JSON.stringify(m) + '\n');
const TOOL = {
  name: 'run_cell',
  description: 'Run a JavaScript cell in your sandbox. The code is the body of an async function: use await, and return a value to see it. Output includes any new lines in your stream.',
  inputSchema: {type: 'object', properties: {code: {type: 'string', description: 'JavaScript to run'}}, required: ['code']},
};
readline.createInterface({input: process.stdin}).on('line', async line => {
  let msg;
  try { msg = JSON.parse(line); } catch { return; }
  const {id, method, params} = msg;
  if (method === 'initialize') return send({jsonrpc: '2.0', id, result: {protocolVersion: params.protocolVersion, capabilities: {tools: {}}, serverInfo: {name: 'ptc', version: '1.0'}}});
  if (method === 'tools/list') return send({jsonrpc: '2.0', id, result: {tools: [TOOL]}});
  if (method === 'tools/call') {
    const r = await runCell(String((params.arguments || {}).code || ''));
    return send({jsonrpc: '2.0', id, result: {content: [{type: 'text', text: r.text}], isError: r.error}});
  }
  if (method === 'ping') return send({jsonrpc: '2.0', id, result: {}});
  if (id !== undefined && id !== null) send({jsonrpc: '2.0', id, error: {code: -32601, message: `unknown method ${method}`}});
});
