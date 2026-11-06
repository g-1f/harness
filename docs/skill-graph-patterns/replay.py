"""Replays of real runs from the sharing experiment, in the patterns player.

Usage: python3 replay.py [output.html]   (defaults to ../sharing-replays.html)

Each replay is one real run. Nodes, lines, holds, cites, reads and shared calls come from the run's state.json in
experiments/sharing/runs/, mapped onto authored steps: a step covers a span of real time, and its narration and
per-node notes are written by hand from the run's record. A line reaches a node at the end of that node's next cell,
the turn boundary where the harness appends it, or never, if the node runs no further cell.
"""

import html
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from core import layout  # noqa: E402
from replays import REPLAYS, PAGE  # noqa: E402

RUNS = HERE.parent.parent / 'experiments' / 'sharing' / 'runs'
DONE = ('completed', 'failed', 'cancelled')


class Stub:
    def __init__(self, nodes):
        self.nodes, self.user = nodes, False


def build(spec):
    d = RUNS / spec['run']
    st = json.loads((d / 'state.json').read_text())
    sm = json.loads((d / 'summary.json').read_text())
    steps = spec['steps']
    T = len(steps)
    bounds = [0.0] + [s[0] for s in steps]
    for a, b in zip(bounds, bounds[1:]):
        if b < a:
            raise ValueError(f"{spec['id']}: step times must not decrease ({a} then {b})")

    def tmap(r):
        if r is None:
            return None
        for k in range(T):
            a, b = bounds[k], bounds[k + 1]
            if r <= b or k == T - 1:
                f = 0 if b <= a else min(1.0, max(0.0, (r - a) / (b - a)))
                return round(k + 0.06 + 0.88 * f, 4)

    names = spec['names']
    by_id = {n['id']: n for n in st['nodes']}
    order = [n['id'] for n in st['nodes']]
    start_line = {l['subj']: l['i'] for l in st['lines'] if l['kind'] == 'open'}
    held = {n: {e['to'] for e in st['edges'] if e['kind'] == 'call' and e['from'] == n and e.get('disp') != 'reused'} for n in order}
    broadcast = sm['cond']['delivery'] == 'broadcast'

    def in_scope(nid, l):
        producer = l.get('by') or l.get('subj')
        if producer == nid and l['kind'] != 'reopen':
            return False
        if broadcast:
            return True
        return l.get('to') == nid or l.get('subj') in held[nid] or (l.get('subj') == nid and l.get('by') and l.get('by') != nid)

    cells = {n: sorted((c for c in st['cells'] if c['node'] == n), key=lambda c: c['t']) for n in order}

    lines = []
    for l in st['lines']:
        got, got_real = {}, {}
        for nid in order:
            if l['i'] <= start_line.get(nid, -1) or not in_scope(nid, l):
                continue
            nxt = next((c for c in cells[nid] if c['t'] >= l['t']), None)
            got[nid] = tmap(nxt['t']) if nxt else None
            got_real[nid] = round(nxt['t'], 1) if nxt else None
        row = dict(t=tmap(l['t']), text=l['text'], kind=l['kind'], subj=l.get('subj'), got=got, gotReal=got_real)
        for k in ('by', 'ref', 'to'):
            if l.get(k):
                row[k] = l[k]
        lines.append(row)

    arts = {ref: a for ref, a in st['artifacts'].items() if a['kind'] in ('result', 'cp')}

    def index_of(nid):
        f = d / 'nodes' / f'{nid}.prompts.txt'
        if not f.exists():
            return []
        m = re.search(r'Run index when you started:\n(.*?)(?:\n\n|\n=====|\Z)', f.read_text(), re.S)
        return [x for x in m.group(1).split('\n') if x.strip()] if m else []

    nodes = []
    for n in st['nodes']:
        nid = n['id']
        mine = sorted(((a['t'], ref, a) for ref, a in arts.items() if a['node'] == nid), key=lambda x: x[0])
        subs = [[tmap(n['states'][0][0]), nid]] + [[tmap(t), f"{nid} · {ref.split('.')[1]}"] for t, ref, _ in mine]
        nodes.append(dict(
            id=nid, name=names.get(nid, nid), task=n['request']['task'], skill=None, by=n['opener'], frm=n.get('from'),
            request=n['request'], t0=tmap(n['states'][0][0]), li=start_line[nid],
            states=[[tmap(t), s] for t, s in n['states']], subs=subs,
            cps=[tmap(t) for t, _, a in mine if a['kind'] == 'cp'], index=index_of(nid),
            reads=[[tmap(r['t']), r['ref']] for r in st['reads'] if r['node'] == nid],
        ))

    edges, pairs = [], set()
    calls = [e for e in st['edges'] if e['kind'] == 'call']
    for e in calls:
        edges.append(dict(kind='call', disp=e['disp'], **{'from': e['from']}, to=e['to'], t0=tmap(e['t']), t1=tmap(e.get('released'))))
    for e in st['edges']:
        if e['kind'] == 'cite':
            src, citing = e['from'], e['to']
            linked = any(c['from'] == citing and c['to'] == src for c in calls)
            if src != citing and not linked and (src, citing) not in pairs:
                pairs.add((src, citing))
                edges.append(dict(kind='cite', **{'from': src}, to=citing, t0=tmap(e['t']), t1=None))
        elif e['kind'] == 'msg':
            first = (e['from'], e['to']) not in pairs
            pairs.add((e['from'], e['to']))
            edges.append(dict(kind='msg', **{'from': e['from']}, to=e['to'], t0=tmap(e['t']), t1=None, trace=first))
        elif e['kind'] == 'data':
            t0 = tmap(e['t'])
            edges.append(dict(kind='read', **{'from': e['to']}, to=e['from'], t0=t0, t1=round(t0 + 0.6, 4)))
    for r in st['reads']:
        owner = r['ref'].split('.')[0]
        if re.fullmatch(r'n\d+', owner) and owner != r['node'] and owner in by_id:
            t0 = tmap(r['t'])
            edges.append(dict(kind='read', **{'from': owner}, to=r['node'], t0=t0, t1=round(t0 + 0.6, 4)))

    ripples = [[l['t'], l.get('by') or l['subj']] for l in lines if (l.get('by') or l.get('subj')) in by_id]
    def brief(text, n=320):
        head = text.strip().split('\n\n', 1)[0].replace('**', '').strip()
        return head if len(head) <= n else head[:n - 1].rstrip() + '…'
    artifacts = {ref: dict(t=tmap(a['t']), node=a['node'], kind=a['kind'], text=brief(a['content']), to=a.get('to'), cites=a.get('cites', []))
                 for ref, a in arts.items()}

    code = []
    for nid, which in spec.get('code', []):
        cs = cells[nid]
        picked = [cs[i]['code'] for i in which if i < len(cs)]
        res = [a for t, ref, a in sorted(((a['t'], ref, a) for ref, a in arts.items() if a['node'] == nid and a['kind'] == 'result'))]
        final = res[-1]['content'].strip().split('\n\n')[0] if res else None
        tab = dict(name=f'{nid} · {names.get(nid, nid)}', cells=picked, final=final)
        if res:
            tab['final_ref'] = [ref for ref, a in arts.items() if a is res[-1]][0]
        code.append(tab)

    pos, width, height = layout(Stub({n: dict(by=by_id[n]['opener'], pos=None) for n in order}), order, [])
    return dict(
        id=spec['id'], group='replay', title=spec['title'], summary=spec['summary'], run=sm['workflow'], uses=[],
        user=False, cap=16, big=False, wide=True, T=T,
        nodes=nodes, ghosts=[], edges=edges, lines=lines, ripples=ripples, artifacts=artifacts,
        steps=[dict(say=s[1], doing=[[k, v] for k, v in (s[2] if len(s) > 2 else {}).items()]) for s in steps],
        code=code, built={}, pos=pos, width=width, height=height,
        real=[[bounds[k], bounds[k + 1]] for k in range(T)],
        meta=dict(stage=spec['run'].split('/')[0], cond=sm['cond']['id'], seed=sm['seed'], wall=sm['wall'], cost=sm['cost']),
    )


def page(out):
    css = (HERE / 'style.css').read_text()
    head = (HERE / 'head.html').read_text()
    js = (HERE / 'renderer.js').read_text()
    data = {'replays': [build(s) for s in REPLAYS]}
    sections = []
    for s, r in zip(REPLAYS, data['replays']):
        m = r['meta']
        sections.append(f"""
  <section class="block" id="{s['id']}" aria-labelledby="{s['id']}-h">
    <div class="sec-head">
      <h2 id="{s['id']}-h">{html.escape(s['title'])}</h2>
      <p>{s['intro']}</p>
      <p class="note">Run <code>{html.escape(s['run'])}</code>: condition <code>{html.escape(m['cond'])}</code>, seed {m['seed']}, {m['wall']:.0f} s, ${m['cost']:.3f}.</p>
    </div>
    <div class="walk" id="{s['id']}-stage"></div>
    <div class="walk-code" id="{s['id']}-code" style="margin-top: 18px">{'<div class="panel-title">Cells the nodes ran</div>' if s.get('code') else ''}</div>
  </section>""")
    body = json.dumps(data, separators=(',', ':')).replace('</', '<\\/')
    doc = f"""{head}<style>[hidden]{{display:none!important}}</style>
<title>{html.escape(PAGE['title'])}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Recursive:slnt,wght,CASL,CRSV,MONO@-15..0,300..1000,0..1,0..1,0..1&display=swap" rel="stylesheet">
<style>{css}</style>
</head>
<body>
<div class="wrap">
  <header class="masthead">
    <h1>{html.escape(PAGE['title'])}</h1>
    {PAGE['lede']}
    <nav class="jump" aria-label="Replays">{''.join(f'<a href="#{s["id"]}">{html.escape(s["nav"])}</a>' for s in REPLAYS)}</nav>
    {PAGE['legend']}
  </header>
  {''.join(sections)}
  <footer class="made" id="made">
    {PAGE['footer']}
  </footer>
</div>
<script type="application/json" id="data">{body}</script>
<script>
{js}
</script>
</body>
</html>
"""
    out.write_text(doc)
    print(out, len(doc), 'bytes')


if __name__ == '__main__':
    page(Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent / 'sharing-replays.html')
