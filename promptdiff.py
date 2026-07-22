"""Pass 1 - PromptDiff.

Answers one question: what changed?

Parses the current prompt module with ast (never executes it),
extracts the format() variables from every top-level *_PROMPT string
constant, and diffs them against a stored baseline snapshot.
"""

import ast
import string
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set


@dataclass
class PromptChange:
    constant_name: str
    symbol_id: str
    added_vars: Set[str] = field(default_factory=set)
    removed_vars: Set[str] = field(default_factory=set)
    current_vars: Set[str] = field(default_factory=set)

    @property
    def is_breaking(self) -> bool:
        # Removing or renaming a variable is breaking; adding a new
        # optional-looking variable on its own is not, since existing
        # callers that don't supply it will still satisfy the rest of
        # the contract as long as nothing they DO supply disappeared.
        return len(self.removed_vars) > 0


def _extract_prompt_vars(source: str) -> Dict[str, Set[str]]:
    """Return {constant_name: {var, ...}} for every top-level *_PROMPT
    string constant in the given source, using AST only (no exec)."""
    tree = ast.parse(source)
    found: Dict[str, Set[str]] = {}

    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not (isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)):
            continue

        for target in node.targets:
            if isinstance(target, ast.Name) and target.id.endswith("_PROMPT"):
                template = node.value.value
                variables = {
                    name for _, name, _, _ in string.Formatter().parse(template) if name
                }
                found[target.id] = variables

    return found


def run(mock_repo_path: str, baseline_path: str) -> List[PromptChange]:
    prompts_file = Path(mock_repo_path) / "prompts.py"
    source = prompts_file.read_text(encoding="utf-8")
    current = _extract_prompt_vars(source)

    import json
    baseline: Dict[str, dict] = json.loads(Path(baseline_path).read_text(encoding="utf-8"))

    changes: List[PromptChange] = []
    for constant_name, current_vars in current.items():
        baseline_entry = baseline.get(constant_name)
        if baseline_entry is None:
            continue  # new prompt, nothing to diff against

        baseline_vars = set(baseline_entry["variables"])
        added = current_vars - baseline_vars
        removed = baseline_vars - current_vars

        if added or removed:
            changes.append(
                PromptChange(
                    constant_name=constant_name,
                    symbol_id=baseline_entry["symbol_id"],
                    added_vars=added,
                    removed_vars=removed,
                    current_vars=current_vars,
                )
            )

    return changes


def render(changes: List[PromptChange]) -> str:
    if not changes:
        return "No breaking variable changes."

    lines = []
    for change in changes:
        lines.append(f"Prompt: {change.symbol_id}")
        lines.append("")
        lines.append("Contract Diff")
        lines.append("")
        if change.removed_vars:
            lines.append(f"Removed: {', '.join('{' + v + '}' for v in sorted(change.removed_vars))}")
        if change.added_vars:
            lines.append(f"Added:   {', '.join('{' + v + '}' for v in sorted(change.added_vars))}")
        lines.append("")
        lines.append(f"Breaking Change: {'YES' if change.is_breaking else 'NO'}")
        lines.append("")

    return "\n".join(lines).rstrip()
