"""The replays shown on sharing-replays.html: which real runs, and the narration written from each run's record.

A step is (end time in seconds, what happened, {node: what it is doing}). The step covers real time from the previous
step's end to its own; every event in that span plays inside it, in order.
"""

PAGE = dict(
    title='Sharing in real runs',
    lede="""<p class="lede">Replays of real runs from the sharing experiment. Each node is a live Sonnet 5.5 session working through PTC code cells against a fictional sandbox, and every line, hold, cite, read and shared call shown here is taken from the run's record.</p>
    <p class="lede-sub">The steps and notes are written by hand from that record. The clock shows the run's own seconds. Select a node to see its stream as it actually received it: a line reaches a node at the end of its next cell, is <em>pending</em> until then, and <em>never arrived</em> if the node finished first.</p>""",
    legend="""<div class="legend-block" aria-label="How to read the graphs">
      <div class="legend-row"><b>Nodes</b>
        <span class="lg"><svg width="16" height="16" viewBox="-8 -8 16 16"><circle r="6.5" fill="var(--cobalt)" stroke="var(--cobalt)" stroke-width="2"/></svg>working</span>
        <span class="lg"><svg width="16" height="16" viewBox="-8 -8 16 16"><circle r="6.5" fill="var(--cobalt-soft)" stroke="var(--cobalt)" stroke-width="2"/></svg>waiting on children or lines</span>
        <span class="lg"><svg width="16" height="16" viewBox="-8 -8 16 16"><circle r="6.5" fill="var(--pine)" stroke="var(--pine)" stroke-width="2"/></svg>published its result</span>
        <span class="lg"><svg width="16" height="16" viewBox="-8 -8 16 16"><path d="M0-5L5 0 0 5-5 0Z" fill="var(--ochre)"/></svg>checkpoint</span>
      </div>
      <div class="legend-row"><b>Between nodes</b>
        <span class="lg"><svg width="30" height="8" viewBox="0 0 30 8"><path d="M1 4H29" stroke="var(--edge)" stroke-width="2.4"/></svg>opened and holds</span>
        <span class="lg"><svg width="30" height="8" viewBox="0 0 30 8"><path d="M1 4H29" stroke="var(--plum)" stroke-width="2"/></svg>addressed checkpoint</span>
        <span class="lg"><svg width="30" height="8" viewBox="0 0 30 8"><path d="M1 4H29" stroke="var(--ochre)" stroke-width="1.6"/></svg>cites a ref</span>
        <span class="lg"><svg width="30" height="8" viewBox="0 0 30 8"><path d="M1 4H29" stroke="var(--muted)" stroke-width="1.6" stroke-dasharray="3 4"/></svg>read a ref, or joined or reused a call</span>
      </div>
    </div>""",
    footer="""<h2>How this page was made</h2>
    <p>Every run is replayed from its <code>state.json</code> in <code>experiments/sharing/runs/</code>: node states, holds, lines, artifacts, cites, reads and shared calls are the harness's own record, mapped onto hand-written steps. Within a step, events keep their real order and spacing. A line's arrival is the end of the receiving node's next cell, which is when the harness appended it to that cell's output.</p>
    <p>The experiment, its stages and its findings are in <code>experiments/sharing/</code>. The design these runs exercise is v3, described on the patterns page.</p>""",
)

REPLAYS = [
    dict(
        id='miss', nav='Contradiction: 0.1 s', run='stage1/conflict-broadcast-s101',
        title='The fire arrives 0.1 s too late',
        summary='Stage 1, broadcast. The disclosures branch reads the release that explains the shipment drop 0.1 s after the shipments branch finished.',
        intro="Stage 1, broadcast: every line goes to every node at its next turn boundary. The question is whether Voltaris will meet its 2027 guidance. Orders are up, shipments are down, and a plant fire that only the disclosures branch can find explains the gap. Select n3 at the last steps: n2's result is marked <em>never arrived</em>.",
        names={'n1': 'VLTG guidance?', 'n2': 'own disclosures', 'n3': 'industry stats'},
        code=[('n2', [2]), ('n3', [1])],
        steps=[
            (0.0, "n1 opens n2 on Voltaris's own disclosures and n3 on industry statistics, then waits on both.",
             {'n1': 'Waits in one cell for both results.', 'n2': 'Starts from the run index: n1 and n3 are running.', 'n3': 'Starts from the run index too.'}),
            (9.7, "Each branch runs one search cell. n2's output carries the one start line it had not seen. n3 started last, so its stream is empty: nothing has been published yet.",
             {'n2': 'Searched orders, backlog and guidance.', 'n3': 'Searched shipments and market share.'}),
            (17.6, 'n3 reads the shipments and market-share releases and both series in one parallel cell. Voltaris shipments fell 9% and its share fell from 31% to 27%. Nothing it read says why.',
             {'n3': 'Has its numbers; about to write its answer.', 'n2': 'Read the orders release, which points to a separate restart release.'}),
            (26.2, "n3 finishes: '2027 revenue of about C$3.4–3.7B, well short'. Its result line enters n2's stream.",
             {'n3': 'Done. Its answer has no cause for the drop.', 'n2': "Mid-cell, fetching the restart release; n3's line waits for this cell to end."}),
            (26.3, "The same cell returns n2's read of 'Halbrook plant restarts after fire': the largest plant was offline nine weeks in Q2, which explains n3's shipment drop. n3 finished 0.1 s earlier, and nothing can reach it now.",
             {'n2': "Has the fire and n3's result line in the same cell output."}),
            (34.4, "n2 finishes 'at or just above C$4.2B'. It ties the fire to its own revenue dip, not to n3's shipment drop, and cites nothing.",
             {'n2': 'Done. Never read n3.r1.', 'n1': 'Gets both results and reads them.'}),
            (43.7, "n1 answers 'probably will not reach C$4.2B'. It repeats the fire as a fact, yet still puts the shipment drop down to the industry. The ground truth is likely yes.",
             {'n1': 'Done. Sided with the shipments branch.'}),
        ],
    ),
    dict(
        id='twice', nav='Shared need: fetched twice', run='stage1/shared-broadcast-s102',
        title='The slow series, fetched twice at once',
        summary='Stage 1, broadcast. Both branches need the CMA path and fetch the same slow series, the second 1.9 s after the first, while it is still in flight.',
        intro='Stage 1, broadcast. Both branches need the market-implied CMA policy path, which comes from a slow series (7–11 s). Watch the second fetch start while the first is in flight: no line exists for a call in progress, so broadcast has nothing to deliver.',
        names={'n1': 'add VLTX calls?', 'n2': 'valuation case', 'n3': 'call pricing'},
        code=[('n2', [1]), ('n3', [1])],
        steps=[
            (0.0, 'n1 opens n2 on the valuation case and n3 on Jan-2028 call pricing, then waits. Both tasks name the expected CMA policy path.',
             {'n1': 'Waits for both results.'}),
            (9.4, "Each runs one search cell. n2's output carries n1 opening n3, a line that names the CMA path. A start line says what a node will answer, not what it will fetch.",
             {'n2': 'Found the CMA minutes, the Governor\'s speech and the factsheet.', 'n3': 'Found the same three, plus the options note.'}),
            (16.1, "n2's second cell reads four documents, then starts the slow series cma_futures. n3 is already reading three of the same documents.",
             {'n2': 'Fetching cma_futures.', 'n3': 'Reading the CMA minutes, the speech and the factsheet, all of which n2 is reading too.'}),
            (18.0, "1.9 s later, n3 starts the same fetch while n2's is still in flight. No line exists for a call in flight, and a ref to the finished data would not exist for another 7 s.",
             {'n3': 'Fetching cma_futures, a second time for the run.'}),
            (25.4, 'Both fetches return within 0.1 s of each other. The run made four duplicate fetches, and every pair overlapped.',
             {'n2': 'Derives 4.50% to 4.00% by end-2027.', 'n3': 'Derives the same path on its own.'}),
            (36.0, 'n2 and n3 finish 2.2 s apart. Neither result line reaches the other: both are done by then.',
             {'n1': 'Reads both results.'}),
            (44.2, "n1 integrates: 'a reasonable time to add, but only modestly sized'. Every line in this run that could have saved work arrived after the work was done.",
             {'n1': 'Done.'}),
        ],
    ),
    dict(
        id='stuck', nav='Cross-branch: stays put', run='stage1/cross-broadcast-s101',
        title='The finding stays in the financing branch',
        summary="Stage 1, broadcast. The equity node reads that Pellham is cutting 2027 orders by 40%; the demand branch, which needs it, finishes without it.",
        intro="Stage 1, broadcast. The financing branch's equity node finds a demand fact: Pellham Power, the largest buyer, is cutting 2027 transformer orders by about 40%. Its result line carries its verdict on equity markets, not Pellham, and it goes out after the demand branch's last cell.",
        names={'n1': 'add LEAPS?', 'n2': 'demand', 'n3': 'financing', 'n4': 'LEAPS price', 'n5': 'debt', 'n6': 'equity', 'n7': 'utility demand', 'n8': 'DC demand'},
        code=[('n6', [1]), ('n7', [1])],
        steps=[
            (0.0, 'n1 opens n2 on demand, n3 on financing and n4 on LEAPS pricing, then waits on all three.',
             {'n1': 'Waits for three results.'}),
            (8.0, 'n3 splits into debt (n5) and equity (n6), and n2 into utility demand (n7) and data-centre demand (n8). Both parents then wait on their children.',
             {'n2': 'Waits on n7 and n8.', 'n3': 'Waits on n5 and n6.'}),
            (17.7, "n6 reads 'Pellham Power withdraws equity offering, scales back procurement': Pellham will cut 2027 transformer orders by about 40%. That is a demand fact, found by the financing branch.",
             {'n6': 'Has the cut. Its question is whether equity markets can fund capex.', 'n7': 'Reading the capital plans.'}),
            (22.0, "n7 reads the utilities' 2027 capital plans: Pellham, the largest buyer, plans spending up 18%. The plan n6 learned is being cut is now in n7's output, and no line says so.",
             {'n7': 'Has the +18% plan and about to answer.', 'n5': 'Read the same Pellham release at 21.9 s.'}),
            (26.2, "n7 finishes: 'Yes, on the plans, though the plans depend on financing'. Nothing in its stream ever mentioned Pellham.",
             {'n7': 'Done.', 'n2': 'Its waiting cell ends with n7 and n8.'}),
            (26.8, "n6's result line goes out: 'Short answer: mostly no. Equity markets can't be relied on…'. It carries n6's verdict, not Pellham. n2's last cell ended at 26.2 s, so the line never reaches the demand branch.",
             {'n6': 'Done.', 'n2': 'Writing its final message; no cell left to receive lines.'}),
            (29.0, "n2 finishes 'Yes, demand is still rising through 2027', citing n7.r1 and n8.r1.",
             {'n2': 'Done.'}),
            (42.9, "n1 connects Pellham to demand itself and answers 'don't add this month', which is right. But n2.r1 still says demand is rising, and an identical request later in a standing run would reuse it.",
             {'n1': 'Done.'}),
        ],
    ),
]
