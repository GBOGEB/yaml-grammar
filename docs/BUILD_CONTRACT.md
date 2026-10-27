# Build contract (JADE H04)

Python floor: `>= 3.11`

## What the CI validation path needs

The grammar checks in `tests/` run on CPython alone. There is nothing to
install: no `pip install`, no `requirements*.txt`, no lockfile, no network
access after checkout. `tests/test_build_contract.py` enforces this:

- every Python file under `bin/` and `tests/` imports only modules in
  `sys.stdlib_module_names` (or sibling test modules);
- the workflow `.github/workflows/build-contract.yml` additionally runs the
  whole suite with `python -I -S`, which removes site-packages from
  `sys.path`, so an undeclared third-party import fails at run time too;
- every `uses:` in `.github/workflows/` is pinned to a 40-hex commit SHA
  (`docker://` references must be pinned by `sha256` digest);
- this file states the Python floor, and CI must test that exact version
  (the lowest `python-version` across workflows must equal the floor).

## Upstream regeneration toolchain (not on the CI path)

The upstream generators in `bin/` are Perl and CoffeeScript, not Python.
They are only needed to regenerate the committed grammar files with the
`Makefile` targets, and they have third-party dependencies:

| Script | Dependencies |
| --- | --- |
| `bin/yaml-grammar-html-to-yaml` | Perl `YAML::PP`, `XXX` (plus `lynx` to fetch the spec) |
| `bin/yaml-grammar-to-comments` | Perl `IO::All`, `YAML::PP`, `XXX` |
| `bin/yaml-grammar-yaml-to-json` | Node `yaml`, `ingy-prelude` (run by `coffee`) |

The test fails if this set changes (a dependency added or removed) without
updating the test and this table. The Makefile `node_modules` target still
creates a worktree from an `origin/node_modules` branch that this fork does
not have, so `make build` is not reproducible offline here. That is
upstream behaviour and is left unchanged on purpose; this contract does not
cover it.

## What this does not prove

It does not prove that the committed JSON/YAML match a fresh scrape of the
spec, that the Perl/Node generators run, or anything about YAML parser
conformance.
