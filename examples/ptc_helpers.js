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
async function run(node, refs = [], task = 'Inspect evidence for the caller question') {
  const result = await tools.runNode({request: {
    node, task, inputs: input, refs, key: node + ':' + (++sequence)
  }});
  if (result.status !== 'accepted') throw new Error(node + ': ' + result.status);
  return result;
}
function observe(stage, value) {
  console.log('OBS:' + JSON.stringify({stage, value}));
}
var sequence = 0;
