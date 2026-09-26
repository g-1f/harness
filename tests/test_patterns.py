"""Execute the documented application race helper through real QuickJS."""

import asyncio
import unittest
from pathlib import Path

from tests import test_ptc

RACE = (Path(__file__).resolve().parents[1] / "examples/patterns/race.js").read_text()


# Reuse the fixture helpers without inheriting and rerunning the wrapper test suite.
class PatternTests(unittest.IsolatedAsyncioTestCase):
    runtime = test_ptc.PTCWrapperTests.runtime
    run_root = test_ptc.PTCWrapperTests.run_root

    async def test_race_winner_releases_loser(self):
        both_started = asyncio.Event()
        count = 0
        cancelled = []

        async def producer(frame, context):
            nonlocal count
            count += 1
            if count == 2:
                both_started.set()
            await both_started.wait()
            if frame.request.inputs["winner"]:
                return {"summary": "Winner", "content": {}, "based_on": []}
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.append(frame.id)

        source = (
            RACE
            + """
const receipt = await raceNodes([false,true].map(winner => ({
  node:'b',task:'race',inputs:{winner},refs:[],key:String(winner),reuse:'fresh'
})));
await tools.submitCandidate({summary:'Done',content:{},based_on:[receipt.ref]});
"""
        )
        runtime = self.runtime(source, producer)
        await self.run_root(runtime)
        self.assertEqual(len(cancelled), 1)

    async def test_race_partial_admission_and_all_producer_failures_release_every_handle(self):
        for nodes in (("b", "missing"), ("b", "b")):
            with self.subTest(nodes=nodes):

                async def producer(frame, context):
                    raise ValueError("producer failed")

                source = (
                    RACE
                    + """
let failed = false;
try {
  await raceNodes(NODES.map((node,index) => ({node,task:'race',inputs:{},refs:[],key:String(index)})));
} catch (error) { failed = true; }
if (!failed) throw new Error('Expected failure');
await tools.submitCandidate({summary:'Handled',content:{},based_on:[]});
""".replace("NODES", str(list(nodes)))
                )
                await self.run_root(self.runtime(source, producer))
