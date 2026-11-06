"""Assemble the v3 patterns page from the authored timelines: head, style, markup, compiled data and renderer.

Usage: python3 page.py [output.html]   (defaults to ../skill-graph-patterns.html)
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from core import compile_pattern  # noqa: E402
from patterns import PATTERNS  # noqa: E402
from walk import WALK  # noqa: E402

css = (HERE / 'style.css').read_text()
head = (HERE / 'head.html').read_text()

MARKUP = r"""
<div class="wrap">
  <header class="masthead">
    <h1>Callable Skill Graph Patterns</h1>
    <p class="lede">A node is one task: an atomic reasoning trace that runs a skill from the graph, or none. Nodes split the <em>what</em> into child nodes, stay aware of each other through one stream of lines each, and talk by publishing addressed artifacts. Everything on this page is written against six host calls.</p>
    <p class="lede-sub">This page describes v3, which is designed and not yet built. Every animation is hand-authored from the design and compiled by a script that checks it against the rules below, so the calls, lines, holds and versions follow v3's semantics; the timing is illustrative. Select any node to see exactly what it sees.</p>
    <nav class="jump" aria-label="Sections">
      <a href="#primitives">Primitives</a>
      <a href="#traversal">Traversal</a>
      <a href="#coordination">Coordination</a>
      <a href="#validation">Validation</a>
      <a href="#compositions">Compositions</a>
      <a href="#walk">Walkthrough: XLI LEAPS</a>
      <a href="#made">How this page was made</a>
    </nav>
    <div class="legend-block" aria-label="How to read the graphs">
      <div class="legend-row"><b>Nodes</b>
        <span class="lg"><svg width="16" height="16" viewBox="-8 -8 16 16"><circle r="6.5" fill="var(--cobalt)" stroke="var(--cobalt)" stroke-width="2"/></svg>working</span>
        <span class="lg"><svg width="16" height="16" viewBox="-8 -8 16 16"><circle r="6.5" fill="var(--cobalt-soft)" stroke="var(--cobalt)" stroke-width="2"/></svg>idle, waiting for lines</span>
        <span class="lg"><svg width="16" height="16" viewBox="-8 -8 16 16"><circle r="6.5" fill="var(--pine)" stroke="var(--pine)" stroke-width="2"/></svg>published its result</span>
        <span class="lg"><svg width="16" height="16" viewBox="-8 -8 16 16"><circle r="6.5" fill="var(--brick)" stroke="var(--brick)" stroke-width="2"/></svg>failed</span>
        <span class="lg"><svg width="16" height="16" viewBox="-8 -8 16 16"><circle r="6.5" fill="var(--surface)" stroke="var(--graphite)" stroke-width="2" stroke-dasharray="3 3"/></svg>cancelled</span>
        <span class="lg"><svg width="16" height="16" viewBox="-8 -8 16 16"><path d="M0-5L5 0 0 5-5 0Z" fill="var(--ochre)"/></svg>checkpoint</span>
        <span class="lg"><svg width="16" height="16" viewBox="-8 -8 16 16"><rect x="-6.5" y="-6.5" width="13" height="13" rx="3.5" fill="var(--plum-soft)" stroke="var(--plum)" stroke-width="2"/></svg>you</span>
        <span class="lg"><svg width="22" height="16" viewBox="-11 -8 22 16"><circle r="4" fill="none" stroke="var(--cobalt)" stroke-width="1.2"/><circle r="7.5" fill="none" stroke="var(--cobalt)" stroke-width="1" opacity="0.45"/></svg>a line reaching every stream</span>
      </div>
      <div class="legend-row"><b>Holding work</b>
        <span class="lg"><svg width="30" height="8" viewBox="0 0 30 8"><path d="M1 4H29" stroke="var(--edge)" stroke-width="2.4"/></svg>opened new work</span>
        <span class="lg"><svg width="30" height="8" viewBox="0 0 30 8"><path d="M1 4H29" stroke="var(--cobalt)" stroke-width="2.4" stroke-dasharray="7 5"/></svg>joined running work</span>
        <span class="lg"><svg width="30" height="8" viewBox="0 0 30 8"><path d="M1 4H29" stroke="var(--pine)" stroke-width="2.4" stroke-dasharray="1.5 5" stroke-linecap="round"/></svg>reused a result</span>
        <span class="lg"><svg width="30" height="8" viewBox="0 0 30 8"><path d="M1 4H29" stroke="var(--edge)" stroke-width="2" stroke-dasharray="9 3 2 3"/></svg>forked from a trail</span>
        <span class="lg">thick while held, thin once released</span>
      </div>
      <div class="legend-row"><b>Between nodes</b>
        <span class="lg"><svg width="30" height="8" viewBox="0 0 30 8"><path d="M1 4H29" stroke="var(--plum)" stroke-width="2"/></svg>addressed artifact (<code>to</code>)</span>
        <span class="lg"><svg width="30" height="8" viewBox="0 0 30 8"><path d="M1 4H29" stroke="var(--ochre)" stroke-width="1.6"/></svg>cites a ref inline</span>
        <span class="lg"><svg width="30" height="8" viewBox="0 0 30 8"><path d="M1 4H29" stroke="var(--muted)" stroke-width="1.6" stroke-dasharray="3 4"/></svg>read a record or trail</span>
      </div>
      <div class="legend-row"><b>Skill graph</b>
        <span class="lg"><svg width="44" height="16" viewBox="0 0 44 16"><path d="M1 8H26" stroke="var(--muted)" stroke-width="1.5" stroke-dasharray="4 4"/><circle cx="35" cy="8" r="6.5" fill="var(--surface)" stroke="var(--muted)" stroke-width="1.5" stroke-dasharray="3 3"/></svg>procedure read, not run</span>
        <span class="lg"><svg width="44" height="16" viewBox="0 0 44 16"><path d="M1 8H26" stroke="var(--rule)" stroke-width="1.5" stroke-dasharray="2 4"/><circle cx="35" cy="8" r="6.5" fill="var(--surface)" stroke="var(--rule)" stroke-width="1.5" stroke-dasharray="3 3"/></svg>linked in prose, not followed</span>
      </div>
    </div>
  </header>

  <section class="block" id="primitives" aria-labelledby="primitives-h">
    <div class="sec-head">
      <h2 id="primitives-h">Six host calls</h2>
      <p>These are the only operations the host implements for node code. Each exists because code alone cannot enforce its identity, lifetime or delivery. Nothing else is hard-coded: no summaries, no declared provenance, no reuse flags.</p>
    </div>
    <div class="prims">
      <div class="prim-group">
        <h3>Read</h3>
        <div class="prim"><code>readNode<span class="args">({node})</span></code><p>Load a skill's procedure, links and resources from the pinned registry. The read is recorded as consulted; nothing runs.</p></div>
        <div class="prim"><code>readArtifact<span class="args">({ref, offset, limit})</span></code><p>Read a bounded slice of any ref in the run: a checkpoint <code>n7.c3</code>, a result <code>n7.r2</code>, a node record <code>n7</code> with its exact request, a trail <code>n7.trail</code>, a message <code>you.m1</code>, or the index <code>run</code>.</p></div>
      </div>
      <div class="prim-group">
        <h3>Run</h3>
        <div class="prim"><code>openNode<span class="args">({request})</span></code><p>Start a node, join identical work that is running, or reuse its latest result if it finished. Returns at once. Failed work is never joined; <code>from</code> forks a trail.</p></div>
        <div class="prim"><code>nextNodeEvent<span class="args">({after})</span></code><p>The node's one stream: everything pending since the cursor, or wait if nothing is. The same lines are pushed at each turn boundary while the node is busy.</p></div>
        <div class="prim"><code>closeNode<span class="args">({handle})</span></code><p>Release this hold. Unfinished work is cancelled only when its last holder leaves.</p></div>
      </div>
      <div class="prim-group">
        <h3>Write</h3>
        <div class="prim"><code>publishCheckpoint<span class="args">({content, to})</span></code><p>Publish free-form content as the next checkpoint. Its first line becomes its line; refs written in it are its links. With <code>to</code> it is addressed to a node or to you, and a finished node is reopened by it.</p></div>
        <div class="prim result"><code>the final message</code><p>Not a call. When a node ends, its final message is stored as its next result: <code>n7.r1</code>, then <code>n7.r2</code> after a reopen. A node cannot end while it holds unfinished work.</p></div>
      </div>
    </div>

    <div class="two">
      <div>
        <div class="panel-title">What node code writes against</div>
        <div class="code" id="wrapper-code"></div>
      </div>
      <div>
        <div class="panel-title">When a request matches earlier work</div>
        <table class="reuse">
          <thead><tr><th>Identical work is</th><th><code>openNode</code></th><th>Line in every stream</th></tr></thead>
          <tbody>
            <tr><td>absent</td><td>starts a node</td><td><code>n3 opened n7 · …</code></td></tr>
            <tr><td>running</td><td>joins it: one more holder</td><td><code>n4 joined n7</code></td></tr>
            <tr><td>finished</td><td>reuses its latest result</td><td><code>n4 reused n7.r1</code></td></tr>
            <tr><td>failed or cancelled</td><td>starts a fresh node</td><td><code>n1 opened n8 · …</code></td></tr>
          </tbody>
        </table>
        <p class="note">Identity is the pinned registry plus <code>task</code>, <code>node</code>, <code>inputs</code>, <code>refs</code>, <code>from</code> and <code>key</code>. Who asks is not part of it. Similar wording is not identical: deciding that two tasks mean the same thing is the model's call, made by copying the exact request from the node record. A <code>key</code> makes a deliberate separate copy.</p>
        <div class="derived" aria-label="Patterns that are code, not calls">
          <span>fan-out: Promise.all</span><span>race: Promise.race + close</span><span>join: send the same request</span><span>fork: from</span><span>settle: to + inline refs</span><span>steer: to</span><span>ask you: to 'you'</span><span>retry: send it again</span><span>deltas: to a finished node</span>
        </div>
      </div>
    </div>

    <div class="two">
      <div>
        <div class="panel-title">One stream per node: n8's, from the walkthrough below</div>
<div class="stream-sample">__SAMPLE__</div>
      </div>
      <div>
        <div class="panel-title">What a node sees</div>
        <p class="note" style="margin-top:0">Every start, join, checkpoint, result, close and reopen in the run becomes one line in every node's stream: who, the first line of the content, and its ref into the run's database. Lines addressed to the node or about work it holds are marked. Nothing else enters its context: it reads an artifact, a record or a trail only when it chooses to. A node that opens late starts from the index, one line per node, and every batch ends with the budget left.</p>
      </div>
    </div>

    <div style="margin-top: 20px">
      <div class="panel-title">Helpers used by the patterns below</div>
      <div class="code" id="helpers-code"></div>
    </div>

    <div class="lists">
      <div>
        <div class="panel-title">The harness guarantees</div>
        <ul>
          <li>Exact-match sharing by identity; failed work is never joined.</li>
          <li>A start line is in every stream before <code>openNode</code> returns.</li>
          <li>One ordered stream per node, delivered at turn boundaries, never dropped.</li>
          <li>Work lives while anyone holds it; the last release cancels it.</li>
          <li>A node cannot end while it holds unfinished work.</li>
          <li>An addressed artifact reopens a finished node; its next result is a new version, and old versions never change.</li>
          <li>Inline refs are checked against the run; reads and trails are recorded.</li>
          <li>Caps on nodes, calls, depth and time, with the budget left in every batch.</li>
          <li>Any node can read any ref in its run; runs are walled off from each other.</li>
        </ul>
      </div>
      <div>
        <div class="panel-title">The model decides</div>
        <ul>
          <li>How to split a task into orthogonal tasks, and how deep to go.</li>
          <li>Whether to join, fork, cite, or run something separately.</li>
          <li>What to read, and when.</li>
          <li>Whom to address, and what to say.</li>
          <li>When to steer a child, and when to close it.</li>
          <li>How to settle a disagreement.</li>
          <li>Which results news touches, and what to reopen.</li>
        </ul>
      </div>
    </div>
  </section>

  <section class="block" id="traversal" aria-labelledby="traversal-h">
    <div class="sec-head">
      <h2 id="traversal-h">Traversal</h2>
      <p>How work spreads over the skill graph. Links in prose are hints; a node opens what it judges it needs, and refs written into tasks and results carry everything between nodes. Hover a primitive to find it in the code; select a node to see its stream.</p>
    </div>
    <div id="traversal-list"></div>
  </section>

  <section class="block" id="coordination" aria-labelledby="coordination-h">
    <div class="sec-head">
      <h2 id="coordination-h">Coordination</h2>
      <p>How nodes that can see each other cooperate: join what is already running, fork a trail for a different aspect, settle a disagreement by talking, steer a child, ask you, and reopen on news. Each is a few lines of code over the six calls, not a protocol.</p>
    </div>
    <div id="coordination-list"></div>
  </section>

  <section class="block" id="validation" aria-labelledby="validation-h">
    <div class="sec-head">
      <h2 id="validation-h">Validation and recovery</h2>
      <p>Checks are nodes over exact versions, and recovery is ordinary control flow. A failing verdict is a published artifact; what it means is the caller's decision.</p>
    </div>
    <div id="validation-list"></div>
  </section>

  <section class="block" id="compositions" aria-labelledby="compositions-h">
    <div class="sec-head">
      <h2 id="compositions-h">Compositions</h2>
      <p>The patterns above, running together. Select a pattern under "Built from" to highlight where it sits in the graph.</p>
    </div>
    <div id="composition-list"></div>
  </section>

  <section class="block" id="walk" aria-labelledby="walk-h">
    <div class="sec-head">
      <h2 id="walk-h">Walkthrough: should we add to our XLI LEAPS this month?</h2>
      <p>One plain question, no skills, and every capability on this page. Step through it with the arrows. The left panel says what every node is doing at that step; select a node to see exactly what it sees on the right: the index it started from, every line since, the ones addressed to it, and what it has read.</p>
    </div>
    <div class="walk" id="walk-stage"></div>
    <div class="walk-code" id="walk-code" style="margin-top: 18px">
      <div class="panel-title">Code from four of the nodes</div>
    </div>
  </section>

  <footer class="made" id="made">
    <h2>How this page was made</h2>
    <p>v3 is designed, not built. Every animation on this page is hand-authored from the design and compiled by a script that numbers refs, derives every line, hold and edge, and checks the timeline against v3's rules: ids follow opening order, refs are cited only after they exist, no node ends while it holds unfinished work, joins land only on running work and reuse only on finished work, and an addressed artifact reopens a finished node. Timing is illustrative: one step is one beat of the run, not a measured duration.</p>
    <p>The node code is what a model would write in its PTC cells. A gap between cells is where the model reads what came back and decides; no regex or rule stands in for that judgment. Data pulls and arithmetic happen inside nodes as ordinary tool calls and are not drawn.</p>
    <p>The previous version of this page replayed real runs of main's eight-call surface. It remains in the repository history at <code>fca89b5</code>.</p>
  </footer>
</div>
"""

data = {'patterns': [compile_pattern(p) for p in PATTERNS], 'walk': compile_pattern(WALK)}

# The sample stream is n8's real stream in the walkthrough, from its start through the settlement.
import html as _html
_w = data['walk']
_n8 = next(n for n in _w['nodes'] if n['id'] == 'n8')
_rows = [l for l in _w['lines'] if _n8['t0'] < l['t'] <= 7.999][:9]
_cap = _w['cap'] - sum(1 for n in _w['nodes'] if n['t0'] <= 7.999)
_sample = '\n'.join((f'<span class="to">{_html.escape(l["text"])}</span>' if l.get('to') == 'n8' else _html.escape(l['text'])) for l in _rows)
_sample += f'\n<span class="dim">left: {_cap} of {_w["cap"]} nodes</span>'
MARKUP = MARKUP.replace('__SAMPLE__', _sample)
js = (HERE / 'renderer.js').read_text()
body = json.dumps(data, separators=(',', ':')).replace('</', '<\\/')

html = f"""{head}<style>[hidden]{{display:none!important}}</style>
<title>Callable Skill Graph Patterns</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Recursive:slnt,wght,CASL,CRSV,MONO@-15..0,300..1000,0..1,0..1,0..1&display=swap" rel="stylesheet">
<style>{css}</style>
</head>
<body>
{MARKUP}
<script type="application/json" id="data">{body}</script>
<script>
{js}
</script>
</body>
</html>
"""
out = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent / 'skill-graph-patterns.html'
out.write_text(html)
print(out, len(html), 'bytes')
