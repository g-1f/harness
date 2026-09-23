"""Synthetic inputs, deliberately separate from the runtime."""

from copy import deepcopy

BASE = {
    "sequence_baseline": False,
    "baseline_requires_snapshot": True,
    "capacity_requires_snapshot": True,
    "current": 105,
    "previous": 100,
    "units": {},
    "observations": {
        "a": "Source evidence supports the baseline claim.",
        "b": "Demand is accelerating while supply remains constrained.",
        "c": "Capacity additions lag demand.",
        "d": "Concentrated supplier exposure warrants further investigation.",
        "f": "Alternative suppliers require lead time.",
        "g": "Inventory limits near-term exposure.",
        "h": "A pending regulatory change warrants investigation.",
        "i": "The proposed rule takes effect next quarter.",
        "k": "Volume increased in the supplied snapshot.",
        "l": "Mix is stable in the supplied snapshot.",
    },
}
CASES = (
    "a",
    "a-diversified",
    "b",
    "b-no-proposal",
    "unchanged",
    "incoherent",
    "unsupported",
    "deferred",
    "skip-c",
)


def fixture(case):
    if case not in CASES:
        raise ValueError(case)
    data = deepcopy(BASE)
    if case in ("b", "b-no-proposal", "unchanged"):
        data["sequence_baseline"] = True
        data["observations"]["b"] = "Demand is stable; investigate the policy outlook."
    if case == "unchanged":
        data["current"] = data["previous"]
    if case == "a-diversified":
        data["observations"]["d"] = "Suppliers are diversified; no concentration concern."
    if case == "b-no-proposal":
        data["observations"]["h"] = "No regulatory proposal is pending."
    if case == "incoherent":
        data["units"]["c"] = "JPY"
    if case == "unsupported":
        data["observations"]["a"] = "UNSUPPORTED claim in the supplied evidence."
    if case == "deferred":
        data["baseline_requires_snapshot"] = False
    if case == "skip-c":
        data["capacity_requires_snapshot"] = False
    return data
