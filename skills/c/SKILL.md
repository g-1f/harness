---
name: c
description: Demo c node
library:
  kind: code
---
# c

Return this bound synthetic observation. A code node performs the transformation directly.

```node-js
const evidence = input.observations['c'];
if (typeof evidence !== 'string') throw new Error('Missing observation');
await tools.submitCandidate({summary: 'Observation c', content: {
  text: evidence, unit: input.units?.['c'] || 'USD', source: 'synthetic/c'
}, based_on: refs});
```
