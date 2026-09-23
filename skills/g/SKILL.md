---
name: g
description: Demo g node
library:
  kind: code
---
# g

Return this bound synthetic observation. A code node performs the transformation directly.

```node-js
const evidence = input.observations['g'];
if (typeof evidence !== 'string') throw new Error('Missing observation');
await tools.submitCandidate({summary: 'Observation g', content: {
  text: evidence, unit: input.units?.['g'] || 'USD', source: 'synthetic/g'
}, based_on: refs});
```
