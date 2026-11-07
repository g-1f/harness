// One-line summaries of every document and series, written once by a small model for readers of the run's question.
// The world is static, so a summary depends only on the workflow and the item; runs read them from summaries.json.
// Build or extend: node lib/summaries.mjs [workflow ...]   (skips items already summarized)

import fs from 'node:fs';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {WORKFLOWS, CORPUS} from './world.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const FILE = path.join(HERE, 'summaries.json');
export const MODEL = 'claude-haiku-4-5';
export const SUMMARIES = fs.existsSync(FILE) ? JSON.parse(fs.readFileSync(FILE, 'utf8')) : {};
export const summaryOf = (workflow, fn, arg) => (SUMMARIES[workflow] || {})[`${fn}:${arg}`] || null;

function ask(prompt) {
  return new Promise(resolve => {
    const p = spawn('claude', ['-p', '--model', MODEL, '--output-format', 'json', '--tools', '', '--setting-sources', '', '--max-turns', '1',
      '--system-prompt', 'You write one-line summaries of research items for analysts. Reply with the line only.'], {stdio: ['pipe', 'pipe', 'pipe']});
    let out = '';
    p.stdout.on('data', d => (out += d));
    p.on('close', () => { try { resolve(JSON.parse(out.trim())); } catch { resolve(null); } });
    p.stdin.end(prompt);
  });
}

function itemText(fn, id, item) {
  if (fn === 'doc') return `${item.title}\n${item.body}`;
  return `Series ${id} (${item.unit}): ${item.desc}. Points: ${item.points.map(([k, v]) => `${k} ${v}`).join(', ')}`;
}

async function build(workflows) {
  let cost = 0;
  for (const wf of workflows) {
    const corpus = CORPUS[wf];
    const out = (SUMMARIES[wf] ||= {});
    const items = [...corpus.docs.map(d => ['doc', d.id, d]), ...Object.entries(corpus.series || {}).map(([k, s]) => ['series', k, s])];
    for (const [fn, id, item] of items) {
      if (out[`${fn}:${id}`]) continue;
      const prompt = `Analysts in this run are working on: ${WORKFLOWS[wf].question}\n\nWrite one line, at most 150 characters, stating the most important fact in the item below. Use the item's own names and figures.\n\nItem:\n${itemText(fn, id, item)}`;
      const d = await ask(prompt);
      if (!d || d.is_error) { console.log(`failed ${wf} ${fn}:${id}`); continue; }
      out[`${fn}:${id}`] = String(d.result).trim().replace(/\s+/g, ' ');
      cost += d.total_cost_usd || 0;
      console.log(`${wf} ${fn}:${id} · ${out[`${fn}:${id}`]}`);
    }
    fs.writeFileSync(FILE, JSON.stringify(SUMMARIES, null, 1));
  }
  console.log(`summaries cost $${cost.toFixed(3)}`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  await build(process.argv.slice(2).length ? process.argv.slice(2) : Object.keys(WORKFLOWS));
}
