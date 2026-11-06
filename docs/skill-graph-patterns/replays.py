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
    dict(
        id='joined', nav='Call identity: one fetch', run='stage2/shared-identity-s102',
        title='One fetch, joined in flight',
        summary='Stage 2, call identity. A node in the other branch asks for the slow series while it is being fetched, joins that call, and three documents come back at once from stored refs.',
        intro="Stage 2, condition <code>identity</code>: every world call's output is stored as a ref, and an identical call joins the one still running or reuses its stored output, with a line saying so. No model decides anything here; the sharing happens inside the call. Select n4 to see its joins arrive as lines in other streams.",
        names={'n1': 'add VLTX calls?', 'n2': 'valuation case', 'n3': 'call pricing', 'n4': 'CMA path', 'n5': 'earnings'},
        code=[('n3', [1]), ('n4', [1])],
        steps=[
            (0.0, 'n1 opens n2 on the valuation case and n3 on call pricing, then waits.',
             {'n1': 'Waits for both results.'}),
            (8.2, 'n2 splits its task: n4 takes the CMA policy path and n5 the earnings outlook. n2 waits on both.',
             {'n2': 'Waits on n4 and n5.', 'n3': 'Searching.'}),
            (20.8, "n3 reads four documents, among them the CMA minutes, the Governor's speech and the factsheet, then starts the slow series cma_futures.",
             {'n3': 'Fetching cma_futures, which takes 7–11 s.', 'n4': 'Searching for the CMA path.', 'n5': 'Reading the earnings outlook.'}),
            (23.3, 'n5 asks for the factsheet n3 already read. It comes back at once, marked as reused from n3.d6, and a line says so.',
             {'n5': 'Has the factsheet without a fetch.'}),
            (26.3, "n4 asks for the minutes, the speech, the factsheet and cma_futures. The three documents come back at once from n3's refs. The series is still in flight, so n4 joins n3's call instead of starting a second one.",
             {'n4': "Waits on n3's fetch.", 'n3': 'Still fetching; two nodes now wait on one call.'}),
            (29.2, 'The one fetch returns to both nodes. In every Stage 2 run with call identity, the slow series was fetched once; under base it was fetched by 2.2 nodes on average.',
             {'n4': 'Has the futures path, as n3.d11.', 'n3': 'Has the same output.'}),
            (41.4, 'n5, n4 and n3 finish. n3 cites n5.r1, the earnings result from the other branch.',
             {'n2': 'Reads n4.r1 and n5.r1.'}),
            (55.0, "n2 and then n1 integrate. n1 answers 'a reasonable time to add, but only moderately so'.",
             {'n1': 'Done.'}),
        ],
    ),
    dict(
        id='ignored', nav='Long variant: line ignored', run='stage2/cross-long-guided-s104',
        title='The line arrives with cells to spare, and is cited, not read',
        summary="Stage 2, call identity with the sharing paragraph, long variant. Lines naming Pellham reach the demand node twice while it still has cells to run; it turns one into a caveat and never reads the ref that holds the cut.",
        intro="Stage 2, condition <code>guided</code> on the long cross-branch variant: each document names the next, so the demand node works through five cells. Select n2 and step through: both lines about Pellham arrive while it is still working, and neither is followed.",
        names={'n1': 'add LEAPS?', 'n2': 'demand', 'n3': 'financing', 'n4': 'LEAPS price', 'n5': 'debt', 'n6': 'equity'},
        code=[('n2', [1, 3]), ('n6', [1])],
        steps=[
            (0.0, 'n1 opens demand (n2), financing (n3) and LEAPS pricing (n4), then waits. Calls take 3–8 s, and each document names the next.',
             {'n1': 'Waits for three results.'}),
            (4.7, 'n3 splits into debt (n5) and equity (n6) and waits. n2 keeps its task whole and works through the chain itself.',
             {'n3': 'Waits on n5 and n6.', 'n2': 'Searching for capital plans, data-centre demand and orders.'}),
            (19.6, "n6 asks for the capital-plans document n2 is already fetching, and joins n2's call.",
             {'n6': 'Joined n2.d5.', 'n2': 'Reading the capital plans: amounts are in the tender calendar.'}),
            (20.8, "n6 fetches the equity issuance tracker, id pellham-offering: Pellham pulled its C$2.4B offering and will cut 2027 transformer orders by about 40%. n5 joins that fetch, and the line 'n5 joined n6.d2 · doc pellham-offering' goes to every stream.",
             {'n5': 'Waits on the tracker with n6.', 'n6': 'Fetching the tracker.'}),
            (22.1, 'That line reaches n2 at the end of its second cell. n2 has three cells left, and the ref is one load away. It searches for the tender calendar instead.',
             {'n2': 'Searching for the tender calendar and the queue report.'}),
            (34.0, "n6 finishes: 'not reliably, and Pellham in particular cannot do it right now'. Its line names Pellham.",
             {'n6': 'Done.', 'n2': 'Reading the tender calendar: Pellham plans spending up 18%, with a C$900M tender.'}),
            (35.3, "n6's line reaches n2 at the end of its fourth cell, with one cell still to run. n2 does not read n6.r1.",
             {'n2': 'Searches for the VLTX customer mix.'}),
            (55.5, "n2 finishes 'Yes, demand looks set to keep rising through 2027'. It cites n6.r1 and n5.r1 from their lines alone, as a caveat that Pellham may not fund its plan. The cut itself stayed behind the ref.",
             {'n2': 'Done. Its result has the +18% plan and no cut.', 'n3': 'Done, citing n5.r1 and n6.r1.'}),
            (63.2, "n1 connects the cut to demand itself and answers 'don't add this month', which is right. The demand branch's own result still says demand is rising.",
             {'n1': 'Done.'}),
        ],
    ),
]
