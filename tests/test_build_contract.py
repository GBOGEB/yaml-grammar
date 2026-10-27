"""H04 build contract: the CI validation path needs nothing beyond CPython.

Checks, all derived from files in this checkout (no network):

* every Python module under bin/ and tests/ imports only the standard library
  (``sys.stdlib_module_names``) or sibling modules;
* the upstream regeneration tools in bin/ (Perl and CoffeeScript) declare
  exactly the third-party modules listed in docs/BUILD_CONTRACT.md -- they are
  NOT on the CI path, and a new or removed dependency fails here;
* every ``uses:`` in .github/workflows/ is pinned to a full 40-hex commit SHA;
* the stated Python floor (docs/BUILD_CONTRACT.md) matches this interpreter
  and the lowest Python version any workflow tests on.
"""
from __future__ import annotations

import ast
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_DOC = ROOT / "docs" / "BUILD_CONTRACT.md"
WORKFLOWS = ROOT / ".github" / "workflows"
PYTHON_FLOOR = (3, 11)

# Upstream regeneration toolchain (Makefile targets build/comments). Not used
# by CI; enumerated so that drift is visible. Pragmas strict/warnings excluded.
REGEN_TOOLCHAIN = {
    "bin/yaml-grammar-html-to-yaml": {"perl:XXX", "perl:YAML::PP"},
    "bin/yaml-grammar-to-comments": {"perl:IO::All", "perl:XXX", "perl:YAML::PP"},
    "bin/yaml-grammar-yaml-to-json": {"node:ingy-prelude", "node:yaml"},
}
PERL_PRAGMAS = {"strict", "warnings", "utf8", "lib", "constant", "vars"}

SHA_PIN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+@[0-9a-f]{40}$")
DOCKER_DIGEST = re.compile(r"^docker://[^@\s]+@sha256:[0-9a-f]{64}$")
USES = re.compile(r"^\s*(?:-\s+)?uses:\s*['\"]?([^'\"#\s]+)['\"]?", re.M)


def python_sources() -> list[Path]:
    found = []
    for base in (ROOT / "bin", ROOT / "tests"):
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix == ".py":
                found.append(path)
                continue
            first = path.read_bytes()[:128].split(b"\n", 1)[0]
            if first.startswith(b"#!") and b"python" in first:
                found.append(path)
    return found


def non_stdlib_imports(source: str, local: set[str]) -> set[str]:
    """Top-level absolute imports that are neither stdlib nor local modules."""
    allowed = set(sys.stdlib_module_names) | {"__future__"} | local
    bad = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names = [node.module]
        else:
            continue
        for name in names:
            top = name.split(".", 1)[0]
            if top not in allowed:
                bad.add(top)
    return bad


def script_dependencies(text: str) -> set[str]:
    deps = set()
    for mod in re.findall(r"^\s*use\s+([A-Za-z_][\w:]*)", text, re.M):
        if mod not in PERL_PRAGMAS:
            deps.add("perl:" + mod)
    for mod in re.findall(r"\brequire\s*\(?\s*[\"']([^\"']+)[\"']", text):
        if not mod.startswith((".", "/")):
            deps.add("node:" + mod)
    return deps


def unpinned_uses(workflow_text: str) -> list[str]:
    bad = []
    for ref in USES.findall(workflow_text):
        if ref.startswith("./"):
            continue
        if ref.startswith("docker://"):
            if not DOCKER_DIGEST.match(ref):
                bad.append(ref)
        elif not SHA_PIN.match(ref):
            bad.append(ref)
    return bad


def matrix_python_versions(workflow_text: str) -> list[tuple[int, int]]:
    versions = []
    for value in re.findall(r"python-version:\s*(.+)", workflow_text):
        for major, minor in re.findall(r"[\"']?(\d+)\.(\d+)[\"']?", value):
            versions.append((int(major), int(minor)))
    return versions


def stated_floor(doc_text: str) -> tuple[int, int]:
    match = re.search(r"Python floor:\s*`?>=\s*(\d+)\.(\d+)`?", doc_text)
    if not match:
        raise ValueError("docs/BUILD_CONTRACT.md does not state 'Python floor: >= X.Y'")
    return int(match.group(1)), int(match.group(2))


def workflow_files() -> list[Path]:
    return sorted([*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml")])


class BuildContractTests(unittest.TestCase):
    def test_python_sources_are_stdlib_only(self):
        sources = python_sources()
        self.assertGreater(len(sources), 0, "no Python sources found; scan is vacuous")
        local = {p.stem for p in sources}
        for path in sources:
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertEqual(non_stdlib_imports(path.read_text("utf-8"), local), set())

    def test_regeneration_toolchain_matches_declared_contract(self):
        actual = {}
        for path in sorted((ROOT / "bin").iterdir()):
            if path.is_file() and path not in python_sources():
                deps = script_dependencies(path.read_text("utf-8"))
                if deps:
                    actual[str(path.relative_to(ROOT))] = deps
        self.assertEqual(actual, REGEN_TOOLCHAIN)
        doc = CONTRACT_DOC.read_text("utf-8")
        for deps in REGEN_TOOLCHAIN.values():
            for dep in deps:
                self.assertIn("`" + dep.split(":", 1)[1] + "`", doc)

    def test_every_workflow_action_is_sha_pinned(self):
        files = workflow_files()
        self.assertGreater(len(files), 0, "no workflows found; pin check is vacuous")
        total = 0
        for path in files:
            text = path.read_text("utf-8")
            total += len(USES.findall(text))
            with self.subTest(workflow=path.name):
                self.assertEqual(unpinned_uses(text), [])
        self.assertGreater(total, 0, "no 'uses:' references found; pin check is vacuous")

    def test_python_floor_is_stated_and_honoured(self):
        floor = stated_floor(CONTRACT_DOC.read_text("utf-8"))
        self.assertEqual(floor, PYTHON_FLOOR)
        self.assertGreaterEqual(sys.version_info[:2], floor)
        versions = [v for p in workflow_files() for v in matrix_python_versions(p.read_text("utf-8"))]
        self.assertTrue(versions, "no workflow declares a python-version")
        self.assertEqual(min(versions), floor, "CI must test the stated floor itself")

    # Negative controls: each guard must reject a synthetic violation.

    def test_third_party_import_is_detected(self):
        src = "import json\nimport yaml\nfrom requests.adapters import HTTPAdapter\nfrom . import x\n"
        self.assertEqual(non_stdlib_imports(src, set()), {"yaml", "requests"})

    def test_undeclared_script_dependency_is_detected(self):
        text = "use strict;\nuse YAML::PP;\nuse JSON::XS;\nx = require('lodash')\nrequire('./local')\n"
        self.assertEqual(script_dependencies(text), {"perl:YAML::PP", "perl:JSON::XS", "node:lodash"})

    def test_tag_or_branch_pinned_action_is_rejected(self):
        text = (
            "steps:\n"
            "  - uses: actions/checkout@v4\n"
            "  - uses: actions/setup-python@main\n"
            "  - uses: actions/cache@0123456789abcdef0123456789abcdef01234567 # ok\n"
            "  - uses: ./local-action\n"
            "  - uses: docker://alpine:3.20\n"
        )
        self.assertEqual(
            unpinned_uses(text),
            ["actions/checkout@v4", "actions/setup-python@main", "docker://alpine:3.20"],
        )

    def test_missing_floor_statement_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Python floor"):
            stated_floor("Requires a recent Python.")
        self.assertEqual(stated_floor("Python floor: `>= 3.11`"), (3, 11))


if __name__ == "__main__":
    unittest.main()
