#!/usr/bin/env node
/**
 * JADE focus: offline, zero-dependency YAML 1.2 grammar JSON audit.
 * Does not regenerate upstream grammar or call network/modify source files.
 */
import { readFileSync, lstatSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
export const SOURCE = resolve(ROOT, 'yaml-spec-1.2.json');

export function auditGrammar(text) {
  const source = JSON.parse(text);
  if (source === null || Array.isArray(source) || typeof source !== 'object')
    throw Error('INVALID_GRAMMAR_MAPPING');
  const keys = Object.keys(source);
  if (keys.length !== 422) throw Error('GRAMMAR_KEY_COUNT_DRIFT');
  const symbols = new Set();
  for (let ordinal = 1; ordinal <= 211; ordinal += 1) {
    const index = (ordinal - 1) * 2;
    const expected = ':' + String(ordinal).padStart(3, '0');
    const name = keys[index + 1];
    if (keys[index] !== expected) throw Error('GRAMMAR_ORDINAL_DRIFT');
    if (typeof source[expected] !== 'string' || source[expected] !== name)
      throw Error('GRAMMAR_SYMBOL_CROSSWALK_DRIFT');
    if (!name || name.startsWith(':') || symbols.has(name))
      throw Error('GRAMMAR_DUPLICATE_SYMBOL');
    symbols.add(name);
    if (source[name] === null || source[name] === undefined)
      throw Error('GRAMMAR_RULE_BODY_MISSING');
  }
  if (source[':001'] !== 'c-printable' || source[':211'] !== 'l-yaml-stream')
    throw Error('GRAMMAR_SENTINEL_DRIFT');
  return {
    schema: 'jade.grammar.offline-audit.v1',
    authority: 'LOCAL_SOURCE_OBSERVATION_ONLY',
    grammar_rules: 211,
    map_keys: keys.length,
    sha256: createHash('sha256').update(text).digest('hex'),
    native_ci: null,
    point_release: 'HOLD',
  };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const target = process.argv[2] ? resolve(process.argv[2]) : SOURCE;
  if (target !== SOURCE || lstatSync(target).isSymbolicLink())
    throw Error('EXACT_SOURCE_PATH_REQUIRED');
  console.log(JSON.stringify(auditGrammar(readFileSync(target, 'utf8')), null, 2));
}
