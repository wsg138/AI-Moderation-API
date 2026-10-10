"""Start an offline ensemble comparison without manual PYTHONPATH configuration."""
from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    service = root / "service"
    if not (service / "moderation_api").is_dir():
        raise ValueError("Missing local moderation_api package")
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(service))
    from workers.w25.ensemble_development import main as worker_main

    worker_main()


if __name__ == "__main__":
    main()
