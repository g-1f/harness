// Offline fixture helpers. Live agents write their own PTC from skill prose.
async function read(ref) {
  let text = '';
  let offset = 0;
  do {
    const slice = await tools.readArtifact({ref, offset, limit: 16000});
    text += slice.text;
    offset = slice.next_offset;
    if (offset >= slice.total_chars) return JSON.parse(text).content;
    if (text.length > 64000) throw new Error('Demo evidence too large');
  } while (true);
}

async function run(node, refs = [], task = 'Interpret the supplied evidence', reuse = 'fresh', inputs = input) {
  const receipt = await tools.runNode({request: {
    node, task, inputs, refs, reuse, key: node + ':' + (++sequence)
  }});
  if (receipt.status !== 'accepted') throw new Error(node + ': ' + receipt.status);
  return receipt;
}

function sharedInputs() {
  return {
    current: input.current, previous: input.previous,
    observations: input.observations, units: input.units
  };
}

// These exact neutral tasks also appear in each producer's prose. Consumer
// interpretation stays in a/c/d/f/g; it is not smuggled into shared work identity.
var sharedTasks = {
  b: 'Produce snapshot evidence',
  delta_check: 'Compute snapshot difference',
  k: 'Report volume evidence',
  l: 'Report mix evidence',
  f: 'Assess supplier alternatives'
};
async function share(node, refs = []) {
  return run(node, refs, sharedTasks[node], 'session', sharedInputs());
}
async function openShared(node, refs = []) {
  return tools.openNode({request: {
    node, task: sharedTasks[node], inputs: sharedInputs(), refs,
    reuse: 'session', key: node + ':' + (++sequence)
  }});
}
async function nextCheckpoint(handle, after = 0) {
  const event = await tools.nextNodeEvent({handle, after});
  if (event.kind !== 'checkpoint' || event.receipt.status !== 'accepted') {
    throw new Error('Expected an accepted checkpoint');
  }
  return event;
}
async function complete(handle, after) {
  let event = await tools.nextNodeEvent({handle, after});
  while (event.kind === 'checkpoint') {
    event = await tools.nextNodeEvent({handle, after: event.cursor});
  }
  if (event.kind !== 'complete' || event.receipt.status !== 'accepted') {
    throw new Error('Node did not complete with an accepted result');
  }
  return event.receipt;
}

function evidence(node, extra = {}) {
  const text = input.observations[node];
  if (typeof text !== 'string') throw new Error('Missing observation for ' + node);
  return {text, unit: input.units?.[node] || 'USD', source: 'synthetic/' + node,
    scope: assignedTask, ...extra};
}
function observe(stage, value) {
  console.log('OBS:' + JSON.stringify({stage, value}));
}
var sequence = 0;
