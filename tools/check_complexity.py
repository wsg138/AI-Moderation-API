from __future__ import annotations

import ast
from pathlib import Path

MAX_CCN = 8
MAX_LINES = 50
ROOTS = (Path("service"), Path("tests"), Path("tools/dataset_qa"), Path("workers/w23"))


class ComplexityVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.value = 1

    def visit_If(self, node: ast.If) -> None:
        self.value += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self.value += 1
        self.generic_visit(node)

    visit_AsyncFor = visit_For

    def visit_While(self, node: ast.While) -> None:
        self.value += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self.value += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        self.value += max(0, len(node.values) - 1)
        self.generic_visit(node)

    def visit_comprehension(self, node: ast.comprehension) -> None:
        self.value += 1 + len(node.ifs)
        self.generic_visit(node)


def function_complexity(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    visitor = ComplexityVisitor()
    for statement in node.body:
        visitor.visit(statement)
    return visitor.value


def analyze(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    failures: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        lines = (node.end_lineno or node.lineno) - node.lineno + 1
        complexity = function_complexity(node)
        if lines > MAX_LINES:
            failures.append(f"{path}:{node.lineno} {node.name} has {lines} lines (max {MAX_LINES})")
        if complexity > MAX_CCN:
            failures.append(f"{path}:{node.lineno} {node.name} CCN {complexity} (max {MAX_CCN})")
    return failures


def main() -> int:
    failures: list[str] = []
    for root in ROOTS:
        for path in sorted(root.rglob("*.py")):
            failures.extend(analyze(path))
    if failures:
        print("\n".join(failures))
        return 1
    print(f"Complexity checks passed (CCN <= {MAX_CCN}, function lines <= {MAX_LINES}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
