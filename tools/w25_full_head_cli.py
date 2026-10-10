"""Windows-friendly launcher for private saved W25 six-head blend diagnostics."""
from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / "service"))
    from workers.w25.full_head_blend import main as blend_main

    blend_main()


if __name__ == "__main__":
    main()
