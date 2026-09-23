---
name: l
description: Demo l node
library:
  kind: code
---
# l

Return this bound synthetic observation. A code node performs the transformation directly.

```node-js
const evidence = input.observations['l'];
if (typeof evidence !== 'string') throw new Error('Missing observation');
await tools.submitCandidate({summary: 'Observation l', content: {
  text: evidence, unit: input.units?.['l'] || 'USD', source: 'synthetic/l'
}, based_on: refs});
```
