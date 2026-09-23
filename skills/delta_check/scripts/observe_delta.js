if (!Number.isFinite(input.current) || !Number.isFinite(input.previous)) {
  throw new Error('Numeric snapshots required');
}
await tools.submitCandidate({summary: 'Computed snapshot delta', content: {
  delta: input.current - input.previous, unit: 'USD',
  source: 'synthetic snapshot pair', text: 'Computed delta observation'
}, based_on: refs});
