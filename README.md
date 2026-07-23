# promptctl

A pure-Python static contract validator for prompt templates — three passes, zero dependencies, catches breaking variable changes before they reach production.

![Python Version](https://img.shields.io/badge/python-3.9%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green)

Most prompt engineering advice stops at getting the prompt right the first time. Nothing checks what happens the fifth time someone changes it. `promptctl` treats a prompt template the way Terraform treats an infrastructure manifest — something to validate before it's applied, not just a string.

Read the full write-up on Towards Data Science → [Prompt Engineering Is Solved. Prompt Management Isn't—I Built the Missing Layer](https://towardsdatascience.com/author/emmimalp-alexander/)

## The Problem

```python
# Someone renames a variable to match a schema change
CUSTOMER_ROUTER_PROMPT = "Categorize support request for {ticket_id} in domain {domain}."
```

```python
# A caller elsewhere in the codebase was never updated
CUSTOMER_ROUTER_PROMPT.format(ticket=user_ticket, domain=user_domain)
```

Git diffs it as a one-line change. Tests pass, because they mock the LLM client and never call `.format()` on real input. Code review has nothing to flag. The deployment goes out clean — and crashes on the first real request with `KeyError: 'ticket_id'`.

## What It Does

```
Prompt Change → PromptDiff → Contract Validation → Impact Analysis → PASS / FAIL
```

Three passes, one exit code:

| Component | Job |
|---|---|
| `PromptDiff` | Detects variable-level changes against a baseline snapshot |
| `Contract Validation` | Checks every `.format()` call site against the prompt's current contract |
| `Impact Analysis` | Maps every file that references a given prompt symbol |

`promptctl check` runs all three and exits `1` if anything is broken, `0` if it isn't — wire that straight into a pre-commit hook or CI step and it becomes a merge gate.

## Installation

```
git clone https://github.com/Emmimal/promptctl.git
cd promptctl
python3 promptctl.py check
```

No dependencies to install. Standard library only — `ast`, `string`, `pathlib`, `argparse`, `time`, `json`. No `pip install`, no API keys, no network calls, no LLM anywhere in the validation path.

## Quick Start

```
# Run all three passes together
python3 promptctl.py check

# Or run one pass at a time
python3 promptctl.py diff
python3 promptctl.py validate
python3 promptctl.py impact customer_router

# Point at any repo / baseline pair
python3 promptctl.py check --repo mock_repo_after_fix --baseline baseline_after_fix.json
```

Example output against the included (intentionally broken) mock repo:

```
$ promptctl.py check
promptctl check
===============================

Repository

Prompts scanned:   1
Python files:      4
Scan time:         0.003 s

Comparing

Baseline: baseline.json
Current : mock_repo/

PromptDiff
----------

Prompt: customer_router

Contract Diff

Removed: {ticket}
Added:   {ticket_id}

Breaking Change: YES

Contract Validation
-------------------

Prompt: customer_router

Required Variables

{domain}
{ticket_id}

Call Site Variables

{domain}
{ticket}

Missing

{ticket_id}

Affected Call Sites

✗ evaluator.py:8
✗ router.py:8

2 contract violations

Impact Analysis
---------------

Prompt:
customer_router

Affected Modules

• evaluator.py
• router.py
• tests/test_router.py

Total: 3 modules

========================================

CHECK FAILED

Breaking Changes        1
Contract Violations     2
Affected Modules        3

Exit Code               1

Merge blocked.

========================================
```

## The Included Demo

Two mock repos ship with the project so the failing and passing cases are both reproducible, not just described:

| Path | State |
|---|---|
| `mock_repo/` + `baseline.json` | The broken state — prompt renamed, callers not updated |
| `mock_repo_after_fix/` + `baseline_after_fix.json` | The fixed state — callers updated, baseline advanced to the new accepted contract |

Running `check` against the second pair returns `CHECK PASSED` with a `0` exit code, using the same real code path, not a separate success-only demo.

## How Prompt Symbols Are Registered

Any top-level string constant in `prompts.py` ending in `_PROMPT` is automatically treated as a registered prompt. Its symbol id is the constant name lowercased with the `_PROMPT` suffix dropped — `CUSTOMER_ROUTER_PROMPT` becomes `customer_router`. No decorator or registry file required.

The baseline snapshot is a small JSON file recording a prompt's last accepted state:

```json
{
  "CUSTOMER_ROUTER_PROMPT": {
    "symbol_id": "customer_router",
    "variables": ["ticket", "domain"]
  }
}
```

## CLI Reference

```
promptctl diff              [--repo PATH] [--baseline PATH]
promptctl validate          [--repo PATH] [--baseline PATH]
promptctl impact <symbol>   [--repo PATH] [--baseline PATH]
promptctl check             [--repo PATH] [--baseline PATH]
```

| Flag | Default | Purpose |
|---|---|---|
| `--repo` | `mock_repo/` | Target directory to scan |
| `--baseline` | `baseline.json` | Snapshot representing the last accepted prompt state |

## Project Structure

```
promptctl/
├── promptctl.py             # CLI entry point
├── promptdiff.py             # Pass 1 — PromptDiff
├── contracts.py                # Pass 2 — Contract Validation
├── impact.py                     # Pass 3 — Impact Analysis
├── baseline.json                  # "Before" snapshot
├── baseline_after_fix.json         # "After" snapshot (merged state)
├── mock_repo/                       # Demo repo with the intentional breaking change
│   ├── prompts.py
│   ├── router.py
│   ├── evaluator.py
│   └── tests/
│       └── test_router.py
├── mock_repo_after_fix/               # Same repo, call sites fixed
│   ├── prompts.py
│   ├── router.py
│   ├── evaluator.py
│   └── tests/
│       └── test_router.py
└── README.md
```

## Performance (single prompt, 4-file mock repo)

| Operation | Internal scan time | What dominates |
|---|---|---|
| PromptDiff | ~1 ms | Parsing one file's AST |
| Contract Validation | ~1 ms | Walking 3 caller files |
| Impact Analysis | ~1 ms | Name-reference scan across 3 files |
| Full `check` (all three) | ~3 ms | Sum of the above |
| `check`, full process incl. Python startup | ~50–90 ms | Python interpreter startup, not the tool |

Every pass is a linear walk over the file tree, so this stays cheap as a repository grows — nothing here scales with the number of prompts the way a per-prompt model call would.

## When to Use This

Worth adopting when you ship prompt templates as code and more than one place in the codebase calls `.format()` / `.render()` on the same template. Two or more callers means a rename anywhere becomes a coordination problem most toolchains don't catch.

Skip it when:
- Every prompt has exactly one caller — a contract break there is a normal bug, not a coordination failure
- Prompts live in a database or CMS rather than local Python source — static analysis over a file tree can't see them
- You're looking for something to judge prompt *quality* — this checks contracts, not writing

## Known Limitations

- **Dynamically composed prompt keys** (e.g. `registry.get(f"prompt_{role}")`) aren't visible to a static parser — there's no fixed string to resolve.
- **Templates stored outside local Python source** (a database, CMS, or remote config service) are outside what this tool can reach.
- **Semantic quality or correctness of the generated text is out of scope.** This checks whether required variables are present, not whether the resulting prompt is good.
- **The `_PROMPT` naming convention is a simple rule, not a general registry** — a prompt without that suffix is invisible to the tool.
- **Baseline snapshots don't advance automatically.** Updating `baseline.json` after a merge is currently a manual step.

## License

MIT
