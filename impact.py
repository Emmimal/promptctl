"""Pass 3 - Impact Analysis.

Answers one question: who breaks if I merge this?

Walks every .py file in the mock repo looking for references to a
given prompt constant name, so a developer can see every downstream
consumer before merging a prompt change.
"""

import ast
from pathlib import Path
from typing import List


def _constant_name_for_symbol(symbol_id: str) -> str:
    return f"{symbol_id.upper()}_PROMPT"


def run(mock_repo_path: str, symbol_id: str) -> List[str]:
    root = Path(mock_repo_path)
    constant_name = _constant_name_for_symbol(symbol_id)
    affected: List[str] = []

    for py_file in root.glob("**/*.py"):
        if py_file.name == "prompts.py":
            continue
        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError):
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == constant_name:
                affected.append(str(py_file.relative_to(root)).replace("\\", "/"))
                break

    return sorted(set(affected))


def render(symbol_id: str, affected: List[str]) -> str:
    lines = ["Prompt:", symbol_id, "", "Affected Modules", ""]
    for path in affected:
        lines.append(f"\u2022 {path}")
    lines.append("")
    lines.append(f"Total: {len(affected)} module{'s' if len(affected) != 1 else ''}")
    return "\n".join(lines)
