"""Synthetic inputs, deliberately separate from the runtime."""
from copy import deepcopy

BASE = {
    "current": 105, "previous": 100, "units": {},
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
CASES = ("a", "a-no-e", "b", "b-no-j", "unchanged", "incoherent", "unsupported")


def fixture(case):
    if case not in CASES:
        raise ValueError(case)
    data = deepcopy(BASE)
    if case in ("b", "b-no-j", "unchanged"):
        data["observations"]["b"] = "Demand is stable; investigate the policy outlook."
    if case == "unchanged":
        data["current"] = data["previous"]
    if case == "a-no-e":
        data["observations"]["d"] = "Suppliers are diversified; no concentration concern."
    if case == "b-no-j":
        data["observations"]["h"] = "No regulatory proposal is pending."
    if case == "incoherent":
        data["units"]["c"] = "JPY"
    if case == "unsupported":
        data["observations"]["a"] = "UNSUPPORTED claim in the supplied evidence."
    return data
