# Patterns page generator

[`../skill-graph-patterns.html`](../skill-graph-patterns.html) is generated from the timelines authored here. Edit a timeline, rebuild, and the compiler checks it against v3's rules before anything is written.

| File | What it holds |
|---|---|
| `patterns.py` | The 19 patterns, authored on the existing skill graph |
| `walk.py` | The skill-free XLI LEAPS walkthrough |
| `core.py` | The compiler: numbers refs, derives every line, hold, edge and state, builds each node's starting index, lays out the graph, and rejects timelines that break v3's rules |
| `page.py` | Assembles the page from `head.html`, `style.css`, the markup, the compiled data and `renderer.js` |
| `renderer.js` | The players: graph, transport, step notes, and each node's stream |
| `tests/` | Playwright checks: step every pattern forward and back and select every node (`test_page.js`), page width (`overflow.js`), autoplay (`autoplay.js`), screenshots (`shots.js`) |

The compiler rejects a timeline when:
- node ids do not follow opening order
- a ref is cited before it exists
- a node ends while it holds unfinished work
- a join lands on work that is not running, or a reuse on work that has not finished
- a node publishes, idles or fails while it is not running
- anything is still running when the timeline ends

An addressed checkpoint to a finished node reopens it automatically, with the sender as holder.

Build and check:

```sh
python3 docs/skill-graph-patterns/page.py
node docs/skill-graph-patterns/tests/test_page.js "$PWD/docs/skill-graph-patterns.html"
```

The tests need Node with Playwright and Chromium.
