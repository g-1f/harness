---
name: f
description: Demo f node
library:
  kind: code
---
# f

Return this bound synthetic observation. A code node performs the transformation directly.

```node-js
const evidence = input.observations['f'];
if (typeof evidence !== 'string') throw new Error('Missing observation');
await tools.submitCandidate({summary: 'Observation f', content: {
  text: evidence, unit: input.units?.['f'] || 'USD', source: 'synthetic/f'
}, based_on: refs});
```
