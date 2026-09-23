---
name: k
description: Demo k node
library:
  kind: code
---
# k

Return this bound synthetic observation. A code node performs the transformation directly.

```node-js
const evidence = input.observations['k'];
if (typeof evidence !== 'string') throw new Error('Missing observation');
await tools.submitCandidate({summary: 'Observation k', content: {
  text: evidence, unit: input.units?.['k'] || 'USD', source: 'synthetic/k'
}, based_on: refs});
```
