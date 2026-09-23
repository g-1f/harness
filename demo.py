"""Choose --model provider:model for runtime PTC generation, or --offline for fixtures."""
import argparse
import asyncio
import json
from pathlib import Path

from code_runner import CodeRunner
from deepagents_adapter import DeepAgentRunner, metered_model
from examples.fixtures import CASES, fixture
from runtime import NodeRequest, Runtime, Registry, Store


async def run_demo(case='a', *, model=None, offline=False, store=None):
    if bool(model) == bool(offline):
        raise ValueError('Choose exactly one: model=provider:model or offline=True')
    runtime = Runtime(Registry.load(Path(__file__).parent), store or Store(), deadline_seconds=240)
    runtime.code_runner = CodeRunner(runtime)

    def model_factory(frame):
        if model:
            from langchain.chat_models import init_chat_model
            base = init_chat_model(model, max_retries=0)
        else:
            from examples.scripted_model import ScriptedFixtureModel
            base = ScriptedFixtureModel(node=frame.request.node, request_inputs=frame.request.inputs,
                                        refs=list(frame.request.refs))
        return metered_model(base, runtime.ledger)

    runtime.agent_runner = DeepAgentRunner(runtime, model_factory, interpreter_timeout=60)
    result = await runtime.run_node(NodeRequest('root','Follow the skill graph and produce a reviewed thesis',fixture(case),'root'))
    return runtime, result


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=CASES, default='a')
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--model', help='Real model writes PTC at runtime; requires provider credentials')
    mode.add_argument('--offline', action='store_true', help='Use prewritten fixture PTC; no LLM code generation')
    parser.add_argument('--trace', type=Path, help='Optional JSON trace path')
    return parser.parse_args(argv)


def main():
    args = parse_args()
    runtime, result = asyncio.run(run_demo(args.case, model=args.model, offline=args.offline))
    events = runtime.store.events()
    report = {'execution_mode':'offline-scripted-fixture' if args.offline else 'live-model',
              'ptc_origin':'prewritten test fragments' if args.offline else 'model-generated at runtime',
              'case':args.case,'status':result['status'],
              'result':runtime.store.get(result['ref'])['content'],
              'nodes':[e['node'] for e in events if e['type']=='admitted'],
              'model_calls':runtime.ledger.model_calls,'invocations':runtime.ledger.frames}
    if args.trace:
        args.trace.parent.mkdir(parents=True,exist_ok=True)
        args.trace.write_text(json.dumps({'report':report,'events':events},indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
