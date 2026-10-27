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

def parse_strict(raw):
    """Refuse duplicate keys and non-finite pseudo-JSON, including nested rows."""
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON object key: " + key)
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError("non-finite JSON number: " + value)

    return json.loads(raw, object_pairs_hook=unique_pairs, parse_constant=invalid_constant)

def audit(data):
    if not isinstance(data, dict):
        raise ValueError("grammar must be a JSON object")
    actual = [key for key in data if re.fullmatch(r":\d{3}", key)]
    if actual != list(INDEX):
        raise ValueError("grammar index missing, reordered or extended")
    names = [data[key] for key in INDEX]
    if any(not isinstance(name, str) or not name.strip() for name in names):
        raise ValueError("empty or non-string production identity")
    if len(set(names)) != 211:
        raise ValueError("duplicate production identity")
    if set(data) != set(INDEX) | set(names):
        raise ValueError("production definitions missing or orphaned")
    for name in names:
        definition = data[name]
        if not isinstance(definition, (str, dict, list)):
            raise ValueError("invalid production definition type")
        if not definition or (isinstance(definition, str) and not definition.strip()):
            raise ValueError("empty production definition")
    return {"index_count": 211, "definition_count": 211}

class GrammarContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = SOURCE.read_bytes()
        cls.fixture = parse_strict(cls.raw)

    def test_exact_211_productions_and_complete_definitions(self):
        self.assertEqual(audit(self.fixture), {"index_count": 211, "definition_count": 211})

    def test_source_digest_report_is_byte_bound_not_acceptance(self):
        digest = hashlib.sha256(self.raw).hexdigest()
        self.assertRegex(digest, r"^[0-9a-f]{64}$")
        self.assertEqual(parse_strict(self.raw)[":211"], "l-yaml-stream")

    def test_duplicate_json_key_rejected_even_when_last_value_matches(self):
        with self.assertRaisesRegex(ValueError, "duplicate JSON object key"):
            parse_strict(b'{"a": 1, "a": 1}')
        with self.assertRaisesRegex(ValueError, "duplicate JSON object key"):
            parse_strict(b'{"outer": {"rule": 1, "rule": 2}}')

    def test_nonfinite_extension_rejected(self):
        for value in (b'{"value": NaN}', b'{"value": Infinity}', b'{"value": -Infinity}'):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "non-finite JSON"):
                    parse_strict(value)

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

    def test_non_object_root_rejected(self):
        with self.assertRaisesRegex(ValueError, "JSON object"):
            audit([])

    def test_whitespace_production_name_rejected(self):
        data = deepcopy(self.fixture)
        data[":001"] = "   "
        with self.assertRaisesRegex(ValueError, "identity"):
            audit(data)

    def test_whitespace_only_definition_rejected(self):
        for value in (" ", "\t", "\r\n", "\u00a0"):
            with self.subTest(value=repr(value)):
                data = deepcopy(self.fixture)
                data[data[":001"]] = value
                with self.assertRaisesRegex(ValueError, "empty production definition"):
                    audit(data)

    def test_literal_backslash_t_is_not_whitespace(self):
        data = deepcopy(self.fixture)
        data[data[":001"]] = r"\t"
        self.assertEqual(audit(data), {"index_count": 211, "definition_count": 211})

    def test_empty_container_definitions_rejected(self):
        for value in ({}, []):
            with self.subTest(type=type(value).__name__):
                data = deepcopy(self.fixture)
                data[data[":001"]] = value
                with self.assertRaisesRegex(ValueError, "empty production definition"):
                    audit(data)

    def test_nonstring_production_name_rejected(self):
        data = deepcopy(self.fixture)
        data[":003"] = 123
        with self.assertRaisesRegex(ValueError, "identity"):
            audit(data)

    def test_malformed_index_injection_rejected(self):
        data = deepcopy(self.fixture)
        data[":1"] = data[":001"]
        with self.assertRaisesRegex(ValueError, "orphaned"):
            audit(data)

if __name__ == "__main__":
    unittest.main()
