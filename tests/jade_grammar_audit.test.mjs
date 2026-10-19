import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { SOURCE, auditGrammar } from '../bin/jade-grammar-audit.mjs';

const source = readFileSync(SOURCE, 'utf8');
const data = JSON.parse(source);

test('211 ordinals and symbols exact local source census', () => {
  const result = auditGrammar(source);
  assert.equal(result.grammar_rules, 211);
  assert.equal(result.map_keys, 422);
  assert.match(result.sha256, /^[0-9a-f]{64}$/);
  assert.equal(result.point_release, 'HOLD');
  assert.equal(result.native_ci, null);
});

test('missing production is a fail-closed census change', () => {
  const invalid = { ...data };
  delete invalid[':002'];
  assert.throws(() => auditGrammar(JSON.stringify(invalid)), /KEY_COUNT_DRIFT/);
});

test('ordinal/symbol misassociation fails closed', () => {
  const invalid = { ...data, ':002': 'c-printable' };
  assert.throws(() => auditGrammar(JSON.stringify(invalid)), /CROSSWALK_DRIFT/);
});

test('rule body deletion cannot pass census', () => {
  const invalid = { ...data, 'c-printable': null };
  assert.throws(() => auditGrammar(JSON.stringify(invalid)), /RULE_BODY_MISSING/);
});

test('unexpected insertion never counts as progress', () => {
  const invalid = { ...data, 'invented-rule': { value: true } };
  assert.throws(() => auditGrammar(JSON.stringify(invalid)), /KEY_COUNT_DRIFT/);
});

test('synthetic alternative order fails closed', () => {
  const keys = Object.keys(data);
  const reordered = {};
  reordered[keys[1]] = data[keys[1]];
  reordered[keys[0]] = data[keys[0]];
  for (const k of keys.slice(2)) reordered[k] = data[k];
  assert.throws(() => auditGrammar(JSON.stringify(reordered)), /ORDINAL_DRIFT/);
});

test('empty and non-object source rejected', () => {
  for (const invalid of ['{}', 'null', '[]']) {
    assert.throws(() => auditGrammar(invalid), /INVALID_GRAMMAR_MAPPING|KEY_COUNT_DRIFT/);
  }
});
