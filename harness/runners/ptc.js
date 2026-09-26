// Host Rejected values become catchable JS errors. Native Python calls still raise.
// Only the response envelope is inspected; artifact content stays opaque.
for (const [name, method] of Object.entries(tools)) {
  if (typeof method !== 'function' || method.__harness_checked__) continue;
  const checked = async args => {
    const result = await method(args);
    if (result && typeof result.__harness_rejection__ === 'string') {
      const error = new Error(result.__harness_rejection__);
      error.name = 'Rejected';
      throw error;
    }
    return result;
  };
  checked.__harness_checked__ = true;
  tools[name] = checked;
}

// Installed by the harness before each eval; existing operation objects survive cells.
if (typeof globalThis.nodes === 'undefined') {
  async function open(request) {
    const opened = await tools.openNode({request});
    if (!opened || typeof opened.handle !== 'string') {
      throw new Error('Host did not return a node handle');
    }
    let cursor = 0;
    let closed = false;
    let busy = false;
    let terminal = null;
    async function close() {
      if (closed) return;
      const response = await tools.closeNode({handle: opened.handle});
      if (!response || response.closed !== true) throw new Error('Host did not close the node');
      closed = true;
    }
    async function advance() {
      if (terminal) return null;
      if (closed) throw new Error('Node observation is closed');
      const event = await tools.nextNodeEvent({handle: opened.handle, after: cursor});
      if (!event || !event.receipt || typeof event.receipt.ref !== 'string' ||
          event.receipt.status !== 'published') {
        throw new Error('Invalid node event');
      }
      if (event.kind === 'complete' && event.cursor === cursor) {
        terminal = {...event.receipt};
        closed = true; // The host releases on terminal delivery.
        return null;
      }
      if (event.kind !== 'checkpoint' || event.cursor !== cursor + 1) {
        throw new Error('Invalid checkpoint event or cursor');
      }
      cursor = event.cursor;
      return {...event.receipt};
    }
    async function reading(action) {
      if (busy) throw new Error('A read is already pending on this observation');
      busy = true;
      try { return await action(); }
      finally { busy = false; }
    }
    return Object.freeze({
      next: () => reading(advance),
      result: () => reading(async () => {
        while (!terminal) await advance();
        return {...terminal};
      }),
      async *checkpoints() {
        for (;;) {
          const checkpoint = await reading(advance);
          if (checkpoint === null) return;
          yield checkpoint;
        }
      },
      close,
    });
  }
  globalThis.nodes = Object.freeze({
    run: request => tools.runNode({request}),
    open,
    async with(request, use) {
      if (typeof use !== 'function') throw new TypeError('Expected a node scope callback');
      const operation = await open(request);
      let failed = false;
      let failure;
      try { return await use(operation); }
      catch (error) { failed = true; failure = error; throw error; }
      finally {
        try { await operation.close(); }
        catch (cleanup) {
          if (failed) throw new AggregateError([failure, cleanup], 'Node scope and cleanup failed');
          throw cleanup;
        }
      }
    },
  });
}
