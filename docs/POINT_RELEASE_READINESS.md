# JADE H04/H05 offline grammar qualification candidate

This owner-local, dependency-free lane verifies the existing 211 YAML 1.2
grammar productions and their definitions on each relevant pull request and
master push. It tests loss, duplicates, index order, orphan definitions, and
source digest reporting. It does not fetch dependencies or publish content.

## Run

python -m unittest discover -s tests -p 'test_*.py' -v

The workflow runs against the exact PR head with read-only permissions.
A successful fixture test proves committed JSON population, not semantic
YAML parser conformance, reproducible source scraping, deployment,
branch protection, or an authorized release.

## Non-compensating JADE blockers

- H04: fully pinned offline reproducible generation remains unverified;
  existing Makefile uses an origin/node_modules worktree and lynx.
- H05: source smoke does not establish a complete native B0/parser suite.
- H07/H08/H09: security scan, effective protection, rejected RED canary
  and eligible independent review require separate receipts.
- H11/H12: Pages, release packaging, hosted parity, runtime and rollback
  are not accepted by this source-integrity PR.

merge_admission=HOLD; point_release_credit=0; no waiver.
