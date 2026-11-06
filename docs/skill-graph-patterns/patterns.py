"""The v3 pattern set, authored on the existing skill graph."""

from core import Pattern


def O(by, n, disp='started'): return ('open', by, n, disp)
def C(n, text, to=None, cites=()): return ('cp', n, text, to, tuple(cites))
def Rz(n, text, cites=()): return ('result', n, text, tuple(cites))
def I(n): return ('idle', n)
def W(n): return ('wake', n)
def RD(n, ref): return ('read', n, ref)
def X(by, n): return ('close', by, n)
def F(n, text): return ('fail', n, text)
def M(to, text, cites=()): return ('msg', 'you', to, text, tuple(cites))
def G(src, skill, kind='read'): return ('ghost', src, skill, kind)
def PAR(*evs): return ('par', list(evs))


PATTERNS = []


def pattern(*a, **k):
    p = Pattern(*a, **k)
    PATTERNS.append(p)
    return p


# ---------------------------------------------------------------- traversal

p = pattern('consult', 'traversal', 'Route and consult',
            'A simple question costs one node. The root reads its linked procedures, picks the one that fits by its '
            'description, and follows it inline. Reading a skill runs nothing.',
            'What is the current rates regime?', ['readNode'])
p.N('n1', 'root', 'What is the current rates regime?', skill='root')
p.step('The run opens n1 on the root skill. Its first batch is the index, which holds only n1 itself.',
       [O(None, 'n1')], {'n1': 'Starts from the root procedure, which links to three skills.'})
p.step('n1 reads the three linked procedures with readNode. Nothing runs; each read is recorded as consulted.',
       [PAR(G('n1', 'rates-regime'), G('n1', 'credit-spreads'), G('n1', 'fx-carry'))],
       {'n1': 'Reads rates-regime, credit-spreads and fx-carry, and judges from the descriptions that rates-regime fits.'})
p.step('n1 follows rates-regime inline. Its final message is the answer, stored as n1.r1.',
       [Rz('n1', 'Rates regime: restrictive, with hike risk elevated into 2027.')],
       {'n1': 'Works through the rates-regime steps in its own context. No child, no handoff.'})
p.tab('n1 root', [
    """// The root's packet links to three skills. Read them: nothing runs.
const options = await Promise.all(
  context.entry.links.map(node => tools.readNode({node})));
return options.map(o => `${o.node}: ${o.description}`);""",
    """// The model picked rates-regime from the descriptions it just read.
return options.find(o => o.node === 'rates-regime').text;   // follow it inline"""],
      final='Rates regime: restrictive, with hike risk elevated into 2027. Followed rates-regime inline.')

p = pattern('delegate', 'traversal', 'Route and delegate',
            "When the chosen skill deserves its own context, open it as a child and answer from its result. The answer "
            "cites the child's result inline, and that citation is the link the trail keeps.",
            'How wide are AI-infrastructure credit spreads?', ['readNode', 'openNode', 'nextNodeEvent'])
p.N('n1', 'root', 'How wide are AI-infrastructure credit spreads?', skill='root')
p.N('n2', 'credit-spreads', 'How wide are AI-infrastructure credit spreads?', skill='credit-spreads', by='n1')
p.step('n1 opens and reads its linked procedures.',
       [O(None, 'n1'), PAR(G('n1', 'rates-regime'), G('n1', 'fx-carry'))],
       {'n1': 'Reads the links. credit-spreads needs its own context and data access, so n1 will delegate rather than follow it inline.'})
p.step('n1 opens n2 on credit-spreads and goes idle. Every stream gets the line "n1 opened n2".',
       [O('n1', 'n2'), I('n1')],
       {'n1': 'Waits in nextNodeEvent. Idle costs nothing until a line arrives.',
        'n2': 'Starts from the credit-spreads procedure and its task.'})
p.step('n2 does the how inside its own node, publishes a checkpoint, then its result.',
       [C('n2', 'Pulled IG index and AI-infra issuer curves; computing the gap.'),
        Rz('n2', 'AI-infra IG spreads are 145bp, 30bp wider than IG overall.'), W('n1')],
       {'n2': 'Data pulls and arithmetic run as parallel tool calls inside n2. None of it is a node.',
        'n1': 'Sees n2.c1 as a line and keeps waiting. Wakes on n2.r1.'})
p.step('n1 writes its final message, citing n2.r1 instead of copying it.',
       [Rz('n1', 'AI-infrastructure IG spreads are 145bp, 30bp wider than IG overall (n2.r1).', ['n2.r1'])],
       {'n1': 'Answers from the line it already has. The inline ref is the link.'})
p.tab('n1 root', [
    """const options = await Promise.all(
  context.entry.links.map(node => tools.readNode({node})));
// credit-spreads needs its own context and data access: delegate it.
const spreads = await nodes.run({node: 'credit-spreads',
  task: 'How wide are AI-infrastructure credit spreads?'});
return spreads;   // {node: 'n2', ref: 'n2.r1', line: 'AI-infra IG spreads are 145bp, …'}"""],
      final='AI-infrastructure IG spreads are 145bp, 30bp wider than IG overall (n2.r1).')

p = pattern('descent', 'traversal', 'Descent through links',
            'Depth comes from the skill graph. Each node opens the skills its own prose links to, and each child does the '
            'same. Every node sees every line in the run, but it waits only on the children it opened.',
            'Assess the capacity outlook', ['openNode', 'nextNodeEvent'])
p.N('n1', 'root', 'Assess the capacity outlook', skill='root')
p.N('n2', 'capacity', 'Interpret capacity', skill='capacity', by='n1')
p.N('n3', 'snapshot', 'Produce snapshot evidence', skill='snapshot', by='n2')
p.N('n4', 'policy', 'Outline policy timing', skill='policy', by='n2')
p.N('n5', 'delta', 'Compute snapshot difference', skill='delta', by='n3')
p.N('n6', 'volume', 'Report volume evidence', skill='volume', by='n4')
p.step('n1 opens n2 on capacity and goes idle.',
       [O(None, 'n1'), O('n1', 'n2'), I('n1')],
       {'n1': 'Delegates the whole question: capacity is one judgment with its own procedure.'})
p.step("n2's procedure links to snapshot and policy. It opens both in parallel and goes idle.",
       [PAR(O('n2', 'n3'), O('n2', 'n4')), I('n2')],
       {'n2': 'Opens what its own prose links to: two orthogonal sub-tasks.',
        'n3': 'Starts on snapshot evidence.', 'n4': 'Starts on policy timing.'})
p.step('Each child does the same: snapshot opens delta, policy opens volume. Four levels, and nobody set a depth.',
       [PAR(O('n3', 'n5'), O('n4', 'n6')), PAR(I('n3'), I('n4'))],
       {'n3': 'Needs the change between snapshots; its prose links delta.',
        'n4': 'Needs volume evidence; its prose links volume.'})
p.step('The leaves publish. Their lines reach every stream, including n1, which reads none of them: it waits on n2 alone.',
       [PAR(Rz('n5', 'Utilization up 3pp against the prior snapshot, 88% to 91%.'),
            Rz('n6', 'Grid equipment volumes up 6% q/q.'))],
       {'n1': 'Sees n5.r1 and n6.r1 as lines. Nothing to do: they belong to n2\'s subtree.',
        'n5': 'Publishes and finishes.', 'n6': 'Publishes and finishes.'})
p.step('Results climb one level, each citing what it rests on.',
       [PAR(Rz('n3', 'Capacity tight: utilization 91%, up 3pp (n5.r1).', ['n5.r1']),
            Rz('n4', 'No policy relief before 2027; volumes still rising (n6.r1).', ['n6.r1']))],
       {'n3': 'Wakes on n5.r1 and cites it.', 'n4': 'Wakes on n6.r1 and cites it.'})
p.step('n2 publishes from its two children.',
       [Rz('n2', 'Capacity outlook: binding through Q3 2027 (n3.r1, n4.r1).', ['n3.r1', 'n4.r1'])],
       {'n2': 'Integrates its own subtree. Its result compresses four nodes into one line.'})
p.step('n1 answers from n2.r1.',
       [Rz('n1', 'Capacity is binding through Q3 2027 (n2.r1).', ['n2.r1'])],
       {'n1': 'One citation, and the trail behind it is four levels deep.'})
p.tab('n2 capacity', [
    """// capacity's prose links to snapshot and policy: open both.
const [snap, pol] = await Promise.all([
  nodes.run({node: 'snapshot', task: 'Produce snapshot evidence', inputs}),
  nodes.run({node: 'policy', task: 'Outline policy timing', inputs}),
]);
return [snap.line, pol.line];"""], final='Capacity outlook: binding through Q3 2027 (n3.r1, n4.r1).')
p.tab('n3 snapshot', [
    """const change = await nodes.run({node: 'delta', task: 'Compute snapshot difference', inputs});
return change.line;"""], final='Capacity tight: utilization 91%, up 3pp (n5.r1).')

p = pattern('pipeline', 'traversal', 'Pipeline',
            "Each step's task cites the previous result inline. The ref in the text is the whole handoff: every node in "
            'the run can read any ref, so there is no grant to pass.',
            'Turn a trade request into a ticket', ['openNode', 'nextNodeEvent', 'readArtifact'])
p.N('n1', 'root', 'Turn a trade request into a ticket', skill='root')
p.N('n2', 'parse-intent', 'Parse this trade request: buy 40 of the XLI Jan-28 150s, limit 21.40', skill='parse-intent', by='n1')
p.N('n3', 'size-position', 'Size the position in n2.r1', skill='size-position', by='n1')
p.N('n4', 'format-ticket', 'Format n3.r1 as an order ticket', skill='format-ticket', by='n1')
p.step('n1 opens n2 to parse the request, and waits.',
       [O(None, 'n1'), O('n1', 'n2'), I('n1')],
       {'n1': 'Opens one step at a time: each step needs the previous result.'})
p.step("n2 publishes. n1 opens n3 with a task that cites n2.r1.",
       [Rz('n2', 'Intent: buy 40 XLI Jan-2028 150 calls, limit 21.40.'), W('n1'), O('n1', 'n3'), I('n1')],
       {'n1': "Writes n2.r1 into n3's task. Nothing else is passed.",
        'n3': 'Starts with a task that names its input by ref.'})
p.step('n3 reads n2.r1, sizes, and publishes. n1 opens the last step the same way.',
       [RD('n3', 'n2.r1'), Rz('n3', '40 contracts is 0.8% of NAV, within the 1% limit (n2.r1).', ['n2.r1']),
        W('n1'), O('n1', 'n4'), I('n1')],
       {'n3': 'Reads n2.r1 by ref. With run-wide visibility, reading needs no grant.',
        'n4': 'Starts with n3.r1 in its task.'})
p.step('n4 reads n3.r1 and formats the ticket.',
       [RD('n4', 'n3.r1'), Rz('n4', 'Ticket: BUY 40 XLI 2028-01 150C @ 21.40 LMT, DAY (n3.r1).', ['n3.r1'])],
       {'n4': 'Its result cites the size it formatted, so the chain is traceable link by link.'})
p.step('n1 answers with the ticket.',
       [Rz('n1', 'Ticket ready (n4.r1).', ['n4.r1'])],
       {'n1': 'n4.r1 cites n3.r1, which cites n2.r1: the whole chain from one ref.'})
p.tab('n1 root', [
    """const intent = await nodes.run({node: 'parse-intent',
  task: `Parse this trade request: ${request}`});
const size = await nodes.run({node: 'size-position',
  task: `Size the position in ${intent.ref}`});
const ticket = await nodes.run({node: 'format-ticket',
  task: `Format ${size.ref} as an order ticket`});
return ticket.line;"""], final='Ticket ready (n4.r1): BUY 40 XLI 2028-01 150C @ 21.40 LMT.')

p = pattern('fanout', 'traversal', 'Fan out and fan in',
            'Split the what, not the how. Each child is one judgment about one name, independent of its siblings, and '
            'its data pulls stay inside it. allSettled keeps one failure from blocking the rest, and the reducer cites '
            'every result it used.',
            'Which of five ETFs has the richest long-dated premium?', ['openNode', 'nextNodeEvent'])
p.N('n1', 'root', 'Which of five ETFs has the richest long-dated premium?', skill='root')
for i, t in enumerate(['SPY', 'QQQ', 'IWM', 'TLT', 'GLD']):
    p.N(f'n{i + 2}', f'screen {t}', f"Is {t}'s long-dated premium rich or cheap against its own history, and why?",
        skill='screen', by='n1')
p.N('n7', 'rank', 'Rank by premium richness: n2.r1, n3.r1, n4.r1, n6.r1 (TLT failed)', skill='rank', by='n1')
p.step('n1 opens five screens at once, one per ETF, and goes idle. Each is its own judgment, so each gets its own context.',
       [O(None, 'n1'), PAR(*[O('n1', f'n{i}') for i in range(2, 7)]), I('n1')],
       {'n1': 'Splits by name: five orthogonal tasks. None needs another.',
        'n2': "Pulls SPY's surface history with tool calls inside its own node."})
p.step('Checkpoints arrive as lines. n1 sees them, but has nothing to act on yet.',
       [PAR(C('n2', 'SPY: 2-year IV at the 31st percentile of 5 years.'),
            C('n5', 'TLT: the vendor surface request timed out once; retrying.'))],
       {'n1': 'Reads the lines, keeps waiting.', 'n5': 'Retries a tool call inside the node: still the how.'})
p.step('Four screens publish. TLT fails; the failure belongs to n5 alone, and nobody waits on it.',
       [PAR(Rz('n2', 'SPY premium cheap: IV 31st percentile, flat skew.'),
            Rz('n3', 'QQQ premium rich: IV 78th percentile after the AI rally.'),
            Rz('n4', 'IWM premium fair: IV 52nd percentile.'),
            F('n5', 'vendor timeout')),
        Rz('n6', 'GLD premium rich: IV 81st percentile, event-driven.')],
       {'n5': 'Fails. Its holder, n1, gets the failure line; the siblings are untouched.'})
p.step('n1 wakes and opens n7 to rank. The task cites the four results and names TLT as missing.',
       [W('n1'), O('n1', 'n7'), I('n1')],
       {'n1': 'Proceeds on four of five, and says so in the task rather than hiding the gap.'})
p.step('n7 ranks, citing every result it used.',
       [Rz('n7', 'Richest: GLD, then QQQ; IWM fair; SPY cheap. TLT missing.', ['n2.r1', 'n3.r1', 'n4.r1', 'n6.r1'])],
       {'n7': 'One reducer over four refs.'})
p.step('n1 answers.',
       [Rz('n1', 'GLD and QQQ have the richest long-dated premium (n7.r1). TLT failed and is not ranked (n5).', ['n7.r1'])],
       {'n1': 'Cites the ranking and names the failed node.'})
p.tab('n1 root', [
    """const names = ['SPY', 'QQQ', 'IWM', 'TLT', 'GLD'];
const screens = await Promise.allSettled(names.map(t => nodes.run({node: 'screen',
  task: `Is ${t}'s long-dated premium rich or cheap against its own history, and why?`})));
const ok = screens.filter(s => s.status === 'fulfilled').map(s => s.value.ref);
const rank = await nodes.run({node: 'rank',
  task: `Rank by premium richness: ${ok.join(', ')} (TLT failed)`});
return rank.line;"""],
      final='GLD and QQQ have the richest long-dated premium (n7.r1). TLT failed and is not ranked (n5).')

p = pattern('conditional', 'traversal', 'Conditional links',
            "Prose offers links; a result's content decides which to follow. The model reads the result between cells "
            'and opens only what it needs. A link not taken stays in the skill graph and never becomes a node.',
            'Explain what changed in the latest snapshot', ['openNode', 'readArtifact', 'nextNodeEvent'])
p.N('n1', 'root', 'Explain what changed in the latest snapshot', skill='root')
p.N('n2', 'snapshot', 'Produce snapshot evidence', skill='snapshot', by='n1')
p.N('n3', 'volume', 'Report volume evidence for n2.r1', skill='volume', by='n1')
p.N('n4', 'mix', 'Report mix evidence for n2.r1', skill='mix', by='n1')
p.step('n1 opens n2 on snapshot.', [O(None, 'n1'), O('n1', 'n2'), I('n1')],
       {'n1': 'Needs the evidence before it can choose what else to open.'})
p.step('n2 publishes. n1 reads n2.r1 in full, because its next move depends on what it says.',
       [Rz('n2', 'Demand up 6% q/q; the mix shifted to large transformers; no regulatory change.'), W('n1'), RD('n1', 'n2.r1')],
       {'n1': 'Reads the artifact itself, not just its line.'})
p.step("n1 opens volume and mix. snapshot's prose also links to policy, but n2.r1 says regulation didn't change, so policy is never opened.",
       [PAR(O('n1', 'n3'), O('n1', 'n4')), G('n1', 'policy', 'link'), I('n1')],
       {'n1': 'Judges relevance from content. The skipped link costs nothing.',
        'n3': 'Starts with n2.r1 in its task.', 'n4': 'Starts with n2.r1 in its task.'})
p.step('Both publish, citing the snapshot.',
       [PAR(Rz('n3', 'Volumes up 6% q/q, led by hyperscaler orders (n2.r1).', ['n2.r1']),
            Rz('n4', 'Large power transformers are 41% of orders, up from 33% (n2.r1).', ['n2.r1']))],
       {'n3': 'Publishes.', 'n4': 'Publishes.'})
p.step('n1 explains the change.',
       [Rz('n1', 'Volume rose 6% (n3.r1) and the mix shifted to large transformers (n4.r1); regulation unchanged (n2.r1).',
           ['n3.r1', 'n4.r1', 'n2.r1'])],
       {'n1': 'Three citations, one per claim.'})
p.tab('n1 root', [
    """const snap = await nodes.run({node: 'snapshot', task: 'Produce snapshot evidence', inputs});
return await read(snap.ref);        // the model reads it before choosing""",
    """// n2.r1: demand up, mix shifted, no regulatory change.
// The model follows volume and mix; policy's link is not taken.
const [vol, mix] = await Promise.all([
  nodes.run({node: 'volume', task: `Report volume evidence for ${snap.ref}`}),
  nodes.run({node: 'mix', task: `Report mix evidence for ${snap.ref}`}),
]);
return [vol.line, mix.line];"""],
      final='Volume rose 6% (n3.r1) and the mix shifted to large transformers (n4.r1); regulation unchanged (n2.r1).')

p = pattern('stream', 'traversal', 'Act on progress',
            "A child's checkpoint is a line in its parent's stream as soon as it is published. The idle parent acts on it "
            'while the child keeps working, then takes the result.',
            'Use the snapshot as early as possible', ['openNode', 'nextNodeEvent'])
p.N('n1', 'root', 'Use the snapshot as early as possible', skill='root')
p.N('n2', 'snapshot', 'Produce snapshot evidence', skill='snapshot', by='n1')
p.N('n3', 'capacity', 'Assess capacity from n2.c1', skill='capacity', by='n1')
p.step('n1 opens n2 with nodes.open, which returns at once, and goes idle in nextNodeEvent.',
       [O(None, 'n1'), O('n1', 'n2'), I('n1')], {'n1': 'Holds n2 and waits for any line about it.'})
p.step("n2.c1 lands in n1's stream at the next turn boundary. n1 wakes on it.",
       [C('n2', 'Utilization measured: 91%. Demand split still running.'), W('n1')],
       {'n2': 'Publishes what it has and keeps working.', 'n1': 'Wakes: utilization is all capacity needs.'})
p.step("n1 opens n3 with a task that cites n2.c1, then waits on both. n2 keeps working, unaware anything happened.",
       [O('n1', 'n3'), I('n1'), C('n2', 'Demand split: hyperscalers 58%, utilities 31%.')],
       {'n3': 'Starts from n2.c1, before n2 has finished.', 'n2': 'Unchanged by the early use of its checkpoint.'})
p.step('n3 and n2 both publish.',
       [Rz('n3', 'Capacity binds before 2027 at 91% utilization (n2.c1).', ['n2.c1']),
        Rz('n2', 'Snapshot: utilization 91%; demand split 58/31/11.')],
       {'n3': 'Cites the checkpoint it used, not the later result.'})
p.step('n1 answers from both.',
       [Rz('n1', 'Capacity binds before 2027 (n3.r1), on the snapshot as published (n2.r1).', ['n3.r1', 'n2.r1'])],
       {'n1': 'Got the capacity answer a full step earlier than waiting for n2.r1 would have.'})
p.tab('n1 root', [
    """const snap = await nodes.open({node: 'snapshot', task: 'Produce snapshot evidence', inputs});
const first = await snap.next();       // n2.c1, while n2 keeps working
const early = await nodes.run({node: 'capacity', task: `Assess capacity from ${first.ref}`});
const final = await snap.result();     // n2.r1
return [early.line, final.line];"""],
      final='Capacity binds before 2027 (n3.r1), on the snapshot as published (n2.r1).')

p = pattern('race', 'traversal', 'Race',
            'Open two vendors, take the first result, close the other. The loser is cancelled because nobody else holds '
            'it; had another node joined it, it would keep running for that node.',
            'Get the XLI vol surface quickly', ['openNode', 'nextNodeEvent', 'closeNode'])
p.N('n1', 'root', 'Get the XLI vol surface quickly', skill='root')
p.N('n2', 'vol-surface A', 'Fetch the XLI vol surface', skill='vol-surface', by='n1', inputs={'vendor': 'A'})
p.N('n3', 'vol-surface B', 'Fetch the XLI vol surface', skill='vol-surface', by='n1', inputs={'vendor': 'B'})
p.step('n1 opens the same task twice with different vendors. Inputs are part of identity, so these are two nodes, not a join.',
       [O(None, 'n1'), PAR(O('n1', 'n2'), O('n1', 'n3')), I('n1')],
       {'n1': 'Holds both and waits for whichever result comes first.'})
p.step('Vendor B finishes first.',
       [C('n2', 'Vendor A: 40% of strikes loaded.'), Rz('n3', 'XLI surface from vendor B: 1,240 quotes as of 15:59.')],
       {'n2': 'Still loading.', 'n3': 'Publishes.'})
p.step('n1 takes n3.r1 and closes n2. Nobody else holds n2, so it is cancelled.',
       [W('n1'), X('n1', 'n2')], {'n1': 'Releases its hold on the loser.', 'n2': 'Cancelled: its last holder left.'})
p.step('n1 answers with the winner.', [Rz('n1', 'XLI vol surface ready (n3.r1).', ['n3.r1'])], {'n1': 'Cites the winner.'})
p.tab('n1 root', [
    """const ops = await Promise.all(['A', 'B'].map(vendor => nodes.open({
  node: 'vol-surface', task: 'Fetch the XLI vol surface', inputs: {vendor}})));
const first = await Promise.race(ops.map(op => op.result()));
await Promise.all(ops.map(op => op.close()));   // the winner is already done
return first.line;"""], final='XLI vol surface ready (n3.r1).')

# ------------------------------------------------------------- coordination

p = pattern('join', 'coordination', 'Join what you see',
            "A start line names the node, and its record holds the exact request. A node that needs the same work sends "
            'that request: if the work is running it joins (one execution, two holders); if it has finished it reuses '
            'the result. There is no flag, and no guessing at similarity.',
            'Build three views over one snapshot', ['openNode', 'readArtifact', 'nextNodeEvent'])
p.N('n1', 'root', 'Build three views over one snapshot', skill='root')
p.N('n2', 'baseline', 'Interpret baseline assumptions', skill='baseline', by='n1')
p.N('n3', 'capacity', 'Interpret capacity', skill='capacity', by='n1')
p.N('n4', 'supply', 'Cross-check supply', skill='supply', by='n1')
p.N('n5', 'snapshot', 'Produce snapshot evidence', skill='snapshot', by='n2', inputs={'as_of': '2026-11-04'})
p.step('n1 opens three orthogonal views and goes idle.',
       [O(None, 'n1'), PAR(O('n1', 'n2'), O('n1', 'n3'), O('n1', 'n4')), I('n1')],
       {'n1': 'Three judgments over the same evidence. None waits on another.'})
p.step('n2 needs snapshot evidence and opens n5. Every stream gets "n2 opened n5 · snapshot · Produce snapshot evidence" at its next turn boundary.',
       [O('n2', 'n5'), I('n2')],
       {'n2': "Opens snapshot with the skill's standard task and inputs.",
        'n3': 'Reading its own inputs. The line reaches it at its next turn.'})
p.step("n3 needs the same evidence. It reads n5's record, finds the exact request, and sends it. n5 is running, so n3 joins.",
       [RD('n3', 'n5'), O('n3', 'n5', 'joined'), I('n3')],
       {'n3': 'Judges from the line that n5 is the evidence it needs, and copies the exact request from the record. The harness only compares identities.',
        'n5': 'Unchanged: same task, now with two holders.'})
p.step('n5 publishes once. Both holders get the result.',
       [C('n5', 'Utilization measured: 91%.'), Rz('n5', 'Snapshot: utilization 91%; demand up 6% q/q.')],
       {'n5': 'Runs once for both.'})
p.step('n2 and n3 publish. n4 reaches the same need later, and the identical request now reuses n5.r1 at once.',
       [PAR(W('n2'), W('n3')),
        PAR(Rz('n2', 'Baseline holds: demand trend intact (n5.r1).', ['n5.r1']),
            Rz('n3', 'Capacity binds before 2027 (n5.r1).', ['n5.r1'])),
        RD('n4', 'n5'), O('n4', 'n5', 'reused')],
       {'n4': 'Its stream already has n5.r1. Sending the request returns that ref without running anything.'})
p.step('n4 publishes, and n1 answers from three views over one snapshot.',
       [Rz('n4', 'Supply tight: transformer lead times of 2 to 4 years (n5.r1).', ['n5.r1']), W('n1'),
        Rz('n1', 'Three views on one snapshot: baseline holds (n2.r1), capacity binds (n3.r1), supply tight (n4.r1).',
           ['n2.r1', 'n3.r1', 'n4.r1'])],
       {'n1': 'All three cite n5.r1: the diamond is in the citations as well as the holds.'})
p.tab('n3 capacity', [
    """// Our stream showed: n2 opened n5 · snapshot · Produce snapshot evidence
const rec = await inspect('n5');             // node record: the exact request
const snap = await nodes.run(rec.request);   // identical, so it joins n5
return snap.line;"""], final='Capacity binds before 2027 (n5.r1).')
p.tab('n4 supply', [
    """const rec = await inspect('n5');             // n5 has finished by now
const snap = await nodes.run(rec.request);   // identical: returns n5.r1 at once
return snap.line;"""], final='Supply tight: transformer lead times of 2 to 4 years (n5.r1).')

p = pattern('fork', 'coordination', 'Fork from a trail',
            "A different aspect is a new task, not a note to shared work. from seeds the new node with the source's trail "
            'as it stands, so it starts where that reasoning is and reuses its prompt cache. The source is never changed.',
            'Ask two more questions of one snapshot', ['openNode', 'nextNodeEvent'])
p.N('n1', 'root', 'Ask two more questions of one snapshot', skill='root')
p.N('n2', 'snapshot', 'Produce snapshot evidence', skill='snapshot', by='n1')
p.N('n3', 'capacity aspect', 'Given this evidence, is capacity binding before 2027?', by='n1', frm='n2')
p.N('n4', 'policy aspect', 'Does this evidence move policy timing?', by='n1', frm='n2')
p.step('n1 opens n2 on snapshot.', [O(None, 'n1'), O('n1', 'n2'), I('n1')], {'n1': 'Holds n2 and waits for progress.'})
p.step("n2.c1: the evidence is collected. n2's trail now holds every tool call and result so far.",
       [C('n2', 'Collected utilization, demand and mix data; interpreting next.'), W('n1')],
       {'n2': 'Keeps interpreting.', 'n1': 'Wakes: the expensive part of the context now exists.'})
p.step('n1 forks twice from n2. Each fork starts from n2.trail as of now, plus its own task. The source keeps running, untouched.',
       [PAR(O('n1', 'n3'), O('n1', 'n4')), I('n1')],
       {'n3': "Starts with n2's context already loaded: same prefix, so the prompt cache hits.",
        'n4': 'Same prefix, different task.', 'n2': 'Never sees the forks except as lines.'})
p.step('All three publish.',
       [Rz('n2', 'Snapshot: utilization 91%; demand up 6% q/q; mix toward large transformers.'),
        Rz('n3', 'Capacity binds before 2027 on this evidence (n2.c1).', ['n2.c1']),
        Rz('n4', 'Policy timing unchanged: nothing here moves it (n2.c1).', ['n2.c1'])],
       {'n3': 'Cites the checkpoint its context was forked at.'})
p.step('n1 answers.', [W('n1'), Rz('n1', 'Snapshot (n2.r1); capacity binds before 2027 (n3.r1); policy timing unchanged (n4.r1).',
                                    ['n2.r1', 'n3.r1', 'n4.r1'])], {'n1': 'Three results, one shared prefix.'})
p.tab('n1 root', [
    """const snap = await nodes.open({node: 'snapshot', task: 'Produce snapshot evidence', inputs});
await snap.next();                     // n2.c1: the evidence is collected
const [cap, pol] = await Promise.all([
  nodes.run({from: snap.node, task: 'Given this evidence, is capacity binding before 2027?'}),
  nodes.run({from: snap.node, task: 'Does this evidence move policy timing?'}),
]);
const base = await snap.result();
return [base.line, cap.line, pol.line];"""],
      final='Snapshot (n2.r1); capacity binds before 2027 (n3.r1); policy timing unchanged (n4.r1).')

p = pattern('settle', 'coordination', 'Settle by talking',
            "Two nodes that disagree talk directly, through addressed checkpoints and each other's trails. One publishes "
            "the settled view citing the exchange, and the other's result cites that view. The diamond closes on one "
            'shared result, with no judge node and no fixed rounds.',
            'Cross-check supply', ['publishCheckpoint', 'readArtifact', 'nextNodeEvent'])
p.N('n1', 'supply', 'Cross-check supply', skill='supply')
p.N('n2', 'alternatives', 'Assess supplier alternatives', skill='alternatives', by='n1')
p.N('n3', 'inventory', 'Interpret inventory protection', skill='inventory', by='n1')
p.step('n1 opens two views. Both depend on a read of demand.',
       [O(None, 'n1'), PAR(O('n1', 'n2'), O('n1', 'n3')), I('n1')], {'n1': 'Opens both and goes idle.'})
p.step('Both publish checkpoints, and the lines disagree about demand.',
       [PAR(C('n2', 'Demand accelerating: orders up 6% q/q. Supplier concentration is the risk.'),
            C('n3', 'Demand flat: shipments flat q/q. Inventory covers two quarters.'))],
       {'n2': 'Sees n3.c1 at its next turn boundary. It contradicts its own premise.',
        'n3': 'Sees n2.c1 the same way.'})
p.step("n2 reads n3's trail to see how it got there, then addresses n3 with one precise question.",
       [RD('n2', 'n3.trail'),
        C('n2', 'We disagree on demand: I read +6% from orders, you read flat from shipments. Which leads?', 'n3'), I('n2')],
       {'n2': 'Reads the turns where n3 pulled shipment data.',
        'n3': 'Gets n2.c2 at its next turn boundary, marked as addressed to it.'})
p.step("n3 reads n2's trail and replies.",
       [RD('n3', 'n2.trail'),
        C('n3', 'Orders lead shipments by about a quarter, so yours leads. Mine shows the lag, not a slowdown: call it +3%, not +6%.', 'n2')],
       {'n3': 'Concedes direction, corrects magnitude.', 'n2': 'Wakes on the reply.'})
p.step("n2 publishes the settled view, citing both sides of the exchange. That is n2.c3, the diamond's bottom vertex.",
       [C('n2', 'Settled: demand accelerating about 3% q/q; orders lead shipments by a quarter.', None, ['n2.c2', 'n3.c2'])],
       {'n2': 'Writes the view both nodes will rest on.', 'n3': 'Sees n2.c3 arrive; it matches what they agreed.'})
p.step('Both results cite n2.c3. n3 changed its own conclusion; nobody overruled it.',
       [PAR(Rz('n2', 'Concentration risk is real at +3% demand (n2.c3).', ['n2.c3']),
            Rz('n3', 'Inventory covers one quarter at +3% demand, not two (n2.c3).', ['n2.c3']))],
       {'n2': 'Publishes.', 'n3': 'Publishes a different conclusion than its own first checkpoint.'})
p.step('n1 answers, and both views rest on one demand read.',
       [W('n1'), Rz('n1', 'Both views rest on one demand read (n2.c3): concentration risk is real (n2.r1); inventory covers one quarter (n3.r1).',
                     ['n2.r1', 'n3.r1'])],
       {'n1': 'Never had to referee. It sees the settlement in the citations.'})
p.tab('n2 alternatives', [
    """// n3.c1 says demand is flat; ours says accelerating. Look before arguing.
return await read('n3.trail');""",
    """await tools.publishCheckpoint({to: 'n3', content:
  'We disagree on demand: I read +6% from orders, you read flat from shipments. Which leads?'});
return await nodes.next();     // idle until n3 answers""",
    """// n3.c2: orders lead shipments by a quarter; the size is nearer +3%.
await tools.publishCheckpoint({content:
  'Settled: demand accelerating about 3% q/q; orders lead shipments by a quarter. (n2.c2, n3.c2)'});"""],
      final='Concentration risk is real at +3% demand (n2.c3).')

p = pattern('steer', 'coordination', 'Steer while idle',
            "An idle parent reads its children's lines as they arrive. When one drifts, it sends a note within the "
            "child's task, and the child adjusts at its next turn. When a branch stops mattering, the parent closes it.",
            'Assess AI-power capacity at the ETF level', ['nextNodeEvent', 'publishCheckpoint', 'closeNode'])
p.N('n1', 'root', 'Assess AI-power capacity at the ETF level', skill='root')
p.N('n2', 'capacity', 'Assess capacity for XLU and XLI holdings', skill='capacity', by='n1')
p.N('n3', 'supply', 'Assess supply constraints for XLI holdings', skill='supply', by='n1')
p.N('n4', 'policy', 'Outline policy timing for grid capex', skill='policy', by='n1')
p.step('n1 opens three views and goes idle.',
       [O(None, 'n1'), PAR(O('n1', 'n2'), O('n1', 'n3'), O('n1', 'n4')), I('n1')], {'n1': 'Holds all three.'})
p.step("n2.c1 shows drift: single names are outside this run's scope. n1 wakes on the line.",
       [C('n2', 'Drilling into single names: NEE, SO and DUK capex plans.'), W('n1')],
       {'n2': 'Following data wherever it leads.', 'n1': 'Reads the line and sees the drift.'})
p.step("n1 sends n2 a note within its task. It arrives at n2's next turn boundary, and n2's task is unchanged.",
       [C('n1', 'Stay at the ETF level (XLU, XLI). Single names are out of scope for this run.', 'n2'), I('n1')],
       {'n2': 'Reads the note as guidance from its opener and drops the single-name work.'})
p.step('n3 publishes, and its result already covers policy timing.',
       [Rz('n3', 'Supply binds through 2028: transformer lead times of 2 to 4 years; no policy fix before then.'), W('n1')],
       {'n1': 'Sees that n4 would only repeat what n3.r1 says.'})
p.step('n4 no longer matters, so n1 closes it. Nobody else holds n4, so it is cancelled.',
       [X('n1', 'n4'), I('n1')], {'n4': 'Cancelled: its last holder left.'})
p.step('n2 publishes at the ETF level.',
       [C('n2', 'Back at ETF level: XLU utilities capex up 12% y/y in aggregate.'),
        Rz('n2', 'Capacity binds for XLU and XLI holdings through 2027 (n2.c2).', ['n2.c2'])],
       {'n2': 'Finishes within the scope it was steered back to.'})
p.step('n1 answers.',
       [W('n1'), Rz('n1', 'Capacity binds through 2027 (n2.r1); supply binds through 2028 (n3.r1).', ['n2.r1', 'n3.r1'])],
       {'n1': 'One steer, one close, no restarts.'})
p.tab('n1 root', [
    """const [cap, sup, pol] = await Promise.all([
  nodes.open({node: 'capacity', task: 'Assess capacity for XLU and XLI holdings'}),
  nodes.open({node: 'supply', task: 'Assess supply constraints for XLI holdings'}),
  nodes.open({node: 'policy', task: 'Outline policy timing for grid capex'}),
]);
return await nodes.next();       // idle until lines arrive""",
    """// n2.c1 drifted into single names. Steer it, within its task.
await tools.publishCheckpoint({to: cap.node, content:
  'Stay at the ETF level (XLU, XLI). Single names are out of scope for this run.'});
return await nodes.next();""",
    """// n3.r1 already answers policy timing: n4 no longer matters.
await pol.close();               // nobody else holds n4, so it is cancelled
return await Promise.all([cap.result(), sup.result()]);"""],
      final='Capacity binds through 2027 (n2.r1); supply binds through 2028 (n3.r1).')

p = pattern('ask', 'coordination', 'Ask the user',
            "Any node can address you, and you can address any node. The asking node isn't blocked: it keeps working on "
            'what needs no answer, and your reply arrives as a line addressed to it.',
            'Size a TLT position', ['publishCheckpoint', 'nextNodeEvent'], user=True)
p.N('n1', 'root', 'Size a TLT position', skill='root', by='you')
p.N('n2', 'sizing', 'Size a TLT position', skill='sizing', by='n1')
p.step('You open the run. n1 opens n2 to size the position.',
       [O('you', 'n1'), O('n1', 'n2'), I('n1')], {'you': 'Asks for a size.', 'n1': 'Delegates and waits.'})
p.step('The request has no risk budget, so n2 asks you directly. The line reaches your view and every stream.',
       [C('n2', 'What risk budget (bps of NAV) and horizon should I size TLT to?', 'you')],
       {'n2': 'Asks, then keeps working: realized vol and ATR need no answer.'})
p.step('n2 does the part that needs no answer, then waits.',
       [C('n2', 'TLT 20-day realized vol 14.8%; ATR 1.9.'), I('n2')],
       {'n2': 'Idle in nextNodeEvent until a reply arrives.'})
p.step('You reply to n2. you.m1 is a line addressed to n2, and it wakes n2.',
       [M('n2', '50 bps of NAV, 20 trading days.')], {'you': 'Answers the node that asked, not the root.'})
p.step('n2 sizes, citing your answer.',
       [Rz('n2', 'Size 1,850 shares: 50 bps of NAV at one 20-day sigma (you.m1, n2.c2).', ['you.m1', 'n2.c2'])],
       {'n2': 'Your message is a ref like any other, so the size traces back to it.'})
p.step('n1 answers.', [W('n1'), Rz('n1', 'Buy 1,850 TLT (n2.r1).', ['n2.r1'])], {'n1': 'Cites the sizing.'})
p.tab('n2 sizing', [
    """// No risk budget in the request: ask, and keep going.
await tools.publishCheckpoint({to: 'you', content:
  'What risk budget (bps of NAV) and horizon should I size TLT to?'});
const vol = await realizedVol('TLT', 20);      // the how, inside this node
await tools.publishCheckpoint({content: `TLT 20-day realized vol ${vol}%; ATR 1.9.`});
return await nodes.next();                     // idle until a reply"""],
      final='Size 1,850 shares: 50 bps of NAV at one 20-day sigma (you.m1, n2.c2).')

p = pattern('reopen', 'coordination', 'Reopen on news',
            'The run stays open after the root answers. News reaches the root, which traces which results cite what the '
            'news touches and reopens only those. A reopened node continues its own session and publishes its next '
            'version; a node whose conclusion holds says so, and the change stops there.',
            'Keep the capacity view current', ['publishCheckpoint', 'nextNodeEvent', 'readArtifact'], user=True)
p.N('n1', 'root', 'Keep the capacity view current', skill='root', by='you')
p.N('n2', 'snapshot', 'Produce snapshot evidence', skill='snapshot', by='n1')
p.N('n3', 'capacity', 'Interpret capacity from n2.r1', skill='capacity', by='n1')
p.N('n4', 'supply', 'Cross-check supply from n2.r1', skill='supply', by='n1')
p.N('n5', 'policy', 'Outline policy timing', skill='policy', by='n1')
p.pre = [O('you', 'n1'), O('n1', 'n2'), Rz('n2', 'Snapshot: utilization 91%; demand up 6% q/q.'),
         O('n1', 'n3'), O('n1', 'n4'), O('n1', 'n5'),
         Rz('n3', 'Capacity binds before 2027 (n2.r1).', ['n2.r1']),
         Rz('n4', 'Transformer shortfall through 2028 (n2.r1).', ['n2.r1']),
         Rz('n5', 'No policy relief before 2027.'),
         Rz('n1', 'Capacity binds (n3.r1); supply short through 2028 (n4.r1); no policy relief (n5.r1).',
            ['n3.r1', 'n4.r1', 'n5.r1'])]
p.step('Days after the run answered, you send news to n1. n1 had finished, so the message reopens it in its own session, with its trail intact.',
       [M('n1', 'Utilization data revised: 88%, not 91%.')],
       {'you': 'Sends the news to the root, not to the node you think it touches.',
        'n1': 'Reopened. Its stream already shows that n3.r1 and n4.r1 cite n2.r1, and n5.r1 cites nothing upstream.'})
p.step('n1 reopens n2 first, because the news touches the source. n1 holds n2 until its next result.',
       [C('n1', 'Utilization revised to 88% (you.m1). Re-derive the snapshot.', 'n2', ['you.m1']), I('n1')],
       {'n2': 'Reopened with its whole trail: it revises the one number instead of redoing the snapshot.'})
p.step('n2 publishes r2. n2.r1 is unchanged and still citable, and the lines show both.',
       [Rz('n2', 'Snapshot r2: utilization 88%, was 91%; demand up 6% q/q (you.m1).', ['you.m1'])],
       {'n2': 'Publishes its next version.'})
p.step('n1 reopens only the two results that cite n2.r1. n5 cites nothing the news touched, so it stays as it is.',
       [W('n1'), PAR(C('n1', 'n2.r2 replaces n2.r1: utilization 88%, was 91%. Does your view change?', 'n3', ['n2.r2']),
                     C('n1', 'n2.r2 replaces n2.r1: utilization 88%, was 91%. Does your view change?', 'n4', ['n2.r2'])),
        I('n1')],
       {'n1': 'Chooses what to reopen from the cites in the result lines. Nothing is recomputed by rule.',
        'n5': 'Untouched.'})
p.step('n3 holds, so the change stops there. n4 changed.',
       [PAR(Rz('n3', 'Holds: capacity still binds before 2027 at 88% (n2.r2).', ['n2.r2']),
            Rz('n4', 'Changed: the shortfall eases one quarter, through Q3 2028 (n2.r2).', ['n2.r2']))],
       {'n3': 'Re-decides in its own session and keeps its conclusion: r2 records the re-check.',
        'n4': 'Re-decides and changes its conclusion.'})
p.step('n1 publishes r2. Exactly the results the news touched have moved.',
       [W('n1'), Rz('n1', 'Capacity still binds (n3.r2); supply short through Q3 2028 (n4.r2); policy unchanged (n5.r1).',
                     ['n3.r2', 'n4.r2', 'n5.r1'])],
       {'n1': 'Cites the new versions, and the unchanged n5.r1.'})
p.tab('n1 root (reopened)', [
    """// Reopened by you.m1. The result lines already show who cites what:
//   n3.r1 · … · cites n2.r1     n4.r1 · … · cites n2.r1     n5.r1 · …
await tools.publishCheckpoint({to: 'n2', content:
  'Utilization revised to 88% (you.m1). Re-derive the snapshot.'});
return await nodes.next();       // n2 reopens; n1 holds it until n2.r2""",
    """// n2.r2 arrived. Reopen only the results that cite n2.r1.
for (const to of ['n3', 'n4'])
  await tools.publishCheckpoint({to, content:
    'n2.r2 replaces n2.r1: utilization 88%, was 91%. Does your view change?'});
return await nodes.next();"""],
      final='Capacity still binds (n3.r2); supply short through Q3 2028 (n4.r2); policy unchanged (n5.r1).')

# ---------------------------------------------------------------- validation

p = pattern('retry', 'validation', 'Retry without blocking',
            "A failure belongs to one node. Identical requests never join failed work, so sending the same request again "
            'starts a fresh node, while siblings carry on.',
            'Gather market inputs', ['openNode', 'nextNodeEvent'])
p.N('n1', 'root', 'Gather market inputs', skill='root')
p.N('n2', 'quotes', 'Fetch end-of-day quotes for the watchlist', skill='quotes', by='n1')
p.N('n3', 'news', 'Summarize overnight news for the watchlist', skill='news', by='n1')
p.N('n4', 'quotes', 'Fetch end-of-day quotes for the watchlist', skill='quotes', by='n1')
p.step('n1 opens two independent inputs.', [O(None, 'n1'), PAR(O('n1', 'n2'), O('n1', 'n3')), I('n1')],
       {'n1': 'Holds both.'})
p.step('n2 fails. Only n1, which holds it, has anything to decide; n3 keeps going.',
       [F('n2', 'vendor timeout after 30 s'), W('n1')], {'n2': 'Failed.', 'n3': 'Unaffected.'})
p.step("n1 sends the identical request again. n2 failed, so nothing is joined: the harness starts n4.",
       [O('n1', 'n4'), I('n1'), C('n3', 'Fed speakers and two guidance cuts so far.')],
       {'n1': 'No key needed: failed work is never joined.', 'n4': 'A fresh node with the same task as n2.'})
p.step('Both publish.',
       [PAR(Rz('n4', 'Quotes for 42 names at 16:00.'), Rz('n3', 'Overnight: two guidance cuts; Fed speakers lean hawkish.'))],
       {'n4': 'Succeeds.', 'n3': 'Publishes.'})
p.step('n1 answers.', [W('n1'), Rz('n1', 'Inputs ready: quotes (n4.r1) and news (n3.r1).', ['n4.r1', 'n3.r1'])],
       {'n1': 'n2 stays in the trail as a failed node.'})
p.tab('n1 root', [
    """const quotes = {node: 'quotes', task: 'Fetch end-of-day quotes for the watchlist'};
const news = nodes.run({node: 'news', task: 'Summarize overnight news for the watchlist'});
let q;
try { q = await nodes.run(quotes); }
catch { q = await nodes.run(quotes); }   // n2 failed, so this starts n4
return [q.line, (await news).line];"""], final='Inputs ready: quotes (n4.r1) and news (n3.r1).')

p = pattern('review', 'validation', 'Review and revise',
            'A reviewer reads the draft and the trail behind it, and publishes a verdict. A failing verdict goes to the '
            'draft as an addressed checkpoint, which reopens it: the author revises in its own session and publishes r2. '
            'The approval cites the exact version it reviewed. How many rounds to allow is the caller\'s call.',
            'Produce an approved thesis', ['openNode', 'publishCheckpoint', 'nextNodeEvent', 'readArtifact'])
p.N('n1', 'root', 'Produce an approved thesis', skill='root')
p.N('n2', 'thesis-draft', 'Draft the AI-power LEAPS thesis', skill='thesis-draft', by='n1')
p.N('n3', 'red-team', 'Review n2.r1: pass or fail, with findings', skill='red-team', by='n1')
p.step('n1 opens the draft.', [O(None, 'n1'), O('n1', 'n2'), I('n1')], {'n1': 'Waits for r1.'})
p.step('n2 publishes r1. n1 opens a reviewer whose task cites n2.r1.',
       [Rz('n2', 'Draft: start XLI LEAPS now; the AI-power capex cycle is intact through 2027.'), W('n1'), O('n1', 'n3'), I('n1')],
       {'n3': 'Starts with the exact version to review in its task.'})
p.step('n3 reads the draft and the trail behind it, then fails it with findings.',
       [RD('n3', 'n2.trail'), Rz('n3', 'Fail: the rates path is assumed flat, and financing risk is never tested (n2.r1).', ['n2.r1'])],
       {'n3': 'Reads how n2 reached its view, not just the view.'})
p.step('n1 sends the review to n2. n2 had finished, so the note reopens it in its own session.',
       [W('n1'), C('n1', 'Revise for n3.r1: test a higher-for-longer rates path, and financing.', 'n2', ['n3.r1']), I('n1')],
       {'n2': 'Reopened with its whole trail: it revises instead of redrafting from scratch.'})
p.step('n2 publishes r2. r1 stays in the record, unchanged.',
       [Rz('n2', 'Draft r2: start half now; financing holds unless IG spreads pass 200bp (n3.r1).', ['n3.r1'])],
       {'n2': 'Its r2 cites the review it answers.'})
p.step('n1 reopens n3 to review the new version.',
       [W('n1'), C('n1', 'Review n2.r2.', 'n3', ['n2.r2']), I('n1')],
       {'n3': 'Reopened with its first review in context, so it checks exactly what it asked for.'})
p.step('n3 passes r2.', [Rz('n3', 'Pass: rates and financing are now tested (n2.r2).', ['n2.r2'])],
       {'n3': 'Its r2 cites the version it passed.'})
p.step('n1 approves the exact version that passed.',
       [W('n1'), Rz('n1', 'Approved thesis: n2.r2, passed by n3.r2.', ['n2.r2', 'n3.r2'])],
       {'n1': 'The approval names versions, so a later r3 cannot inherit it.'})
p.tab('n1 root', [
    """const draft = await nodes.run({node: 'thesis-draft', task: 'Draft the AI-power LEAPS thesis'});
const review = await nodes.run({node: 'red-team',
  task: `Review ${draft.ref}: pass or fail, with findings`});
return review.line;""",
    """// n3.r1 failed it. Send the review to the draft: that reopens n2.
await tools.publishCheckpoint({to: draft.node, content:
  `Revise for ${review.ref}: test a higher-for-longer rates path, and financing.`});
return await nodes.next();       // n2.r2""",
    """await tools.publishCheckpoint({to: review.node, content: 'Review n2.r2.'});
return await nodes.next();       // n3.r2: pass"""],
      final='Approved thesis: n2.r2, passed by n3.r2.')

p = pattern('redteam', 'validation', 'Red team',
            "Three adversaries with different tasks are three nodes. Independence is a choice about what to read: each "
            "sees the others' lines, but none reads the others' work before publishing its own.",
            'Stress-test the thesis', ['openNode', 'readArtifact', 'nextNodeEvent'])
p.N('n1', 'root', 'Stress-test the thesis', skill='root')
p.N('n2', 'thesis-draft', 'Draft the AI-power LEAPS thesis', skill='thesis-draft', by='n1')
for i, who in enumerate(['a rates bear', 'a liquidity skeptic', 'a data auditor']):
    p.N(f'n{i + 3}', who.split(' ', 1)[1], f'As {who}, attack n2.r1', skill='red-team', by='n1')
p.step('n1 opens the draft.', [O(None, 'n1'), O('n1', 'n2'), I('n1')], {'n1': 'Waits for r1.'})
p.step('Three tasks, three identities, three nodes. Each task cites n2.r1.',
       [Rz('n2', 'Draft: start XLI LEAPS now; capex cycle intact through 2027.'), W('n1'),
        PAR(O('n1', 'n3'), O('n1', 'n4'), O('n1', 'n5')), I('n1')],
       {'n1': 'Different personas are different tasks, so they cannot collapse into one shared run.'})
p.step("Each adversary reads the draft's trail. None reads another adversary's work, even as its lines arrive.",
       [PAR(RD('n3', 'n2.trail'), RD('n4', 'n2.trail'), RD('n5', 'n2.trail'))],
       {'n3': 'Reads n2.trail only.', 'n4': 'Sees n3\'s lines but does not open them.', 'n5': 'Same.'})
p.step('The attacks start landing.',
       [C('n4', 'LEAPS open interest is thin beyond the 2027 strikes.'),
        Rz('n3', 'Rates bear: two 2027 hikes cut LEAPS value about 8% (n2.r1).', ['n2.r1'])],
       {'n4': 'Its checkpoint is visible to the others; they leave it unread.'})
p.step('The other two publish.',
       [Rz('n4', 'Liquidity: exits beyond the 2027 strikes cost 3 to 5% in spread (n2.r1).', ['n2.r1']),
        Rz('n5', 'Data: the capex series mixes guidance and actuals (n2.r1).', ['n2.r1'])],
       {'n5': 'Independent of the other two by what it chose not to read.'})
p.step('n1 collects three independent attacks.',
       [W('n1'), Rz('n1', 'Three attacks on n2.r1: rates (n3.r1), liquidity (n4.r1), data mixing (n5.r1).',
                     ['n3.r1', 'n4.r1', 'n5.r1'])], {'n1': 'Each attack cites the draft, none cites another.'})
p.tab('n1 root', [
    """const draft = await nodes.run({node: 'thesis-draft', task: 'Draft the AI-power LEAPS thesis'});
const personas = ['a rates bear', 'a liquidity skeptic', 'a data auditor'];
const attacks = await Promise.all(personas.map(who => nodes.run({node: 'red-team',
  task: `As ${who}, attack ${draft.ref}`})));
return attacks.map(a => a.line);"""],
      final='Three attacks on n2.r1: rates (n3.r1), liquidity (n4.r1), data mixing (n5.r1).')

# -------------------------------------------------------------- compositions

p = pattern('screening', 'composition', 'Screen with recovery',
            'A screen that survives a slow vendor and a flaky one: a race for the vol surface, a fan-out of per-name '
            'judgments that cite the winner, one retry, a ranking, then an audit.',
            'Rank four ETFs by long-dated premium richness', ['openNode', 'nextNodeEvent', 'closeNode', 'readArtifact'],
            big=True)
p.N('n1', 'root', 'Rank four ETFs by long-dated premium richness', skill='root')
p.N('n2', 'vol-surface A', 'Fetch long-dated vol surfaces for SPY, QQQ, IWM, TLT', skill='vol-surface', by='n1', inputs={'vendor': 'A'})
p.N('n3', 'vol-surface B', 'Fetch long-dated vol surfaces for SPY, QQQ, IWM, TLT', skill='vol-surface', by='n1', inputs={'vendor': 'B'})
for i, t in enumerate(['SPY', 'QQQ', 'IWM', 'TLT']):
    p.N(f'n{i + 4}', f'screen {t}', f"Is {t}'s long-dated premium rich or cheap on n3.r1?", skill='screen', by='n1')
p.N('n8', 'screen TLT', "Is TLT's long-dated premium rich or cheap on n3.r1?", skill='screen', by='n1')
p.N('n9', 'rank', 'Rank by premium richness: n4.r1, n5.r1, n6.r1, n8.r1', skill='rank', by='n1')
p.N('n10', 'coherence', 'Check n9.r1 for consistent units and scope', skill='coherence', by='n1')
p.step('A race for the surface: two vendors, one task.', [O(None, 'n1'), PAR(O('n1', 'n2'), O('n1', 'n3')), I('n1')],
       {'n1': 'Holds both vendors.'})
p.step('Vendor B wins. n1 closes A, which is cancelled.',
       [Rz('n3', 'Vol surfaces for SPY, QQQ, IWM and TLT from vendor B.'), W('n1'), X('n1', 'n2')],
       {'n2': 'Cancelled: no holders left.'})
p.step('Four judgments at once, each citing the winning surface.',
       [PAR(O('n1', 'n4'), O('n1', 'n5'), O('n1', 'n6'), O('n1', 'n7')), I('n1')],
       {'n1': 'Every task names n3.r1, so every screen reads the same surface.'})
p.step('Three publish and TLT fails on a quote gap.',
       [PAR(Rz('n4', 'SPY cheap: IV 31st percentile (n3.r1).', ['n3.r1']),
            Rz('n5', 'QQQ rich: IV 78th percentile (n3.r1).', ['n3.r1']),
            Rz('n6', 'IWM fair: IV 52nd percentile (n3.r1).', ['n3.r1']),
            F('n7', 'quote gap in TLT strikes'))], {'n7': 'Failed; nothing else waits on it.'})
p.step('n1 resends the identical TLT request; failed work is never joined, so n8 starts.',
       [W('n1'), O('n1', 'n8'), I('n1')], {'n8': 'Same task as n7, fresh node.'})
p.step('TLT publishes. n1 opens the ranking over four results.',
       [Rz('n8', 'TLT rich: IV 70th percentile on refreshed strikes (n3.r1).', ['n3.r1']), W('n1'), O('n1', 'n9'), I('n1')],
       {'n9': 'Ranks four refs.'})
p.step('The ranking publishes. n1 opens an audit over it.',
       [Rz('n9', 'Richest: QQQ, then TLT; IWM fair; SPY cheap.', ['n4.r1', 'n5.r1', 'n6.r1', 'n8.r1']),
        W('n1'), O('n1', 'n10'), I('n1')], {'n10': 'Checks n9.r1 and how it was produced.'})
p.step('The audit reads the ranking\'s trail and passes it.',
       [RD('n10', 'n9.trail'), Rz('n10', 'Pass: one surface (n3.r1) and one unit throughout n9.r1.', ['n9.r1', 'n3.r1'])],
       {'n10': 'Audits the trail, not just the table.'})
p.step('n1 answers.', [W('n1'), Rz('n1', 'QQQ and TLT are richest (n9.r1); the audit passed (n10.r1).', ['n9.r1', 'n10.r1'])],
       {'n1': 'Two citations stand on ten nodes.'})
p.built = {'race': ['n1', 'n2', 'n3'], 'fanout': ['n1', 'n4', 'n5', 'n6', 'n7'], 'retry': ['n1', 'n7', 'n8'],
           'review': ['n1', 'n9', 'n10']}
p.tab('n1 root', [
    """const ops = await Promise.all(['A', 'B'].map(vendor => nodes.open({node: 'vol-surface',
  task: 'Fetch long-dated vol surfaces for SPY, QQQ, IWM, TLT', inputs: {vendor}})));
const surface = await Promise.race(ops.map(op => op.result()));
await Promise.all(ops.map(op => op.close()));""",
    """const screen = t => ({node: 'screen',
  task: `Is ${t}'s long-dated premium rich or cheap on ${surface.ref}?`});
const names = ['SPY', 'QQQ', 'IWM', 'TLT'];
const first = await Promise.allSettled(names.map(t => nodes.run(screen(t))));
const views = await Promise.all(first.map((s, i) =>
  s.status === 'fulfilled' ? s.value : nodes.run(screen(names[i]))));   // TLT starts n8""",
    """const rank = await nodes.run({node: 'rank',
  task: `Rank by premium richness: ${views.map(v => v.ref).join(', ')}`});
const audit = await nodes.run({node: 'coherence',
  task: `Check ${rank.ref} for consistent units and scope`});
return [rank.line, audit.line];"""],
      final='QQQ and TLT are richest (n9.r1); the audit passed (n10.r1).')

p = pattern('thesis', 'composition', 'Validated thesis',
            'Three views share one snapshot through a join and a reuse; a draft cites the views; a review fails the '
            'draft and reopens it; the approval cites the exact versions. Each part is a pattern above.',
            'Produce an approved thesis', ['openNode', 'nextNodeEvent', 'publishCheckpoint', 'readArtifact'], big=True)
p.N('n1', 'root', 'Produce an approved thesis', skill='root')
p.N('n2', 'baseline', 'Interpret baseline assumptions', skill='baseline', by='n1')
p.N('n3', 'capacity', 'Interpret capacity', skill='capacity', by='n1')
p.N('n4', 'supply', 'Cross-check supply', skill='supply', by='n1')
p.N('n5', 'snapshot', 'Produce snapshot evidence', skill='snapshot', by='n2', inputs={'as_of': '2026-11-04'})
p.N('n6', 'thesis-draft', 'Draft the thesis from n2.r1, n3.r1, n4.r1', skill='thesis-draft', by='n1')
p.N('n7', 'red-team', 'Review n6.r1', skill='red-team', by='n1')
p.step('Three views at once.', [O(None, 'n1'), PAR(O('n1', 'n2'), O('n1', 'n3'), O('n1', 'n4')), I('n1')],
       {'n1': 'Opens three orthogonal judgments.'})
p.step('n2 opens the snapshot. n3 sees the line, sends the same request, and joins.',
       [O('n2', 'n5'), I('n2'), RD('n3', 'n5'), O('n3', 'n5', 'joined'), I('n3')],
       {'n3': 'Joins n5 instead of starting a second snapshot.'})
p.step('The snapshot publishes once for both holders.',
       [Rz('n5', 'Snapshot: utilization 91%; demand up 6% q/q.'), PAR(W('n2'), W('n3'))], {'n5': 'Runs once.'})
p.step('Two views publish. n4 reuses the finished snapshot.',
       [PAR(Rz('n2', 'Baseline holds (n5.r1).', ['n5.r1']), Rz('n3', 'Capacity binds before 2027 (n5.r1).', ['n5.r1'])),
        RD('n4', 'n5'), O('n4', 'n5', 'reused')], {'n4': 'Reuse: nothing runs.'})
p.step('n4 publishes. n1 opens a draft that cites all three views.',
       [Rz('n4', 'Supply short through 2028 (n5.r1).', ['n5.r1']), W('n1'), O('n1', 'n6'), I('n1')],
       {'n6': 'Its task names the three refs it builds on.'})
p.step('The draft publishes. n1 opens a review of it.',
       [Rz('n6', 'Draft: start XLI LEAPS now (n2.r1, n3.r1, n4.r1).', ['n2.r1', 'n3.r1', 'n4.r1']), W('n1'), O('n1', 'n7'), I('n1')],
       {'n7': 'Reviews n6.r1.'})
p.step('The review reads the draft\'s trail and fails it.',
       [RD('n7', 'n6.trail'), Rz('n7', 'Fail: financing is untested (n6.r1).', ['n6.r1'])], {'n7': 'Fails r1.'})
p.step('n1 sends the review to the draft, which reopens it.',
       [W('n1'), C('n1', 'Revise for n7.r1: test financing.', 'n6', ['n7.r1']), I('n1')],
       {'n6': 'Revises in its own session.'})
p.step('r2 publishes, and n1 reopens the review.',
       [Rz('n6', 'Draft r2: start half now; financing holds below 200bp IG spreads (n7.r1).', ['n7.r1']),
        W('n1'), C('n1', 'Review n6.r2.', 'n7', ['n6.r2']), I('n1')], {'n7': 'Re-checks exactly what it asked for.'})
p.step('The review passes r2.', [Rz('n7', 'Pass (n6.r2).', ['n6.r2'])], {'n7': 'Cites the version it passed.'})
p.step('n1 approves the exact versions.', [W('n1'), Rz('n1', 'Approved: n6.r2, passed by n7.r2.', ['n6.r2', 'n7.r2'])],
       {'n1': 'Cites versions, so the approval cannot drift.'})
p.built = {'join': ['n2', 'n3', 'n4', 'n5'], 'fanout': ['n1', 'n2', 'n3', 'n4'], 'review': ['n1', 'n6', 'n7']}
p.tab('n1 root', [
    """const views = await Promise.all([
  ['baseline', 'Interpret baseline assumptions'],
  ['capacity', 'Interpret capacity'],
  ['supply', 'Cross-check supply'],
].map(([node, task]) => nodes.run({node, task, inputs})));""",
    """const draft = await nodes.run({node: 'thesis-draft',
  task: `Draft the thesis from ${views.map(v => v.ref).join(', ')}`});
const review = await nodes.run({node: 'red-team', task: `Review ${draft.ref}`});""",
    """// n7.r1 failed it: reopen the draft, then the review.
await tools.publishCheckpoint({to: draft.node, content: `Revise for ${review.ref}: test financing.`});
await nodes.next();                                   // n6.r2
await tools.publishCheckpoint({to: review.node, content: 'Review n6.r2.'});
await nodes.next();                                   // n7.r2: pass"""],
      final='Approved: n6.r2, passed by n7.r2.')
p.tab('n3 capacity', [
    """// Our stream showed: n2 opened n5 · snapshot · Produce snapshot evidence
const snap = await nodes.run((await inspect('n5')).request);   // joins n5
return snap.line;"""], final='Capacity binds before 2027 (n5.r1).')
