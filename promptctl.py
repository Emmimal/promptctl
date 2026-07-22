#!/usr/bin/env python3
"""promptctl - static contract validation for prompt templates.

Zero external dependencies. Standard library only (ast, string,
pathlib, argparse, time, json). Treats prompt templates the way
Terraform treats infrastructure manifests: something to validate
before it's applied.

Commands
--------
promptctl diff              Pass 1 - what changed?
promptctl validate          Pass 2 - will existing callers still work?
promptctl impact <symbol>   Pass 3 - who breaks if I merge this?
promptctl check             Runs all three in sequence (convenience alias,
                             no new functionality). Exits 1 on any
                             contract violation, 0 otherwise.

Every command accepts --repo and --baseline to point at a different
mock repo / snapshot (e.g. mock_repo_after_fix), so you can compare a
broken state against a fixed one without editing files by hand.
"""

import argparse
import sys
import time
from pathlib import Path

import contracts
import impact
import promptdiff

DEFAULT_REPO = str(Path(__file__).parent / "mock_repo")
DEFAULT_BASELINE = str(Path(__file__).parent / "baseline.json")


def cmd_diff(repo: str, baseline: str) -> int:
    changes = promptdiff.run(repo, baseline)
    print(promptdiff.render(changes))
    return 0


def cmd_validate(repo: str) -> int:
    violations = contracts.run(repo)
    print(contracts.render(violations))
    return 1 if violations else 0


def cmd_impact(repo: str, symbol_id: str) -> int:
    affected = impact.run(repo, symbol_id)
    print(impact.render(symbol_id, affected))
    return 0


def _print_section(title: str, body: str) -> None:
    print(title)
    print("-" * len(title))
    print()
    print(body)
    print()


def cmd_check(repo: str, baseline: str) -> int:
    start = time.perf_counter()

    changes = promptdiff.run(repo, baseline)
    violations = contracts.run(repo)

    affected_symbols = sorted({v.symbol_id for v in violations} or {c.symbol_id for c in changes})
    all_affected: set = set()
    impact_bodies = []
    for symbol_id in affected_symbols:
        affected = impact.run(repo, symbol_id)
        all_affected |= set(affected)
        impact_bodies.append(impact.render(symbol_id, affected))

    elapsed = time.perf_counter() - start

    print("promptctl check")
    print("=" * 31)
    print()
    print("Repository")
    print()
    print(f"Prompts scanned:   {len(contracts.get_current_contracts(repo))}")
    print(f"Python files:      {len(list(Path(repo).glob('**/*.py')))}")
    print(f"Scan time:         {elapsed:.3f} s")
    print()
    print("Comparing")
    print()
    print(f"Baseline: {Path(baseline).name}")
    print(f"Current : {Path(repo).name}/")
    print()

    _print_section("PromptDiff", promptdiff.render(changes))
    _print_section("Contract Validation", contracts.render(violations))

    if impact_bodies:
        _print_section("Impact Analysis", "\n\n".join(impact_bodies))
    else:
        _print_section("Impact Analysis", "No prompt changes to check.")

    breaking_count = sum(1 for c in changes if c.is_breaking)
    violation_count = len(violations)
    affected_count = len(all_affected)

    print("=" * 40)
    print()
    if violations:
        exit_code = 1
        print("CHECK FAILED")
        print()
        print(f"Breaking Changes        {breaking_count}")
        print(f"Contract Violations     {violation_count}")
        print(f"Affected Modules        {affected_count}")
        print()
        print(f"Exit Code               {exit_code}")
        print()
        print("Merge blocked.")
        print()
        print("=" * 40)
        return exit_code
    else:
        exit_code = 0
        print("CHECK PASSED")
        print()
        print(f"Breaking Changes        {breaking_count}")
        print(f"Contract Violations     {violation_count}")
        print()
        print(f"Exit Code               {exit_code}")
        print()
        print("Repository is safe.")
        print()
        print("=" * 40)
        return exit_code


def main() -> int:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--repo", default=DEFAULT_REPO, help="Path to the target repo (default: mock_repo)")
    common.add_argument("--baseline", default=DEFAULT_BASELINE, help="Path to the baseline snapshot (default: baseline.json)")

    parser = argparse.ArgumentParser(prog="promptctl", parents=[common])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("diff", parents=[common], help="Show variable-level changes vs the baseline")
    sub.add_parser("validate", parents=[common], help="Check current callers against current prompt contracts")

    impact_parser = sub.add_parser("impact", parents=[common], help="List downstream consumers of a prompt symbol")
    impact_parser.add_argument("symbol", help="Prompt symbol id, e.g. customer_router")

    sub.add_parser("check", parents=[common], help="Run diff, validate, and impact together")

    args = parser.parse_args()

    if args.command == "diff":
        return cmd_diff(args.repo, args.baseline)
    if args.command == "validate":
        return cmd_validate(args.repo)
    if args.command == "impact":
        return cmd_impact(args.repo, args.symbol)
    if args.command == "check":
        return cmd_check(args.repo, args.baseline)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
