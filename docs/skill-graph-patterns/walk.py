"""The XLI walkthrough: one plain question, no skills, every capability."""

from core import Pattern
from patterns import O, C, Rz, I, W, RD, X, M, PAR

ALL = ['readArtifact', 'openNode', 'nextNodeEvent', 'closeNode', 'publishCheckpoint']

w = Pattern('walkthrough', 'walkthrough', 'Should we add to our XLI LEAPS this month?',
            'One plain question, no skills. Every node is a generic node with one task, and every capability shows up '
            'once: decomposition, recursive fan-out, a join seen in the stream, a fork from a trail, a citation across '
            'branches, a settlement, a steer, questions in both directions with you, and, weeks later, a reopen on news.',
            'Should we add to our XLI LEAPS this month?', ALL, user=True, cap=64, wide=True)
w.user_pos = (-0.15 * 104, 0)

w.N('n1', 'add XLI?', 'Should we add to our XLI LEAPS this month?', by='you', pos=(4.1, 0))
w.N('n2', 'demand', "Is the AI-capex demand cycle behind XLI's industrials intact through 2027?", by='n1', pos=(1.4, 1))
w.N('n3', 'rates', 'What do rates and financing conditions imply for capex-heavy industrials through 2027?', by='n1', pos=(4.1, 1))
w.N('n4', 'entry', 'Are XLI LEAPS attractively priced to add to now?', by='n1', pos=(6.6, 1))
w.N('n5', 'capex', "Are hyperscalers' 2027 capex plans credible?", by='n2', pos=(2.1, 2))
w.N('n6', 'grid', "Do grid-equipment lead times support the backlogs of XLI's holdings?", by='n2', pos=(0.7, 2))
w.N('n7', 'Fed path', 'What is the base-case 2027 Fed path?', by='n3', pos=(4.9, 2))
w.N('n8', 'credit', 'Is AI-infrastructure credit open for 2027 issuance?', by='n3', pos=(3.5, 2))
w.N('n9', 'two hikes', 'Under two 2027 hikes, what are the path and the 10Y?', by='n4', frm='n7', pos=(6.6, 2))
w.N('n10', 'URA hedge', 'Would URA LEAPS hedge this position, or add the same risk?', by='n1', frm='n4', pos=(8.2, 1))

w.step('You open the run with one question. n1 starts from the index, which is empty apart from itself.',
       [O('you', 'n1')],
       {'you': 'Asks: "Should we add to our XLI LEAPS this month?"',
        'n1': 'Decides the answer rests on three orthogonal judgments: is demand intact, what do rates imply, and is the price right.'})
w.step('n1 opens three nodes, one task each, and goes idle. Their start lines reach every stream.',
       [PAR(O('n1', 'n2'), O('n1', 'n3'), O('n1', 'n4')), I('n1')],
       {'n1': 'Idle in nextNodeEvent. That costs nothing until a line arrives.',
        'n2': 'Starts from the index: n1, n3 and n4 are running. Splits its own task in two.',
        'n3': 'Splits its task too: the Fed path and credit conditions are separate judgments.',
        'n4': 'Starts pricing: IV rank, term structure and skew are tool calls inside its own node, not nodes.'})
w.step("Recursive fan-out: each child splits its own what. Four start lines reach every stream, including n4's.",
       [PAR(O('n2', 'n5'), O('n2', 'n6'), O('n3', 'n7'), O('n3', 'n8')), PAR(I('n2'), I('n3'))],
       {'n2': 'Opens capex credibility (n5) and grid lead times (n6), then idles.',
        'n3': 'Opens the base-case Fed path (n7) and credit conditions (n8), then idles.',
        'n4': 'At its next turn boundary it sees "n3 opened n7 · What is the base-case 2027 Fed path?", the exact input its pricing needs.'})
w.step("n4 reads n7's record and sends its exact request. n7 is running, so n4 joins it. For a stress case it needs a different aspect, so it forks n9 from n7's trail instead of bending n7's task.",
       [RD('n4', 'n7'), O('n4', 'n7', 'joined'), O('n4', 'n9')],
       {'n4': 'Joins n7 (one Fed path, two holders) and opens n9 with from: n7. It keeps pricing meanwhile.',
        'n7': 'Unchanged: same task, now held by n3 and n4.',
        'n9': "Starts from n7.trail as it stands, plus its own task, so it reuses n7's prompt cache."})
w.step("Checkpoints flow. n6 sees n8.c1 on utility equity issuance; it matters for who pays for grid build-outs, so n6 reads it and will cite it. That's a reference, not a join: the task stays n8's.",
       [PAR(C('n5', 'Hyperscaler 2027 capex looks credible: covered by operating cash flow.'),
            C('n8', 'Utility equity issuance hit a record in Q3, and more is guided for 2027.')),
        RD('n6', 'n8.c1')],
       {'n5': 'Publishes its first read.', 'n8': 'Publishes a finding outside its own question, for whoever needs it.',
        'n6': 'Reads n8.c1 by ref and keeps its own task.'})
w.step("n8.c2 contradicts n5.c1. n5 reads n8's trail to see how it got there, then asks n8 one precise question.",
       [C('n8', 'AI-infra credit tightening: hyperscaler spreads up 35bp since August; part of 2027 capex is debt-funded.'),
        RD('n5', 'n8.trail'),
        C('n5', 'We conflict on funding: I see 2027 capex covered by cash flow; you say debt-funded. My basis is FY26 cash-flow guidance. What is yours?', 'n8'),
        I('n5')],
       {'n5': 'Sees the contradiction in its stream, reads the turns where n8 pulled bond data, and addresses n8.',
        'n8': 'Gets n5.c2 at its next turn boundary, marked as addressed to it.'})
w.step("n8 reads n5's trail and replies. Each stream marks the other's message as addressed to it; every other node sees one line each.",
       [RD('n8', 'n5.trail'),
        C('n8', 'Both hold: cash flow covers about 80%; the other 20% is bonds, and above 200bp spreads that slice gets repriced.', 'n5')],
       {'n8': 'Reconciles the two bases instead of defending its own.', 'n5': 'Wakes on the reply.'})
w.step("n5 publishes the settled view citing both sides, and both results cite it. That's the second diamond: two trails, one shared result, no judge.",
       [C('n5', 'Settled: 2027 capex is credible. About 80% is cash-funded and 20% debt-funded, sensitive above 200bp spreads.',
          None, ['n5.c2', 'n8.c3']),
        PAR(Rz('n5', 'Hyperscaler 2027 capex is credible; the debt-funded 20% is the risk (n5.c3).', ['n5.c3']),
            Rz('n8', 'Credit is open for 2027 issuance below 200bp spreads; today 165bp (n5.c3).', ['n5.c3']))],
       {'n5': 'Writes the view both rest on, n5.c3, then finishes.',
        'n8': 'Finishes on the same view instead of its own first draft.',
        'n2': 'Sees n5.r1 arrive; still waiting on n6.', 'n3': 'Sees n8.r1 arrive; still waiting on n7.'})
w.step("n4.c1 drifts into single names. n1, idle, wakes on the line and steers n4 within its task. The note lands at n4's next turn boundary.",
       [C('n4', 'Comparing XLI LEAPS with GE Vernova and Eaton single-name calls.'), W('n1'),
        C('n1', 'ETF only: XLI LEAPS. Single names are out of scope for this run.', 'n4'), I('n1')],
       {'n1': 'Steers only: same task, a narrower path.', 'n4': 'Drops the single names at its next turn.'})
w.step('n4 needs a number only you have, so it asks you. It keeps pricing while it waits, and your reply arrives as a line addressed to it.',
       [C('n4', 'What premium budget should adding stay within?', 'you'), M('n4', '$250k of premium at most.')],
       {'n4': 'Asks you directly, not through n1.', 'you': 'Answer n4 directly.'})
w.step("You ask n1 a new question mid-run. n1 answers from the lines it already holds, and forks n10 from n4's trail, which already has the options context.",
       [M('n1', 'Would URA LEAPS hedge this better than adding XLI?'), O('n1', 'n10'),
        C('n1', "Checking in n10, forked from n4's options work. The answer will be in the final.", 'you'), I('n1')],
       {'n1': "Knows every node's state from its stream, so it replies at once without waiting on anyone.",
        'n10': 'Starts from n4.trail: surfaces, IV ranks and your budget are already in context.'})
w.step('Results arrive as lines. n2 and n3 wake: everything they hold is done.',
       [PAR(Rz('n7', 'Base case: one cut by mid-2027; 10Y 4.4 to 4.9%.'),
            Rz('n9', 'Two 2027 hikes: 10Y near 5.5%; XLI LEAPS lose about 8% to rho and vega (n7.trail).', ['n7.trail']),
            Rz('n6', 'Lead times of 2 to 4 years support backlogs through 2028; utility equity issuance is a drag on buyers (n8.c1).', ['n8.c1'])),
        PAR(W('n2'), W('n3'))],
       {'n7': 'Publishes once for both holders, n3 and n4.', 'n9': 'Cites the trail it forked from.',
        'n6': 'Cites the checkpoint it borrowed from another branch.'})
w.step('The second level publishes, each result citing what it rests on.',
       [PAR(Rz('n2', 'Demand intact through 2027: capex credible (n5.r1), backlogs supported (n6.r1).', ['n5.r1', 'n6.r1']),
            Rz('n3', 'Financing open: one cut by mid-2027 (n7.r1); credit open below 200bp (n8.r1).', ['n7.r1', 'n8.r1']),
            Rz('n4', 'XLI LEAPS fairly priced at IV rank 28; a two-hike path costs about 8% (n7.r1, n9.r1); stay within $250k (you.m1).',
               ['n7.r1', 'n9.r1', 'you.m1']),
            Rz('n10', 'URA adds correlated risk, not a hedge: 0.71 correlation to XLI LEAPS (n4.trail).', ['n4.trail']))],
       {'n4': 'Cites your budget like any other ref.', 'n10': 'Cites the trail it forked from.'})
w.step('n1 writes its final message: the answer, with every claim citing the result it rests on. The run stays open.',
       [W('n1'), Rz('n1', 'Add, staged: half now, half after the December FOMC, within $250k; skip URA (n2.r1, n3.r1, n4.r1, n10.r1).',
                     ['n2.r1', 'n3.r1', 'n4.r1', 'n10.r1'])],
       {'n1': 'Four citations; behind them, ten nodes and two diamonds.', 'you': 'Get the answer as n1.r1.'})
w.step("Weeks later you send n1 the CPI print, which reopens it. The result lines show that n3.r1 and n4.r1 cite n7.r1, and n2.r1 cites nothing rates-related, so n1 reopens n7 first.",
       [M('n1', 'Core CPI 3.6% against 3.1% expected; the 10Y is up 40bp today.'),
        C('n1', 'Re-derive the base case after a hot CPI (you.m3).', 'n7', ['you.m3']), I('n1')],
       {'n1': 'Traces the delta through cites it already has; reads nothing new.',
        'n7': 'Reopened in its own session, with its whole trail in context.'})
w.step('n7 publishes r2, and n1 reopens the two results that cite n7.r1.',
       [Rz('n7', 'Base case r2: one hike in 2027; 10Y 4.9 to 5.3% (you.m3).', ['you.m3']), W('n1'),
        PAR(C('n1', 'n7.r2 replaces n7.r1: one hike, not one cut. Does your result change?', 'n3', ['n7.r2']),
            C('n1', 'n7.r2 replaces n7.r1: one hike, not one cut. Does your result change?', 'n4', ['n7.r2'])),
        I('n1')],
       {'n7': 'n7.r1 stays in the record; n7.r2 is the latest.',
        'n2': 'Untouched: nothing it rests on moved.',
        'n9': 'Not reopened: it already assumed hikes.'})
w.step('n3 holds, so nothing under it moves: n8 is never reopened. n4 changes.',
       [PAR(Rz('n3', 'Holds: financing still open at these levels (n7.r2, n8.r1).', ['n7.r2', 'n8.r1']),
            Rz('n4', 'Changed: wait for the December FOMC; rho cost is now about 6% (n7.r2, n9.r1).', ['n7.r2', 'n9.r1']))],
       {'n3': 'Re-decides in its own session. Its r2 records the re-check.',
        'n4': 'Re-decides and changes its conclusion.'})
w.step('n1 publishes r2. Of ten nodes, four moved, each along a cite the news actually touched.',
       [W('n1'), Rz('n1', 'Hold the add until after the December FOMC (n4.r2); demand and financing unchanged (n2.r1, n3.r2).',
                     ['n4.r2', 'n2.r1', 'n3.r2'])],
       {'n1': 'Cites the new versions and the untouched n2.r1.', 'you': 'Get n1.r2.'})

w.tab('n1 add XLI?', [
    """// The task holds three separate judgments. Open one node per judgment.
const [demand, rates, entry] = await Promise.all([
  nodes.open({task: "Is the AI-capex demand cycle behind XLI's industrials intact through 2027?"}),
  nodes.open({task: 'What do rates and financing conditions imply for capex-heavy industrials through 2027?'}),
  nodes.open({task: 'Are XLI LEAPS attractively priced to add to now?'}),
]);
return await nodes.next();       // idle until lines arrive""",
    """// n4.c1 drifted into single names. Steer it, within its task.
await tools.publishCheckpoint({to: entry.node, content:
  'ETF only: XLI LEAPS. Single names are out of scope for this run.'});
return await nodes.next();""",
    """// you.m2 asks about URA. n4's trail already holds the options context: fork it.
const ura = await nodes.open({from: entry.node,
  task: 'Would URA LEAPS hedge this position, or add the same risk?'});
await tools.publishCheckpoint({to: 'you', content:
  "Checking in n10, forked from n4's options work. The answer will be in the final."});
return await nodes.next();"""],
      final='Add, staged: half now, half after the December FOMC, within $250k; skip URA (n2.r1, n3.r1, n4.r1, n10.r1).')
w.tab('n4 entry', [
    """// Our stream showed: n3 opened n7 · What is the base-case 2027 Fed path?
const fed = await nodes.open((await inspect('n7')).request);    // joins n7
const stress = await nodes.open({from: 'n7',
  task: 'Under two 2027 hikes, what are the path and the 10Y?'});
const surface = await ivRank('XLI', {tenors: ['2027-12', '2028-01']});   // the how
return surface;""",
    """await tools.publishCheckpoint({to: 'you', content:
  'What premium budget should adding stay within?'});
return await nodes.next();       // keeps pricing; your reply arrives as a line"""],
      final='XLI LEAPS fairly priced at IV rank 28; a two-hike path costs about 8% (n7.r1, n9.r1); stay within $250k (you.m1).')
w.tab('n5 capex', [
    """// n8.c2 contradicts our n5.c1. See how n8 got there, then ask.
const theirs = await read('n8.trail');
await tools.publishCheckpoint({to: 'n8', content:
  'We conflict on funding: I see 2027 capex covered by cash flow; you say debt-funded. ' +
  'My basis is FY26 cash-flow guidance. What is yours?'});
return await nodes.next();""",
    """// n8.c3: cash flow covers about 80%, bonds the rest. Publish the view both rest on.
await tools.publishCheckpoint({content:
  'Settled: 2027 capex is credible. About 80% is cash-funded and 20% debt-funded, ' +
  'sensitive above 200bp spreads. (n5.c2, n8.c3)'});"""],
      final='Hyperscaler 2027 capex is credible; the debt-funded 20% is the risk (n5.c3).')
w.tab('n1 after CPI', [
    """// Reopened by you.m3. The result lines say who rests on n7.r1:
//   n3.r1 · … · cites n7.r1, n8.r1     n4.r1 · … · cites n7.r1, n9.r1, you.m1
await tools.publishCheckpoint({to: 'n7', content: 'Re-derive the base case after a hot CPI (you.m3).'});
return await nodes.next();       // n7.r2""",
    """for (const to of ['n3', 'n4'])
  await tools.publishCheckpoint({to, content:
    'n7.r2 replaces n7.r1: one hike, not one cut. Does your result change?'});
return await nodes.next();       // n3.r2 holds, n4.r2 changes"""],
      final='Hold the add until after the December FOMC (n4.r2); demand and financing unchanged (n2.r1, n3.r2).')

WALK = w
