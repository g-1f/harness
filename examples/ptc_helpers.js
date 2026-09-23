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
  const inputs = {
    current: input.current, previous: input.previous,
    observations: input.observations, units: input.units
  };
  return run(node, refs, sharedTasks[node], 'session', inputs);
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
