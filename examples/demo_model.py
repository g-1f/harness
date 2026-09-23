"""An observation-driven model double, not domain logic in the runtime.

This makes the integration reproducible without credentials. It inspects actual
PTC tool observations and chooses a subsequent fragment. Replace the factory with
a live chat model to test semantic decisions; these fixture rules prove mechanics.
"""
import json
import re
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult


def action(code):
    return AIMessage(content="", tool_calls=[{"name": "eval", "args": {"code": code}, "id": "step"}])


HELPERS = """
async function read(ref) {
  let text = '', offset = 0;
  do {
    const slice = await tools.readArtifact({ref, offset, limit:16000});
    text += slice.text; offset = slice.next_offset;
    if (offset >= slice.total_chars) return JSON.parse(text).content;
    if (text.length > 64000) throw new Error('Demo evidence too large');
  } while (true);
}
async function run(node, refs=[], task='Execute the node procedure', extra={}) {
  const result = await tools.runNode({request:{node, task, inputs:input,
    refs, key:node + ':' + (++sequence), ...extra}});
  if (result.status !== 'accepted') throw new Error(node + ': ' + result.status);
  return result;
}
function observe(stage, value) {
  console.log('OBS:' + JSON.stringify({stage, value}));
}
var sequence = 0;
"""

AUDIT = """
state.auditTargets = [state.a, state.b, ...state.artifacts.filter(x => x.name==='c').map(x=>x.receipt)];
state.audits = await Promise.all([
  ...state.auditTargets.map(x => run('artifact_coherence', [x.ref], 'Audit this artifact')),
  run('artifact_coherence', state.auditTargets.map(x=>x.ref), 'Audit joint coherence'),
  run('red_team', [state.a.ref], 'Challenge candidate ' + state.a.ref)
]);
const auditBodies = await Promise.all(state.audits.map(x=>read(x.ref)));
observe('audits', auditBodies);
"""


class DemoModel(BaseChatModel):
    node: str
    request_inputs: dict[str, Any]
    refs: list[str]

    @property
    def _llm_type(self):
        return "node-demo-model-double"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        tool_messages = [m for m in messages if m.type == "tool"]
        if not tool_messages:
            code = 'var input = ' + json.dumps(self.request_inputs) + ';\n' + HELPERS
            code += 'var suppliedRefs = ' + json.dumps(self.refs) + ';\n'
            value = action(code + self.first())
        else:
            output = str(tool_messages[-1].content)
            match = re.search(r'OBS:(\{[^\n]+\})', output)
            if match:
                observation = json.loads(match[1])
                value = action(self.next(observation["stage"], observation["value"]))
            elif 'Error' in output or 'error' in output:
                raise RuntimeError('Demo PTC failed: ' + output[:1000])
            else:
                value = AIMessage(content="Candidate staged")
        return ChatResult(generations=[ChatGeneration(message=value)])

    def first(self):
        if self.node == 'root':
            return """
var rootPrivate = 'not inherited by reviewers';
const linked = await tools.readNode({node:'root'});
const [a,b] = await Promise.all([run('a'),run('b')]);
var state = {a,b,artifacts:[{name:'a',receipt:a},{name:'b',receipt:b}],decisions:[]};
observe('b', await read(b.ref));
"""
        if self.node == 'b':
            return """
var delta = await run('delta_check');
observe('delta', await read(delta.ref));
"""
        if self.node in ('red_team','artifact_coherence'):
            return """
if (typeof rootPrivate !== 'undefined') throw new Error('Inherited parent globals');
var targets = await Promise.all(suppliedRefs.map(read));
observe('review', targets);
"""
        if self.node == 'thesis':
            return """
var sources = await Promise.all(suppliedRefs.map(read));
observe('synthesis', sources);
"""
        raise RuntimeError('No demo agent for ' + self.node)

    def next(self, stage, value):
        if self.node == 'b' and stage == 'delta':
            if value['delta'] == 0:
                return """
await tools.submitCandidate({summary:'No snapshot change; b returns early',content:{
  text:input.observations.b,unit:'USD',changed:false,internal:[]
},based_on:[delta.ref]});
"""
            return """
const parts = await Promise.all([run('k',[delta.ref]),run('l',[delta.ref])]);
await tools.submitCandidate({summary:'B investigated changed snapshot',content:{
  text:input.observations.b,unit:'USD',changed:true,internal:['k','l']
},based_on:[delta.ref,...parts.map(x=>x.ref)]});
"""
        if self.node == 'root' and stage == 'b':
            scenario_a = 'accelerating' in value['text'].lower()
            nodes = ['c','d'] if scenario_a else ['h']
            return """
const branch = NODES;
state.decisions.push({after:'b',run:branch,reason:REASON});
const branchResults = await Promise.all(branch.map(n=>run(n,[state.b.ref])));
state.artifacts.push(...branchResults.map((receipt,i)=>({name:branch[i],receipt})));
observe('investigation', {node:branch[branch.length-1], body:await read(branchResults[branchResults.length-1].ref)});
""".replace('NODES',json.dumps(nodes)).replace('REASON',json.dumps(value['text']))
        if self.node == 'root' and stage == 'investigation':
            narrative = value['body']['text'].lower()
            if value['node']=='d':
                extra = ['f','g'] if 'concentrated supplier' in narrative else []
            else:
                extra = ['i'] if 'pending regulatory change' in narrative else []
            return """
const extra = EXTRA;
state.decisions.push({after:AFTER,run:extra,reason:REASON});
const source = state.artifacts[state.artifacts.length-1].receipt.ref;
const investigations = await Promise.all(extra.map(n=>run(n,[source])));
state.artifacts.push(...investigations.map((receipt,i)=>({name:extra[i],receipt})));
""".replace('EXTRA',json.dumps(extra)).replace('AFTER',json.dumps(value['node'])).replace('REASON',json.dumps(narrative)) + AUDIT
        if self.node == 'root' and stage == 'audits':
            if any(x.get('verdict')!='pass' for x in value):
                return """
await tools.submitCandidate({summary:'Investigation blocked by failed audit',content:{
 outcome:'blocked',executed:state.artifacts.map(x=>x.name),decisions:state.decisions,
 audits:state.audits.map(x=>x.ref),limitations:['No thesis produced after failed audit']
},based_on:[...state.artifacts.map(x=>x.receipt.ref),...state.audits.map(x=>x.ref)]});
"""
            return """
const thesis = await run('thesis',[...state.artifacts.map(x=>x.receipt.ref),...state.audits.map(x=>x.ref)]);
await tools.submitCandidate({summary:'Completed investigated and reviewed thesis',content:{
 outcome:'complete',thesis:thesis.ref,executed:state.artifacts.map(x=>x.name),
 decisions:state.decisions,audited:state.auditTargets.map(x=>x.ref),
 omitted_c_audit:!state.artifacts.some(x=>x.name==='c')
},based_on:[thesis.ref,...state.artifacts.map(x=>x.receipt.ref),...state.audits.map(x=>x.ref)]});
"""
        if stage=='review' and self.node=='red_team':
            target=value[0]
            invalid='UNSUPPORTED' in target.get('text','')
            findings=['Unsupported assertion in candidate'] if invalid else []
            assessment={'candidate_ref':self.refs[0],'verdict':'fail' if invalid else 'pass','findings':findings}
            return "await tools.submitCandidate({summary:'Red-team assessment',content:"+json.dumps(assessment)+",based_on:[]});"
        if stage=='review' and self.node=='artifact_coherence':
            units={x.get('unit') for x in value if x.get('unit')}
            findings=[]
            if len(units)>1: findings.append('Conflicting currency units across target artifacts')
            if any('INCONSISTENT' in x.get('text','') for x in value): findings.append('Internal inconsistency')
            assessment={'targets':self.refs,'verdict':'fail' if findings else 'pass','findings':findings,'coverage':len(value)}
            return "await tools.submitCandidate({summary:'Coherence assessment',content:"+json.dumps(assessment)+",based_on:suppliedRefs});"
        if self.node=='thesis' and stage=='synthesis':
            texts=[x['text'] for x in value if 'text' in x]
            content={'text':'Synthetic thesis: '+' '.join(texts),'evidence_count':len(texts),'limitations':['Synthetic observations; not an investment recommendation']}
            return "await tools.submitCandidate({summary:'Synthetic thesis candidate',content:"+json.dumps(content)+",based_on:suppliedRefs});"
        raise RuntimeError(f'Unexpected observation {self.node}/{stage}')
