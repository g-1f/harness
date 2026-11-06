"""Compile hand-authored v3 timelines into page data, enforcing the v3 rules.

A pattern is a list of steps. Each step holds events; the compiler assigns times,
numbers refs (n5.c1, n5.r2, you.m1), derives lines, holds, edges, states and the
index each node starts from, and raises if the timeline breaks a v3 rule.
"""

import re
from collections import defaultdict

REF = re.compile(r'\b(?:n\d+\.(?:c\d+|r\d+|trail)|you\.m\d+)\b')
FIRST = 92            # characters of an artifact's first line shown in a line
GAP, ROW, MX, MT = 104, 132, 64, 58
R = 15


TAIL = re.compile(r'\s*\((?:\s*(?:n\d+\.(?:c\d+|r\d+|trail)|you\.m\d+)\s*,?)+\)\.?\s*$')


def line_text(text, refs):
    head = text.strip().split('\n', 1)[0]
    if refs:
        head = TAIL.sub('', head).rstrip(' ;,')
    out = first_line(head)
    return out + (f" · cites {', '.join(refs)}" if refs else '')


def first_line(text, n=FIRST):
    line = text.strip().split('\n', 1)[0].strip()
    return line if len(line) <= n else line[: n - 1].rstrip() + '…'


class AuthoringError(ValueError):
    pass


class Pattern:
    def __init__(self, id, group, title, summary, run, uses, *, user=False, cap=32,
                 big=False, wide=False):
        self.id, self.group, self.title, self.summary, self.run = id, group, title, summary, run
        self.uses, self.user, self.cap, self.big, self.wide = uses, user, cap, big, wide
        self.nodes, self.steps, self.pre, self.code, self.built = {}, [], [], [], {}

    def N(self, id, name, task, *, skill=None, by=None, inputs=None, frm=None, key=None,
          refs=None, pos=None):
        if id in self.nodes:
            raise AuthoringError(f'{self.id}: duplicate node {id}')
        self.nodes[id] = dict(id=id, name=name, task=task, skill=skill, by=by, inputs=inputs,
                              frm=frm, key=key, refs=refs, pos=pos)
        return id

    def step(self, say, ev, doing=None):
        self.steps.append(dict(say=say, ev=ev, doing=doing or {}))

    def tab(self, name, cells, final=None):
        self.code.append(dict(name=name, cells=cells, final=final))


def request_of(node):
    req = {'task': node['task']}
    for k in ('node', 'inputs', 'refs', 'from', 'key'):
        v = node['skill'] if k == 'node' else node['frm'] if k == 'from' else node.get(k)
        if v:
            req[k] = v
    return req


def compile_pattern(p):
    nodes = p.nodes
    timeline = [(-1.0, ev) for ev in p.pre]
    for k, st in enumerate(p.steps):
        items = st['ev']
        n = len(items)
        for i, item in enumerate(items):
            t = k + (0.3 if n == 1 else 0.12 + 0.72 * i / (n - 1))
            group = item[1] if item[0] == 'par' else [item]
            for ev in group:
                timeline.append((round(t, 4), ev))

    state, opened, finished_at = {}, {}, {}
    st_tl, sub_tl, cps = defaultdict(list), defaultdict(list), defaultdict(list)
    cnt_c, cnt_r = defaultdict(int), defaultdict(int)
    cnt_m = 0
    holders, holding = defaultdict(set), defaultdict(set)
    artifacts, lines, edges, ripples, ghosts, reads = {}, [], [], [], [], defaultdict(list)
    call_edge = {}
    index_at = {}
    start_line = {}
    order = []
    msg_pairs, cite_pairs = set(), set()

    def err(msg):
        raise AuthoringError(f'{p.id}: {msg}')

    def set_state(nid, t, s):
        state[nid] = s
        st_tl[nid].append([t, s])

    def latest(nid):
        if cnt_r[nid]:
            return f'{nid}.r{cnt_r[nid]}'
        if cnt_c[nid]:
            return f'{nid}.c{cnt_c[nid]}'
        return None

    def set_sub(nid, t):
        ref = latest(nid)
        sub_tl[nid].append([t, f"{nid} · {ref.split('.')[1]}" if ref else nid])

    def live(nid):
        return state.get(nid) in ('running', 'waiting')

    def act(nid, t):
        if nid in nodes and state.get(nid) == 'waiting':
            set_state(nid, t, 'running')

    def line(t, text, kind, subj, **kw):
        lines.append(dict(t=t, text=text, kind=kind, subj=subj, **kw))

    def name_of(nid):
        return 'you' if nid == 'you' else nodes[nid]['name']

    def ref_exists(ref, t):
        if ref in artifacts:
            return artifacts[ref]['t'] <= t
        base, _, part = ref.partition('.')
        if part == 'trail' or not part:
            return base in opened and opened[base] <= t
        return False

    def node_of_ref(ref):
        return ref.split('.', 1)[0]

    def release(holder, target, t):
        if holder in holders[target]:
            holders[target].discard(holder)
            holding[holder].discard(target)
            e = call_edge.get((holder, target))
            if e is not None and edges[e]['t1'] is None:
                edges[e]['t1'] = t

    def terminal(nid, t):
        for h in list(holders[nid]):
            release(h, nid, t)

    def cancel(nid, t):
        set_state(nid, t, 'cancelled')
        finished_at[nid] = t
        line(t, f'{nid} cancelled · no holders left', 'cancel', nid)
        ripples.append([t, nid])
        terminal(nid, t)
        for child in list(holding[nid]):
            release(nid, child, t)
            if live(child) and not holders[child]:
                cancel(child, round(t + 0.04, 4))

    def reopen(target, sender, t):
        set_state(target, round(t + 0.06, 4), 'running')
        holders[target].add(sender)
        if sender in nodes:
            holding[sender].add(target)
        line(round(t + 0.06, 4), f'{target} reopened · held by {sender}', 'reopen', target, by=sender)
        sub_tl[target].append([round(t + 0.06, 4), f'{target} · r{cnt_r[target]} → r{cnt_r[target] + 1}'])

    def deliver(sender, to, t):
        if to == 'you':
            if not p.user:
                err('message to you, but the pattern has no user node')
        elif to not in opened:
            err(f'message to unopened {to}')
        elif state[to] == 'completed':
            reopen(to, sender, t)
        elif state[to] == 'waiting':
            set_state(to, round(t + 0.08, 4), 'running')
        elif state[to] in ('failed', 'cancelled'):
            err(f'message to {state[to]} node {to}')
        edges.append(dict(kind='msg', **{'from': sender}, to=to, t0=t, t1=None,
                          trace=(sender, to) not in msg_pairs))
        msg_pairs.add((sender, to))

    def with_refs(text, refs):
        found = REF.findall(text)
        missing = [r for r in refs if r not in found]
        if missing:
            text = text.rstrip() + ' (' + ', '.join(missing) + ')'
        return text, list(dict.fromkeys(found + list(refs)))

    def cite(citing, refs, t):
        for ref in refs:
            if not ref_exists(ref, t):
                err(f'{citing} cites {ref} before it exists')
            src = node_of_ref(ref)
            # Draw a cite only where no other edge already connects the pair: a parent citing a child it held,
            # a fork citing its source trail, or a node citing a message it was sent are already visible.
            shown = any((e['kind'] == 'fork' and e['from'] == src and e['to'] == citing) or
                        (e['kind'] == 'call' and e['from'] == citing and e['to'] == src) or
                        (e['kind'] == 'msg' and e['from'] == src and e['to'] == citing) for e in edges)
            if src != citing and not shown and (src, citing) not in cite_pairs:
                cite_pairs.add((src, citing))
                edges.append(dict(kind='cite', **{'from': src}, to=citing, t0=t, t1=None))

    for t, ev in sorted(timeline, key=lambda x: x[0]):
        kind = ev[0]
        if kind == 'open':
            by, nid = ev[1], ev[2]
            disp = ev[3] if len(ev) > 3 else 'started'
            if by is not None:
                act(by, t)
            if disp == 'started':
                if nid not in nodes:
                    err(f'open of undefined node {nid}')
                if nid in opened:
                    err(f'{nid} opened twice')
                expect = f'n{len(order) + 1}'
                if nid != expect:
                    err(f'node ids follow opening order: got {nid}, expected {expect}')
                node = nodes[nid]
                if node['by'] != by:
                    err(f"{nid}.by is {node['by']} but opened by {by}")
                index_at[nid] = list(order)
                order.append(nid)
                opened[nid] = t
                set_state(nid, t, 'running')
                set_sub(nid, t)
                if by is not None:
                    holders[nid].add(by)
                    holding[by].add(nid)
                    edges.append(dict(kind='call', disp='started', **{'from': by}, to=nid, t0=t, t1=None))
                    call_edge[(by, nid)] = len(edges) - 1
                frm = node['frm']
                if frm:
                    if frm not in opened or opened[frm] > t:
                        err(f'{nid} forks from {frm} before it exists')
                    edges.append(dict(kind='fork', **{'from': frm}, to=nid, t0=t, t1=None))
                task_refs = REF.findall(node['task'])
                if task_refs:
                    cite(nid, task_refs, t)
                start_line[nid] = len(lines)
                head = f"{by} opened {nid}" if by else f"the run opened {nid}"
                if frm:
                    head += f' from {frm}'
                tag = f" · {node['skill']}" if node['skill'] else ''
                line(t, f"{head}{tag} · {first_line(node['task'], 70)}", 'open', nid, by=by)
                ripples.append([t, nid])
            elif disp == 'joined':
                if not live(nid):
                    err(f'{by} joins {nid}, which is {state.get(nid)}')
                holders[nid].add(by)
                holding[by].add(nid)
                edges.append(dict(kind='call', disp='joined', **{'from': by}, to=nid, t0=t, t1=None))
                call_edge[(by, nid)] = len(edges) - 1
                line(t, f'{by} joined {nid}', 'join', nid, by=by)
                ripples.append([t, by])
            elif disp == 'reused':
                if state.get(nid) != 'completed':
                    err(f'{by} reuses {nid}, which is {state.get(nid)}')
                edges.append(dict(kind='call', disp='reused', **{'from': by}, to=nid, t0=t, t1=t))
                line(t, f'{by} reused {latest(nid)}', 'reuse', nid, by=by)
                ripples.append([t, by])
            else:
                err(f'unknown disposition {disp}')
        elif kind == 'cp':
            nid, text = ev[1], ev[2]
            to = ev[3] if len(ev) > 3 else None
            refs = ev[4] if len(ev) > 4 else ()
            if not live(nid):
                err(f'{nid} publishes while {state.get(nid)}')
            text, refs = with_refs(text, refs)
            act(nid, t)
            cnt_c[nid] += 1
            ref = f'{nid}.c{cnt_c[nid]}'
            artifacts[ref] = dict(t=t, node=nid, kind='cp', text=text, to=to, cites=list(refs))
            cps[nid].append(t)
            set_sub(nid, t)
            cite(nid, refs, t)
            arrow = f' → {to}' if to else ''
            line(t, f'{ref}{arrow} · {line_text(text, refs)}', 'cp', nid, ref=ref, to=to)
            ripples.append([t, nid])
            if to:
                deliver(nid, to, t)
        elif kind == 'msg':
            sender, to, text = ev[1], ev[2], ev[3]
            refs = ev[4] if len(ev) > 4 else ()
            if sender != 'you':
                err('msg events are for you; nodes publish with cp')
            text, refs = with_refs(text, refs)
            cite('you', refs, t) if refs else None
            cnt_m += 1
            ref = f'you.m{cnt_m}'
            artifacts[ref] = dict(t=t, node='you', kind='msg', text=text, to=to, cites=list(refs))
            line(t, f'{ref} → {to} · {first_line(text)}', 'msg', 'you', ref=ref, to=to)
            ripples.append([t, 'you'])
            deliver('you', to, t)
        elif kind == 'result':
            nid, text = ev[1], ev[2]
            refs = ev[3] if len(ev) > 3 else ()
            if not live(nid):
                err(f'{nid} finishes while {state.get(nid)}')
            text, refs = with_refs(text, refs)
            open_kids = [c for c in holding[nid] if live(c)]
            if open_kids:
                err(f'{nid} writes its final message while holding open {open_kids}')
            act(nid, t)
            cnt_r[nid] += 1
            ref = f'{nid}.r{cnt_r[nid]}'
            artifacts[ref] = dict(t=t, node=nid, kind='result', text=text, cites=list(refs))
            cite(nid, refs, t)
            set_state(nid, t, 'completed')
            finished_at[nid] = t
            set_sub(nid, t)
            line(t, f'{ref} · {line_text(text, refs)}', 'result', nid, ref=ref)
            ripples.append([t, nid])
            terminal(nid, t)
        elif kind == 'idle':
            if not live(ev[1]):
                err(f'{ev[1]} idles while {state.get(ev[1])}')
            set_state(ev[1], t, 'waiting')
        elif kind == 'wake':
            set_state(ev[1], t, 'running')
        elif kind == 'read':
            reader, ref = ev[1], ev[2]
            if not ref_exists(ref, t):
                err(f'{reader} reads {ref} before it exists')
            act(reader, t)
            reads[reader].append([t, ref])
            src = node_of_ref(ref)
            if src != reader:
                edges.append(dict(kind='read', **{'from': src}, to=reader, t0=t, t1=round(t + 0.75, 4)))
        elif kind == 'close':
            by, nid = ev[1], ev[2]
            if by not in holders[nid]:
                err(f'{by} closes {nid} without holding it')
            act(by, t)
            release(by, nid, t)
            line(t, f'{by} closed {nid}', 'close', nid, by=by)
            if live(nid) and not holders[nid]:
                cancel(nid, round(t + 0.05, 4))
        elif kind == 'fail':
            nid, text = ev[1], ev[2]
            if not live(nid):
                err(f'{nid} fails while {state.get(nid)}')
            set_state(nid, t, 'failed')
            finished_at[nid] = t
            line(t, f'{nid} failed · {text}', 'fail', nid)
            ripples.append([t, nid])
            terminal(nid, t)
            for child in list(holding[nid]):
                release(nid, child, t)
                if live(child) and not holders[child]:
                    cancel(child, round(t + 0.04, 4))
        elif kind == 'ghost':
            src, skill, gkind = ev[1], ev[2], ev[3]
            gid = f'g{len(ghosts) + 1}'
            ghosts.append(dict(id=gid, skill=skill, kind=gkind, **{'from': src}, t=t))
            edges.append(dict(kind='ghost', gkind=gkind, **{'from': src}, to=gid, t0=t, t1=None))
            act(src, t)
        else:
            err(f'unknown event {kind}')

    # A node's starting index: one line per node already open, with its state and latest ref.
    def state_at(nid, t):
        s = None
        for tt, ss in st_tl[nid]:
            if tt <= t:
                s = ss
        return s

    def latest_at(nid, t):
        mine = [(a['t'], ref, a['kind']) for ref, a in artifacts.items() if a['node'] == nid and a['t'] < t]
        results = [m for m in mine if m[2] == 'result']
        pick = max(results or mine, default=None)
        return pick[1] if pick else None

    for nid, prior in index_at.items():
        t = opened[nid]
        rows = []
        for x in prior:
            s = state_at(x, t)
            word = {'running': 'running', 'waiting': 'idle', 'completed': 'done',
                    'failed': 'failed', 'cancelled': 'cancelled'}.get(s, s)
            ref = latest_at(x, t)
            rows.append(f"{x} · {nodes[x]['name']} · {word}" + (f' · {ref}' if ref else ''))
        index_at[nid] = rows

    unfinished = [n for n in order if live(n)]
    if unfinished and not p.__dict__.get('allow_open'):
        err(f'nodes left running at the end: {unfinished}')
    for k, st in enumerate(p.steps):
        for nid in st['doing']:
            if nid != 'you' and nid not in nodes:
                err(f'step {k + 1} notes unknown node {nid}')

    for e in edges:
        for end in (e['from'], e['to']):
            if end != 'you' and end not in nodes and not end.startswith('g'):
                err(f'edge to unknown {end}')

    for tab in p.code:
        nid = tab['name'].split()[0]
        results = [(a['t'], ref, a['text']) for ref, a in artifacts.items() if a['node'] == nid and a['kind'] == 'result']
        if tab.get('final') and results:
            match = [r for r in sorted(results) if r[2][:28] == tab['final'][:28]]
            tab['final_ref'] = (match or sorted(results))[-1][1]
    pos, width, height = layout(p, order, ghosts)
    return dict(
        id=p.id, group=p.group, title=p.title, summary=p.summary, run=p.run, uses=p.uses,
        user=p.user, cap=p.cap, big=p.big, wide=p.wide, T=len(p.steps),
        nodes=[dict(id=n, name=nodes[n]['name'], task=nodes[n]['task'], skill=nodes[n]['skill'],
                    by=nodes[n]['by'], frm=nodes[n]['frm'], request=request_of(nodes[n]),
                    t0=opened[n], li=start_line[n], states=st_tl[n], subs=sub_tl[n], cps=cps[n],
                    index=index_at[n], reads=reads[n]) for n in order],
        ghosts=ghosts, edges=edges, lines=lines, ripples=ripples,
        artifacts={k: v for k, v in artifacts.items()},
        steps=[dict(say=s['say'], doing=[[n, d] for n, d in s['doing'].items()]) for s in p.steps],
        code=p.code, built=p.built, pos=pos, width=width, height=height,
    )


def layout(p, order, ghosts):
    nodes = p.nodes
    pos = {}
    manual = all(nodes[n]['pos'] is not None for n in order)
    if manual:
        for n in order:
            c, r = nodes[n]['pos']
            pos[n] = [c * GAP, r * ROW]
        if p.user:
            pos['you'] = list(p.user_pos) if hasattr(p, 'user_pos') else [-GAP, 0]
        for g in ghosts:
            if g.get('pos'):
                pos[g['id']] = [g['pos'][0] * GAP, g['pos'][1] * ROW]
    else:
        depth = {}

        def d_of(n):
            if n in depth:
                return depth[n]
            by = nodes[n]['by']
            depth[n] = 0 if by in (None, 'you') else d_of(by) + 1
            return depth[n]

        items = [(n, d_of(n), i) for i, n in enumerate(order)]
        items += [(g['id'], d_of(g['from']) + 1, 1000 + i) for i, g in enumerate(ghosts)]
        parents = {it[0]: set() for it in items}
        for n in order:
            if nodes[n]['by'] not in (None, 'you'):
                parents[n].add(nodes[n]['by'])
        for g in ghosts:
            parents[g['id']].add(g['from'])
        layers = defaultdict(list)
        for it in items:
            layers[it[1]].append(it)
        y = 0
        for d in sorted(layers):
            layer = layers[d]

            def bary(it):
                xs = [pos[q][0] for q in parents[it[0]] if q in pos]
                return sum(xs) / len(xs) if xs else 0

            layer.sort(key=lambda it: (bary(it), it[2]))
            row = [it[0] for it in layer]
            if d == 0 and p.user:
                row = ['you'] + row
            chunks = [row[i:i + 6] for i in range(0, len(row), 6)]
            for ci, chunk in enumerate(chunks):
                if ci:
                    y += 100
                gap = {2: 190, 3: 165, 4: 135}.get(len(chunk), GAP)
                for k, n in enumerate(chunk):
                    pos[n] = [(k - (len(chunk) - 1) / 2) * gap, y]
            y += ROW
    xs = [v[0] for v in pos.values()]
    ys = [v[1] for v in pos.values()]
    minx, maxx, maxy = min(xs), max(xs), max(ys)
    for v in pos.values():
        v[0] = round(v[0] - minx + MX + 20, 1)
        v[1] = round(v[1] + MT, 1)
    width = round(maxx - minx + 2 * MX + 40)
    height = round(maxy + MT + 74)
    return pos, width, height
