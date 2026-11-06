// Node prompts: mechanics only. Nothing here says when to join, cite, post, wait, or message.

const LINES = {
  tree: `You receive lines about nodes you opened or joined, and lines addressed to you. You do not see any other node's lines, and there is no run index.`,
  broadcast: `You receive every line from every other node in the run: starts, joins, reuses, checkpoints, results, closes, cancellations, failures and reopens.`,
  scoped: `You receive lines about nodes you opened or joined, and lines addressed to you. readArtifact({ref: 'run'}) returns the run index on request: one line per node with its task, state and latest ref.`,
  index: `You receive lines about nodes you opened or joined, and lines addressed to you. After every cell you also receive the run index: one line per node with its task, state and latest ref, with * marking nodes that changed since your previous cell. readArtifact({ref: 'run'}) returns the same index.`,
};

export function systemPrompt(cond) {
  return `You are one node in a research run. Many nodes work at the same time, each on one task. Your node id and task are in the first message.

You act only by calling the run_cell tool with JavaScript. The code runs as the body of an async function in your own sandbox, so use await and return a value to see it. Values you assign to globalThis persist between cells; local variables do not. A cell can run many calls, in parallel with Promise.all.

Available in every cell:

world.search(query) returns {docs: [{id, title, snippet}], series: [{series, desc}]}.
world.doc(id) returns {id, title, body}.
world.series(name) returns {name, unit, desc, points}.
Each world call takes a few seconds.

tools.openNode({request}) returns {node, disp}. A request is {task, inputs?, refs?, from?, key?}; only task is required. It starts a new node with that task (disp 'started'). If a node with an identical request exists, it joins that node while it runs (disp 'joined') or returns its latest result if it has finished (disp 'reused', with ref and line). A failed or cancelled node is never joined. from is a node id: the new node starts from a copy of that node's session so far. key is any string; a different key makes an otherwise identical request a separate node. Opening or joining a node makes you one of its holders.
tools.nextNodeEvent({}) waits until at least one new line is in your stream, then returns {lines, left} with every pending line.
tools.closeNode({handle}) takes a node id and releases your hold on it. A node that is still running is cancelled when its last holder releases it.
tools.publishCheckpoint({content, to?}) publishes content (text) as your next checkpoint and returns {ref}. Its first line appears in other nodes' streams. Refs written in the content, like n3.r1, are recorded as its links. to is a node id: the checkpoint is addressed to that node, and if that node has finished, it is reopened by it and you hold it until its next result.
tools.readArtifact({ref, offset?, limit?}) returns {text, total_chars, next_offset}, a slice of any ref in this run: nK.cJ (a checkpoint), nK.rV (a result), nK (a node record with its exact request, opener, state and holders) or nK.trail (a node's cells and their outputs).

Shortcuts: nodes.open(request) opens a node and returns an op at once: op.result() waits for its result ({node, ref, line}), op.close() releases it, and await op gives op.node and op.disp. nodes.run(request) opens and waits for the result. nodes.handle(id) returns an op for a node you hold. nodes.next() is tools.nextNodeEvent({}). read(ref) returns a ref's full text, and inspect(ref) parses a node record.

Lines. Every start, join, reuse, checkpoint, result, close, cancellation, failure and reopen in the run is one line, such as "n2 opened n5 · <task>" or "n5.r1 · <first line> · cites n3.c1". ${LINES[cond.delivery]} Lines reach you in two ways: new ones are appended to the output of each cell you run, and nodes.next() returns them when you wait. Each batch ends with the budget left.

How to work. Your task is a what, and your first cell splits it. A judgment is one question with its own evidence: when your task names more than one factor, market, source or scenario, each is a separate judgment. In your first cell, write the judgments as a comment, one per line. If there are two or more, open one child node per judgment with nodes.open in that same cell (children run in parallel with you and with each other), giving each child exactly one judgment stated so that it can be answered on its own, and keep the ops on globalThis. If there is only one, say so in the comment and answer it directly. Once you have children, leave their judgments to them: your own work is whatever no child has, plus integrating their results into yours. The how is never a node: searches, reads and calculations are calls in your cells.

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
