"""Authored schema, resource identity and extension boundaries."""

import tempfile
import unittest
from dataclasses import fields
from pathlib import Path

from examples.application import ROOT
from harness import Registry, Rejected, Resource, Skill


class SkillTests(unittest.TestCase):
    def test_graph_frontmatter_has_no_execution_configuration(self):
        registry = Registry.load(ROOT / "skills")
        self.assertEqual(registry.nodes["a"].links, ("b",))
        self.assertEqual(registry.nodes["c"].links, ("b", "h"))
        self.assertEqual(registry.nodes["b"].links, ("delta_check", "k", "l"))
        self.assertEqual(registry.nodes["d"].links, ("b", "f", "g"))
        self.assertEqual(registry.nodes["g"].links, ("delta_check", "l", "f"))
        incoming = {
            name: sum(name in node.links for node in registry.nodes.values())
            for name in ("b", "f", "k", "l")
        }
        self.assertTrue(all(count > 1 for count in incoming.values()))
        authored = {f.name for f in fields(Skill) if f.init}
        self.assertEqual(authored, {"name", "description", "instructions", "resources"})
        for node in registry.nodes.values():
            self.assertNotIn("```node-js", node.instructions)
        self.assertEqual([n.name for n in registry.nodes.values() if n.resources], ["delta_check"])

    def test_frontmatter_rejects_unknown_duplicate_missing_and_mismatched_fields(self):
        variants = [
            "name: calc\ndescription: Compute\nlibrary: {kind: code}",
            "name: calc\nname: calc\ndescription: Compute",
            "name: calc",
            "name: other\ndescription: Compute",
            "name: calc\ndescription: [Compute]",
            "name: calc\ndescription: ''",
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "calc" / "SKILL.md"
            path.parent.mkdir()
            for meta in variants:
                with self.subTest(meta=meta):
                    path.write_text(f"---\n{meta}\n---\n# Compute\n")
                    with self.assertRaises(Rejected):
                        Registry.load(Path(directory))

    def test_resource_bytes_are_pinned_and_symlinks_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "calc"
            package.mkdir()
            (package / "SKILL.md").write_text(
                "---\nname: calc\ndescription: Compute\n---\n# Compute\n"
            )
            script = package / "delta.js"
            script.write_text("1+1")
            first = Registry.load(root)
            script.write_text("1+2")
            self.assertNotEqual(Registry.load(root).snapshot, first.snapshot)
            self.assertEqual(first.nodes["calc"].resource("delta.js"), b"1+1")
            script.unlink()
            script.symlink_to(root / "outside.js")
            with self.assertRaisesRegex(Rejected, "symlinks"):
                Registry.load(root)

    def test_nested_package_does_not_become_a_parent_resource(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("group", "group/child"):
                path = root / name / "SKILL.md"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f"---\nname: {name}\ndescription: Test\n---\n# Test\n")
            (root / "group/child/data.txt").write_text("evidence")
            registry = Registry.load(root)
            self.assertEqual(registry.nodes["group"].resources, ())
            self.assertEqual(len(registry.nodes["group/child"].resources), 1)

    def test_prose_edges_are_not_execution_or_code_block_edges(self):
        skill = Skill("a", "Test", "[[b|baseline check]]\n```js\n[[missing]]\n```\n[[b#detail]]")
        registry = Registry([skill, Skill("b", "Test", "[[a]]")])
        self.assertEqual(registry.nodes["a"].links, ("b",))
        # Cyclic authored links are legal; active invocation cycles are bounded separately.
        with self.assertRaisesRegex(Rejected, "Broken link"):
            Registry([skill])

    def test_invalid_resource_paths(self):
        for path in ("../outside.js", "/absolute.js", "SKILL.md", "a/../b.js"):
            with self.subTest(path=path), self.assertRaises(Rejected):
                Resource(path, b"source")
