---
name: a
description: Demo a node
library:
  kind: code
---
# a

Return this bound synthetic observation. A code node performs the transformation directly.

```node-js
const evidence = input.observations['a'];
if (typeof evidence !== 'string') throw new Error('Missing observation');
await tools.submitCandidate({summary: 'Observation a', content: {
  text: evidence, unit: input.units?.['a'] || 'USD', source: 'synthetic/a'
}, based_on: refs});
```
