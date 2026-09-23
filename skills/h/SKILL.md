---
name: h
description: Demo h node
library:
  kind: code
---
# h

Return this bound synthetic observation. A code node performs the transformation directly.

```node-js
const evidence = input.observations['h'];
if (typeof evidence !== 'string') throw new Error('Missing observation');
await tools.submitCandidate({summary: 'Observation h', content: {
  text: evidence, unit: input.units?.['h'] || 'USD', source: 'synthetic/h'
}, based_on: refs});
```
