"""Branch coverage and mixed execution through the real interpreter and model double."""
import asyncio
import tempfile
import unittest
from pathlib import Path
from quickjs_rs import TimeoutError as JSTimeoutError

from code_runner import CodeRunner
from demo import run_demo
from runtime import Node, NodeRequest, Registry, Rejected, Runtime, Store


class DemoTests(unittest.IsolatedAsyncioTestCase):
    async def test_example_paths_and_audits(self):
        expected={
            'a': {'a','b','c','d','f','g','k','l'},
            'a-no-e': {'a','b','c','d','k','l'},
            'b': {'a','b','h','i','k','l'},
            'b-no-j': {'a','b','h','k','l'},
            'unchanged': {'a','b','h','i'},
        }
        for case, names in expected.items():
            with self.subTest(case=case):
                runtime,receipt=await run_demo(case)
                report=runtime.store.get(receipt['ref'])['content']
                events=runtime.store.events()
                admitted=[x for x in events if x['type']=='admitted']
                actual={x['node'] for x in admitted} & set('abcdefghijkl')
                self.assertEqual(actual,names)
                self.assertEqual(report['outcome'],'complete')
                self.assertEqual(report['omitted_c_audit'],'c' not in names)
                self.assertEqual(len(report['audited']),3 if 'c' in names else 2)
                self.assertEqual(len({x['frame'] for x in admitted}),len(admitted))
                for entry in admitted:
                    if entry['node'] in ('red_team','artifact_coherence'):
                        self.assertTrue(entry['restricted'])
                    if entry['kind']=='code':
                        self.assertFalse(any(x['type']=='agent_actions' and x['frame']==entry['frame'] for x in events))
                thesis=runtime.store.get(report['thesis'])
                self.assertEqual(len(thesis['reviews']),1)
                review=runtime.store.get(thesis['reviews'][0])['content']
                target=runtime.store.get(review['candidate_ref'])
                self.assertEqual(target['content'],thesis['content'])
                self.assertEqual(review['verdict'],'pass')

    async def test_failed_optional_audit_reports_blocked_without_thesis(self):
        for case in ('incoherent','unsupported'):
            with self.subTest(case=case):
                runtime,result=await run_demo(case)
                report=runtime.store.get(result['ref'])['content']
                self.assertEqual(report['outcome'],'blocked')
                self.assertFalse(any(e['type']=='admitted' and e['node']=='thesis' for e in runtime.store.events()))
                assessments=[runtime.store.get(ref)['content'] for ref in report['audits']]
                self.assertTrue(any(x['verdict']=='fail' for x in assessments))

    async def test_code_node_can_compose_other_nodes_with_no_model(self):
        leaf=Node('leaf','# leaf','v1',kind='code',code="""
await tools.submitCandidate({summary:'Leaf',content:{value:input.n},based_on:[]});
""")
        parent=Node('sum','# sum','v1',kind='code',code="""
const parts = await Promise.all([1,2].map(n=>tools.runNode({request:{
 node:'leaf',task:'number',inputs:{n},key:String(n),refs:[]
}})));
const values = await Promise.all(parts.map(p=>tools.readArtifact({ref:p.ref})));
await tools.submitCandidate({summary:'Sum',content:{value:values.reduce((n,v)=>n+JSON.parse(v.text).content.value,0)},based_on:parts.map(p=>p.ref)});
""")
        runtime=Runtime(Registry([leaf,parent]),Store())
        runtime.code_runner=CodeRunner(runtime)
        result=await runtime.run_node(NodeRequest('sum','sum',{},'root'))
        self.assertEqual(runtime.store.get(result['ref'])['content']['value'],3)
        self.assertEqual(runtime.ledger.model_calls,0)
        self.assertEqual(runtime.ledger.frames,3)

    async def test_code_timeout_and_invalid_link_rejection(self):
        node=Node('loop','# loop','v1',kind='code',code='while(true) {}')
        runtime=Runtime(Registry([node]),Store())
        runtime.code_runner=CodeRunner(runtime,timeout=0.02)
        with self.assertRaises(JSTimeoutError):
            await asyncio.wait_for(runtime.run_node(NodeRequest('loop','loop',{},'root')),2)
        self.assertFalse(any(e['type']=='accepted' for e in runtime.store.events()))
        with self.assertRaisesRegex(Rejected,'Broken link'):
            Registry([Node('bad','# bad','v1',links=('missing',))])

    def test_code_revision_and_schema_validation(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'skills'/'calc'/'SKILL.md';p.parent.mkdir(parents=True)
            p.write_text('---\nlibrary:\n  kind: code\n---\n# Calc\n```node-js\n1+1\n```\n')
            first=Registry.load(Path(d)).snapshot
            p.write_text(p.read_text().replace('1+1','1+2'))
            self.assertNotEqual(Registry.load(Path(d)).snapshot,first)
            p.write_text(p.read_text().replace('```node-js','```js'))
            with self.assertRaisesRegex(Rejected,'exactly one'):
                Registry.load(Path(d))


if __name__=='__main__':
    unittest.main()
