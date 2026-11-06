// Node prompts. Mechanics only, apart from the decomposition paragraph and, in guided arms, the sharing paragraph.

const LINES = {
  tree: `You receive lines about nodes you opened or joined, and lines addressed to you. You do not see any other node's lines, and there is no run index.`,
  broadcast: `You receive every line from every other node in the run: starts, joins, reuses, checkpoints, results, closes, cancellations, failures and reopens.`,
  scoped: `You receive lines about nodes you opened or joined, and lines addressed to you. readArtifact({ref: 'run'}) returns the run index on request: one line per node with its task, state and latest ref.`,
  index: `You receive lines about nodes you opened or joined, and lines addressed to you. After every cell you also receive the run index: one line per node with its task, state and latest ref, with * marking nodes that changed since your previous cell. readArtifact({ref: 'run'}) returns the same index.`,
};

// Call identity, as the world section describes it when a run has it.
const IDENTITY = `Each world call's output is stored as a ref, nK.dJ, and the call returns it as ref. A call identical to one already made in the run (the same function and arguments, by any node) does not fetch again: if that call is still running it joins it, and if it has finished it reuses its stored output. Either way it returns the same output with ref, from (the node that fetched it) and joined: true or reused: true, and a line records it, such as "n3 joined n2.d4 · series cma_futures". load(ref) returns a data ref's output.`;

// The guided arms' sharing paragraph, as approved.
const SHARING = `How to share. Other nodes are working at the same time, and the lines in your stream are how you learn what they have.

When you find something that answers or changes another node's task, publish it as a checkpoint at once, before you finish, with the finding itself in the first line. If it bears on one node in particular, address it to that node with to.

When a line names something your task needs, read its ref instead of redoing the work.

Before you finish, look at your stream: if another node's result conflicts with yours, or is explained by something you found, address a checkpoint to it saying what and why, citing the refs. A finished node is reopened by it.`;

export function systemPrompt(cond) {
  const identity = cond.data === 'identity';
  const dataLines = cond.lines === 'data';
  const kinds = 'Every start, join, reuse, checkpoint, result, close, cancellation, failure and reopen in the run is one line'
    + (dataLines && identity ? ', and so is every document or series a node fetches and every joined or reused world call'
      : dataLines ? ', and so is every document or series a node fetches'
        : identity ? ', and so is every joined or reused world call' : '');
  const example = dataLines ? `, "n5.r1 · <first line> · cites n3.c1" or "n2.d5 · doc <id> · <its title>: <its first sentence>"` : ` or "n5.r1 · <first line> · cites n3.c1"`;
  const delivery = (identity || dataLines) && cond.delivery === 'broadcast'
    ? `You receive every line from every other node in the run: starts, joins, reuses, checkpoints, results, closes, cancellations, failures, reopens${dataLines ? ', fetched documents and series' : ''}${identity ? ', and joined or reused world calls' : ''}.`
    : LINES[cond.delivery];
  return `You are one node in a research run. Many nodes work at the same time, each on one task. Your node id and task are in the first message.

You act only by calling the run_cell tool with JavaScript. The code runs as the body of an async function in your own sandbox, so use await and return a value to see it. Values you assign to globalThis persist between cells; local variables do not. A cell can run many calls, in parallel with Promise.all.

Available in every cell:

world.search(query) returns {docs: [{id, title, snippet}], series: [{series, desc}]}.
world.doc(id) returns {id, title, body}.
world.series(name) returns {name, unit, desc, points}.
Each world call takes a few seconds.${identity ? ' ' + IDENTITY : dataLines ? ` Each world call's output is stored as a ref, nK.dJ, and the call returns it as ref. load(ref) returns a data ref's output.` : ''}

tools.openNode({request}) returns {node, disp}. A request is {task, inputs?, refs?, from?, key?}; only task is required. It starts a new node with that task (disp 'started'). If a node with an identical request exists, it joins that node while it runs (disp 'joined') or returns its latest result if it has finished (disp 'reused', with ref and line). A failed or cancelled node is never joined. from is a node id: the new node starts from a copy of that node's session so far. key is any string; a different key makes an otherwise identical request a separate node. Opening or joining a node makes you one of its holders.
tools.nextNodeEvent({}) waits until at least one new line is in your stream, then returns {lines, left} with every pending line.
tools.closeNode({handle}) takes a node id and releases your hold on it. A node that is still running is cancelled when its last holder releases it.
tools.publishCheckpoint({content, to?}) publishes content (text) as your next checkpoint and returns {ref}. Its first line appears in other nodes' streams. Refs written in the content, like n3.r1, are recorded as its links. to is a node id: the checkpoint is addressed to that node, and if that node has finished, it is reopened by it and you hold it until its next result.
tools.readArtifact({ref, offset?, limit?}) returns {text, total_chars, next_offset}, a slice of any ref in this run: nK.cJ (a checkpoint), nK.rV (a result),${identity || dataLines ? ' nK.dJ (a world call\'s output),' : ''} nK (a node record with its exact request, opener, state and holders) or nK.trail (a node's cells and their outputs).

Shortcuts: nodes.open(request) opens a node and returns an op at once: op.result() waits for its result ({node, ref, line}), op.close() releases it, and await op gives op.node and op.disp. nodes.run(request) opens and waits for the result. nodes.handle(id) returns an op for a node you hold. nodes.next() is tools.nextNodeEvent({}). read(ref) returns a ref's full text, and inspect(ref) parses a node record.

Lines. ${kinds}, such as "n2 opened n5 · <task>"${example}. ${delivery} Lines reach you in two ways: new ones are appended to the output of each cell you run, and nodes.next() returns them when you wait. Each batch ends with the budget left.

How to work. Your task is a what, and your first cell splits it. A judgment is one question with its own evidence: when your task names more than one factor, market, source or scenario, each is a separate judgment. In your first cell, write the judgments as a comment, one per line. If there are two or more, open one child node per judgment with nodes.open in that same cell (children run in parallel with you and with each other), giving each child exactly one judgment stated so that it can be answered on its own, and keep the ops on globalThis. If there is only one, say so in the comment and answer it directly. Once you have children, leave their judgments to them: your own work is whatever no child has, plus integrating their results into yours. The how is never a node: searches, reads and calculations are calls in your cells.
${cond.guided ? '\n' + SHARING + '\n' : ''}
Your result. When you stop calling run_cell, your final message is stored as your result (nK.r1, or the next version if you are reopened) and its first line appears in the streams of other nodes. Refs you write in it are recorded as its links. You cannot finish while a node you hold is still running: wait for its result or close it first.`;
}

export function taskPrompt(node, run, {children = [], index = null} = {}) {
  const parts = [`You are node ${node.id}.`, `Your task: ${node.request.task}`, `Your request: ${JSON.stringify(node.request)}`];
  parts.push(node.opener ? `Opened by: ${node.opener}.` : 'You are the root of this run; your result is the run\'s answer.');
  if (children.length) {
    parts.push(`These nodes were opened for you at the start; you hold them and they are running now:\n${children.map(c => `${c.id}: ${c.request.task}`).join('\n')}`);
  }
  if (index && index.length) parts.push(`Run index when you started:\n${index.join('\n')}`);
  return parts.join('\n\n');
}

export function forkPrompt(node, src) {
  return `This session continues as a copy of node ${src}'s session up to this point. From here on you are a new node, ${node.id}, and the cell sandbox is new (refs still resolve).

Your task: ${node.request.task}
Your request: ${JSON.stringify(node.request)}
Opened by: ${node.opener}.`;
}

export function reopenPrompt(node, version, messages, lines) {
  return `You were reopened. Your next final message becomes ${node.id}.r${version}. Your cell sandbox is new; refs still resolve.

Addressed to you:
${messages.map(m => `${m.ref} from ${m.from}: ${m.content}`).join('\n\n')}
${lines.length ? `\nLines since you finished:\n${lines.join('\n')}` : ''}`;
}

export function finishPrompt(open) {
  return `You still hold nodes that are running: ${open.join(', ')}. Wait for each result (for example await nodes.handle('${open[0]}').result()) or release it (await tools.closeNode({handle: '${open[0]}'})) before writing your final message.`;
}
