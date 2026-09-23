---
name: i
description: Demo i node
library:
  kind: code
---
# i

Return this bound synthetic observation. A code node performs the transformation directly.

```node-js
const evidence = input.observations['i'];
if (typeof evidence !== 'string') throw new Error('Missing observation');
await tools.submitCandidate({summary: 'Observation i', content: {
  text: evidence, unit: input.units?.['i'] || 'USD', source: 'synthetic/i'
}, based_on: refs});
```
