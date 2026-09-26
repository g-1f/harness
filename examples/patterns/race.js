// Application helper, not an installed primitive. Request keys remain explicit.
async function raceNodes(requests) {
  if (requests.length === 0) throw new Error('A race needs at least one request');
  const acquired = await Promise.allSettled(requests.map(request => nodes.open(request)));
  const operations = acquired.filter(item => item.status === 'fulfilled').map(item => item.value);
  let failure;
  try {
    const errors = acquired.filter(item => item.status === 'rejected').map(item => item.reason);
    if (errors.length) throw new AggregateError(errors, 'Race admission failed');
    // Promise.any attaches rejection handlers to every participant, including losers.
    return await Promise.any(operations.map(operation => operation.result()));
  } catch (error) {
    failure = error;
    throw error;
  } finally {
    const closed = await Promise.allSettled(operations.map(operation => operation.close()));
    const errors = closed.filter(item => item.status === 'rejected').map(item => item.reason);
    if (errors.length) {
      throw new AggregateError(failure ? [failure, ...errors] : errors, 'Race cleanup failed');
    }
  }
}
