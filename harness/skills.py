"""Load prose packages. Links and revisions are derived, never YAML policy."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType

import yaml

from harness.contracts import Rejected, digest

NAME = re.compile(r"[a-z0-9_-]+(?:/[a-z0-9_-]+)*\Z")
FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)


class _UniqueKeysLoader(yaml.SafeLoader):
    """Reject duplicate keys instead of silently accepting the last value."""


def _mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str) or key in result:
            raise Rejected("Frontmatter keys must be unique strings")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_UniqueKeysLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


@dataclass(frozen=True, slots=True)
class Resource:
    path: str
    data: bytes

    def __post_init__(self):
        path = Path(self.path)
        if (
            path.is_absolute()
            or ".." in path.parts
            or path.as_posix() != self.path
            or not self.path
            or self.path == "."
            or self.path == "SKILL.md"
            or not isinstance(self.data, bytes)
        ):
            raise Rejected("Resource needs immutable bytes and a relative package path")
        if len(self.data) > 1_000_000:
            raise Rejected("Resource exceeds the 1 MB package-file limit")


@dataclass(frozen=True, slots=True)
class Skill:
    name: str
    description: str
    instructions: str
    resources: tuple[Resource, ...] = ()
    links: tuple[str, ...] = field(init=False)
    revision: str = field(init=False)

    def __post_init__(self):
        if not isinstance(self.name, str) or not NAME.fullmatch(self.name):
            raise Rejected("Invalid canonical skill name")
        if not isinstance(self.description, str) or not self.description.strip():
            raise Rejected("Skill description must be a nonempty string")
        if not isinstance(self.instructions, str) or not self.instructions.strip():
            raise Rejected("Skill instructions must be nonempty prose")
        if len((self.instructions + self.description).encode()) > 24_000:
            raise Rejected("Split skills exceeding the 24 KB entry size budget")
        if not isinstance(self.resources, tuple) or any(
            not isinstance(r, Resource) for r in self.resources
        ):
            raise Rejected("Resources must be an immutable tuple of Resource values")
        if len({r.path for r in self.resources}) != len(self.resources):
            raise Rejected("Duplicate resource path")
        # Wikilinks in prose refer to canonical IDs; code examples do not add edges.
        prose = re.sub(r"^(`{3,}|~{3,}).*?^\1\s*$", "", self.instructions, flags=re.M | re.S)
        links = tuple(
            dict.fromkeys(
                x.split("|", 1)[0].split("#", 1)[0].strip()
                for x in re.findall(r"\[\[([^\]]+)\]\]", prose)
            )
        )
        object.__setattr__(self, "links", links)
        object.__setattr__(
            self,
            "revision",
            digest(
                {
                    "name": self.name,
                    "description": self.description,
                    "instructions": self.instructions,
                    "resources": {
                        r.path: hashlib.sha256(r.data).hexdigest() for r in self.resources
                    },
                }
            ),
        )

    def resource(self, path: str) -> bytes:
        for resource in self.resources:
            if resource.path == path:
                return resource.data
        raise Rejected(f"Missing resource: {self.name}/{path}")


class Registry:
    def __init__(self, skills: Iterable[Skill]):
        items = list(skills)
        nodes = {s.name: s for s in items}
        if len(nodes) != len(items):
            raise Rejected("Duplicate skill name")
        for skill in items:
            for linked in skill.links:
                if linked not in nodes:
                    raise Rejected(f"Broken link: {skill.name} -> {linked}")
        self.nodes = MappingProxyType(nodes)
        self.snapshot = digest({s.name: s.revision for s in items})

    @classmethod
    def load(cls, skills_dir: Path) -> Registry:
        """This repo's local convention requires exactly name and description."""
        root = skills_dir.resolve()
        paths = sorted(root.rglob("SKILL.md"))
        if not paths:
            raise Rejected(f"No skills found in {skills_dir}")
        packages = {p.parent for p in paths}
        skills = []
        for path in paths:
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                raise Rejected("Skill must stay inside the skills directory")
            text = path.read_text(encoding="utf-8")
            match = FRONTMATTER.match(text)
            if not match:
                raise Rejected(f"{path}: expected name and description frontmatter")
            try:
                meta = yaml.load(match[1], Loader=_UniqueKeysLoader)
            except yaml.YAMLError as error:
                raise Rejected(f"{path}: invalid YAML") from error
            if not isinstance(meta, dict) or set(meta) != {"name", "description"}:
                raise Rejected(f"{path}: frontmatter permits only name and description")
            name = path.parent.relative_to(root).as_posix()
            if meta["name"] != name:
                raise Rejected(f"{path}: name must match canonical package path {name}")
            resources = []
            for item in sorted(path.parent.rglob("*")):
                # A nested skill owns its files independently of the parent package.
                if any(
                    p in packages and p != path.parent
                    for p in item.parents
                    if p.is_relative_to(path.parent)
                ):
                    continue
                if item.is_symlink():
                    raise Rejected("Resources cannot be symlinks")
                if item.is_file() and item != path:
                    if not item.resolve().is_relative_to(path.parent.resolve()):
                        raise Rejected("Resource must stay inside its skill package")
                    resources.append(
                        Resource(item.relative_to(path.parent).as_posix(), item.read_bytes())
                    )
            skills.append(Skill(name, meta["description"], text[match.end() :], tuple(resources)))
        return cls(skills)
