"""Host-owned publication rules, separate from authored skills and executors."""

from collections.abc import Mapping
from dataclasses import dataclass

from harness.contracts import Rejected
from harness.skills import Registry


@dataclass(frozen=True, slots=True)
class ReviewPolicy:
    reviewers: tuple[str, ...]
    max_revisions: int = 0

    def __post_init__(self):
        if (
            not isinstance(self.reviewers, tuple)
            or not self.reviewers
            or any(not isinstance(name, str) or not name for name in self.reviewers)
            or len(set(self.reviewers)) != len(self.reviewers)
            or type(self.max_revisions) is not int
            or self.max_revisions < 0
        ):
            raise Rejected("Review policy needs unique reviewers and a nonnegative revision bound")


def validate_policies(registry: Registry, policies: Mapping[str, ReviewPolicy]) -> None:
    for name, policy in policies.items():
        if name not in registry.nodes or not isinstance(policy, ReviewPolicy):
            raise Rejected("Review policies must name registered skills")
        if any(reviewer not in registry.nodes for reviewer in policy.reviewers):
            raise Rejected("Unknown required reviewer")

    def visit(name: str, active: set[str], done: set[str]) -> None:
        if name in active:
            raise Rejected("Required-review cycle")
        if name in done or name not in policies:
            return
        active.add(name)
        for reviewer in policies[name].reviewers:
            visit(reviewer, active, done)
        active.remove(name)
        done.add(name)

    done: set[str] = set()
    for name in policies:
        visit(name, set(), done)
