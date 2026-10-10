"""Launch a local-only W25 CPU development probe from the repository root.

The moderation_api package lives under service/ and the worker modules live at
the repository root. This wrapper sets up local imports without installing
anything or relying on a shell-managed PYTHONPATH.
"""
from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    service = root / "service"
    if not (service / "moderation_api").is_dir():
        raise ValueError("Expected the repository-local moderation API source")
    sys.path.insert(0, str(service))
    from workers.w25.development_probe import main as probe_main

    probe_main()


if __name__ == "__main__":
    main()
