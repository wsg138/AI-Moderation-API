from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

Severity = Literal["error", "warning"]


@dataclass(frozen=True, slots=True)
class Diagnostic:
    path: str
    line: int | None
    severity: Severity
    code: str
    message: str

    def sort_key(self) -> tuple[int, str, str, str]:
        return (self.line or 0, self.severity, self.code, self.message)

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "line": self.line,
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class ExpectedRange:
    prefix: str
    start: int
    end: int

    @property
    def width(self) -> int:
        return 4

    def expected_ids(self) -> set[str]:
        return {
            f"{self.prefix}-{value:0{self.width}d}"
            for value in range(self.start, self.end + 1)
        }


@dataclass(frozen=True, slots=True)
class RecordRef:
    path: Path
    line: int
    data: dict[str, Any]

    @property
    def example_id(self) -> str:
        value = self.data.get("example_id")
        return value if isinstance(value, str) else f"line-{self.line}"


@dataclass(slots=True)
class DatasetResult:
    path: Path
    records: list[RecordRef]
    diagnostics: list[Diagnostic]
    exact_duplicate_groups: list[list[str]] = field(default_factory=list)
    near_duplicate_candidates: list[dict[str, object]] = field(default_factory=list)
    family_suggestions: list[dict[str, object]] = field(default_factory=list)

    def errors(self) -> list[Diagnostic]:
        return [item for item in self.diagnostics if item.severity == "error"]

    def warnings(self) -> list[Diagnostic]:
        return [item for item in self.diagnostics if item.severity == "warning"]
