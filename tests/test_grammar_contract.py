"""Offline YAML 1.2 grammar fixture integrity, without network or node_modules.

This is a source-population smoke test, not complete YAML parser conformance.
"""
from __future__ import annotations
import hashlib
import json
import re
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "yaml-spec-1.2.json"
INDEX = tuple(f":{n:03d}" for n in range(1, 212))

def audit(data):
    if not isinstance(data, dict):
        raise ValueError("grammar must be a JSON object")
    actual = [key for key in data if re.fullmatch(r":\d{3}", key)]
    if actual != list(INDEX):
        raise ValueError("grammar index missing, reordered or extended")
    names = [data[key] for key in INDEX]
    if any(not isinstance(name, str) or not name for name in names):
        raise ValueError("empty or non-string production identity")
    if len(set(names)) != 211:
        raise ValueError("duplicate production identity")
    if set(data) != set(INDEX) | set(names):
        raise ValueError("production definitions missing or orphaned")
    if any(data[name] is None or data[name] == "" for name in names):
        raise ValueError("empty production definition")
    return {"index_count": 211, "definition_count": 211}

class GrammarContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = SOURCE.read_bytes()
        cls.fixture = json.loads(cls.raw)

    def test_exact_211_productions_and_complete_definitions(self):
        self.assertEqual(audit(self.fixture), {"index_count": 211, "definition_count": 211})

    def test_source_digest_report_is_byte_bound_not_acceptance(self):
        digest = hashlib.sha256(self.raw).hexdigest()
        self.assertRegex(digest, r"^[0-9a-f]{64}$")
        self.assertEqual(json.loads(self.raw)[":211"], "l-yaml-stream")

    def test_deleted_production_rejected(self):
        data = deepcopy(self.fixture)
        del data[":211"]
        with self.assertRaisesRegex(ValueError, "index"):
            audit(data)

    def test_missing_definition_rejected(self):
        data = deepcopy(self.fixture)
        del data[data[":001"]]
        with self.assertRaisesRegex(ValueError, "definitions"):
            audit(data)

    def test_duplicate_production_identity_rejected(self):
        data = deepcopy(self.fixture)
        data[":211"] = data[":001"]
        with self.assertRaisesRegex(ValueError, "duplicate"):
            audit(data)

    def test_injected_orphan_definition_rejected(self):
        data = deepcopy(self.fixture)
        data["unauthorized-extra-rule"] = "epsilon"
        with self.assertRaisesRegex(ValueError, "orphaned"):
            audit(data)

    def test_reordered_index_rejected(self):
        data = {key: value for key, value in self.fixture.items() if key not in (":001", ":002")}
        data = {":002": self.fixture[":002"], ":001": self.fixture[":001"], **data}
        with self.assertRaisesRegex(ValueError, "reordered"):
            audit(data)

if __name__ == "__main__":
    unittest.main()
