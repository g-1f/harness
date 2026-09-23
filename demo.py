"""Choose --model provider:model for runtime PTC generation, or --offline for fixtures."""

import argparse
import asyncio
import json
from collections import Counter
from pathlib import Path

from examples.application import build_runtime, prompt_for
from examples.fixtures import CASES, fixture
from harness import NodeRequest, Store


async def run_demo(case="a", *, model=None, offline=False, store: Store | None = None):
    runtime = build_runtime(model=model, offline=offline, store=store)
    try:
        result = await runtime.run_node(
            NodeRequest("root", prompt_for(case), fixture(case), "root")
        )
        return runtime, result
    finally:
        await runtime.aclose()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=CASES, default="a")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--model", help="Real model writes PTC at runtime; requires provider credentials"
    )
    mode.add_argument(
        "--offline", action="store_true", help="Use prewritten fixture PTC; no LLM code generation"
    )
    parser.add_argument("--trace", type=Path, help="Optional JSON trace path")
    return parser.parse_args(argv)


def main():
    args = parse_args()
    runtime, result = asyncio.run(run_demo(args.case, model=args.model, offline=args.offline))
    events = runtime.store.events()
    report = {
        "execution_mode": "offline-scripted-fixture" if args.offline else "live-model",
        "ptc_origin": "prewritten test fragments" if args.offline else "model-generated at runtime",
        "case": args.case,
        "status": result["status"],
        "result": runtime.store.get(result["ref"])["content"],
        "nodes": [e["node"] for e in events if e["type"] == "admitted"],
        "model_calls": runtime.ledger.model_calls,
        "calls": runtime.ledger.calls,
        "executions": runtime.ledger.frames,
        "dispatch_counts": dict(
            Counter(e["disposition"] for e in events if e["type"] == "call_acquired")
        ),
    }
    if args.trace:
        args.trace.parent.mkdir(parents=True, exist_ok=True)
        args.trace.write_text(json.dumps({"report": report, "events": events}, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    runtime.store.close()


if __name__ == "__main__":
    main()
