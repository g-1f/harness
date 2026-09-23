state.auditTargets = [
  state.a,
  state.b,
  ...state.artifacts.filter(item => item.name === 'c').map(item => item.receipt)
];
state.audits = await Promise.all([
  ...state.auditTargets.map(target => run('artifact_coherence', [target.ref], 'Audit this artifact')),
  run('artifact_coherence', state.auditTargets.map(target => target.ref), 'Audit joint coherence'),
  run('red_team', [state.a.ref], 'Challenge candidate ' + state.a.ref)
]);
const auditBodies = await Promise.all(state.audits.map(audit => read(audit.ref)));
observe('audits', auditBodies);
