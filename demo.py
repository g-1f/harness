"""python demo.py --case a; optional --model provider:model for real inference."""
import argparse
import asyncio
import json
from pathlib import Path

from code_runner import CodeRunner
from deepagents_adapter import DeepAgentRunner, metered_model
from examples.demo_model import DemoModel
from examples.fixtures import CASES, fixture
from runtime import NodeRequest, Runtime, Registry, Store


async def run_demo(case='a', *, model=None, store=None):
    runtime = Runtime(Registry.load(Path(__file__).parent), store or Store(), deadline_seconds=240)
    runtime.code_runner = CodeRunner(runtime)

    def model_factory(frame):
        if model:
            from langchain.chat_models import init_chat_model
            base = init_chat_model(model, max_retries=0)
        else:
            base = DemoModel(node=frame.request.node, request_inputs=frame.request.inputs,
                             refs=list(frame.request.refs))
        return metered_model(base, runtime.ledger)

    runtime.agent_runner = DeepAgentRunner(runtime, model_factory, interpreter_timeout=60)
    result = await runtime.run_node(NodeRequest('root','Follow the skill graph and produce a reviewed thesis',fixture(case),'root'))
    return runtime, result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=CASES, default='a')
    parser.add_argument('--model', help='Optional provider:model; requires provider credentials')
    parser.add_argument('--trace', type=Path, help='Optional JSON trace path')
    args = parser.parse_args()
    runtime, result = asyncio.run(run_demo(args.case, model=args.model))
    events = runtime.store.events()
    report = {'case':args.case,'status':result['status'],
              'result':runtime.store.get(result['ref'])['content'],
              'nodes':[e['node'] for e in events if e['type']=='admitted'],
              'model_calls':runtime.ledger.model_calls,'invocations':runtime.ledger.frames}
    if args.trace:
        args.trace.parent.mkdir(parents=True,exist_ok=True)
        args.trace.write_text(json.dumps({'report':report,'events':events},indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
