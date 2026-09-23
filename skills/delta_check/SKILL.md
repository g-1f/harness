---
name: delta_check
description: Demo delta_check node
library:
  kind: code
---
# delta_check

Compute the change in the two bound numeric snapshots. This node makes no model calls.

```node-js
if (!Number.isFinite(input.current) || !Number.isFinite(input.previous)) {
  throw new Error('Numeric snapshots required');
}
await tools.submitCandidate({summary: 'Computed snapshot delta', content: {
  delta: input.current - input.previous, unit: 'USD',
  source: 'synthetic snapshot pair', text: 'Computed delta observation'
}, based_on: refs});
```
