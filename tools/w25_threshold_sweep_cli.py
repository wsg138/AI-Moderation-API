"""Windows-friendly launcher for a private development-only threshold sweep."""
from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / "service"))
    from workers.w25.threshold_sweep import main as run_sweep

    run_sweep()


if __name__ == "__main__":
    main()
