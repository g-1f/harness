// Plan usage limits. A claude -p session that hits the plan's limit exits at once with a 429 result such as
// "You've hit your 5-hour limit · resets 9:40am (UTC)". A run touched by it is void: the stage drops it, waits, and runs it again.

import {spawn} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

export function limitOf(d) {
  if (!d) return null;
  if (d.api_error === 'usage_limit_reached' || (d.is_error && d.api_error_status === 429)) return {until: resetAt(d.result), text: d.result};
  return null;
}

const MONTHS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'];

// Reset time from the limit text, plus a minute of margin. Unreadable text waits 20 minutes and probes again.
export function resetAt(text, now = Date.now()) {
  const s = String(text || '');
  const m = s.match(/resets\s+(?:([A-Za-z]{3})[a-z]*\s+(\d{1,2}),?\s+(?:at\s+)?)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)\s*\(UTC\)/i);
  if (!m) return now + 20 * 60 * 1000;
  const d = new Date(now);
  let h = +m[3] % 12;
  if (/pm/i.test(m[5])) h += 12;
  let month = d.getUTCMonth(), day = d.getUTCDate();
  if (m[1] && MONTHS.includes(m[1].toLowerCase())) { month = MONTHS.indexOf(m[1].toLowerCase()); day = +m[2]; }
  const t = new Date(Date.UTC(d.getUTCFullYear(), month, day, h, +(m[4] || 0)));
  if (!m[1] && t.getTime() <= now) t.setUTCDate(t.getUTCDate() + 1);
  if (m[1] && t.getTime() < now - 864e5) t.setUTCFullYear(t.getUTCFullYear() + 1);
  return t.getTime() + 60 * 1000;
}

function probe(model) {
  return new Promise(resolve => {
    const p = spawn('claude', ['-p', '--model', model, '--output-format', 'json', '--tools', '', '--setting-sources', '', '--max-turns', '1'],
      {stdio: ['pipe', 'pipe', 'pipe']});
    let out = '';
    p.stdout.on('data', x => (out += x));
    p.on('close', () => { try { resolve(JSON.parse(out.trim())); } catch { resolve(null); } });
    p.stdin.end('Reply with the single word ok.');
  });
}

// Sleep until the reset, then probe until a call goes through.
export async function waitForReset(until, {model = 'claude-sonnet-5-5', log = console.log} = {}) {
  for (;;) {
    const ms = Math.max(0, until - Date.now());
    log(`usage limit: waiting ${Math.round(ms / 60000)} min, until ${new Date(until).toISOString()}`);
    await new Promise(r => setTimeout(r, ms));
    const d = await probe(model);
    const l = limitOf(d);
    if (!l && d && !d.is_error) return;
    until = l ? l.until : Date.now() + 10 * 60 * 1000;
  }
}

// Did any session in a finished run hit the limit? Covers runs recorded before the run marked it itself.
export function runHitLimit(dir) {
  const nd = path.join(dir, 'nodes');
  if (!fs.existsSync(nd)) return false;
  return fs.readdirSync(nd).filter(f => f.endsWith('.exits.jsonl'))
    .some(f => fs.readFileSync(path.join(nd, f), 'utf8').includes('usage_limit_reached'));
}
