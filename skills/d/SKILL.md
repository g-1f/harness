---
name: d
description: Demo d node
library:
  kind: code
---
# d

Return this bound synthetic observation. A code node performs the transformation directly.

```node-js
const evidence = input.observations['d'];
if (typeof evidence !== 'string') throw new Error('Missing observation');
await tools.submitCandidate({summary: 'Observation d', content: {
  text: evidence, unit: input.units?.['d'] || 'USD', source: 'synthetic/d'
}, based_on: refs});
```
