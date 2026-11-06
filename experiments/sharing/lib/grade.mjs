// Blind grading of a run's final answer by Opus 5.5 against the planted facts. The grader never sees the condition.

import {spawn} from 'node:child_process';
import {WORKFLOWS} from './world.mjs';
import {limitOf, waitForReset} from './limit.mjs';

const SYSTEM = 'You grade research answers against known ground truth. Judge each rubric item strictly and literally from the answer text alone: an item is met only if the answer clearly states it. Reply with JSON only.';

function ask(prompt, model) {
  return new Promise(resolve => {
    const p = spawn('claude', ['-p', '--model', model, '--output-format', 'json', '--strict-mcp-config', '--tools', '',
      '--setting-sources', '', '--system-prompt', SYSTEM], {stdio: ['pipe', 'pipe', 'pipe']});
    let out = '';
    p.stdout.on('data', d => (out += d));
    p.on('close', () => {
      try { resolve(JSON.parse(out.trim())); } catch { resolve(null); }
    });
    p.stdin.end(prompt);
  });
}

function lastJson(text) {
  const m = String(text || '').match(/\{[\s\S]*\}/g);
  if (!m) return null;
  for (const s of m.reverse()) { try { return JSON.parse(s); } catch {} }
  return null;
}

export async function grade(workflow, answer, {model = 'claude-opus-5-5'} = {}) {
  const wf = WORKFLOWS[workflow];
  if (!answer) return {score: 0, max: wf.rubric.length, items: [], cost: 0, note: 'no answer'};
  const prompt = `Question: ${wf.question}

Ground truth, known to the grader only:
${Object.entries(wf.planted).map(([k, v]) => `- ${k}: ${v}`).join('\n')}

Rubric items:
${wf.rubric.map((r, i) => `${i + 1}. ${r}`).join('\n')}

Answer to grade:
"""
${answer}
"""

Reply with JSON only: {"items": [{"n": 1, "met": true, "why": "short reason"}], "score": <items met>}`;
  for (let attempt = 0; attempt < 2; attempt++) {
    const d = await ask(prompt, model);
    const lim = limitOf(d);
    if (lim) { await waitForReset(lim.until, {model}); attempt--; continue; }
    const j = d && lastJson(d.result);
    if (j && Array.isArray(j.items)) {
      const met = j.items.filter(x => x.met === true).length;
      return {score: met, max: wf.rubric.length, items: j.items, cost: d.total_cost_usd || 0};
    }
  }
  return {score: null, max: wf.rubric.length, items: [], cost: 0, note: 'grader failed'};
}
