"""Launch a local-only W25 CPU development probe from the repository root.

The moderation_api package lives under service/ and the worker modules live at
the repository root. This wrapper sets up local imports without installing
anything or relying on a shell-managed PYTHONPATH.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    service = root / "service"
    if not (service / "moderation_api").is_dir():
        raise ValueError("Expected the repository-local moderation API source")
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--private-data-root", type=Path)
    args, remaining = parser.parse_known_args()
    if args.private_data_root is not None:
        private = args.private_data_root.resolve()
        if not private.is_dir() or root == private or root in private.parents:
            raise ValueError("Private admitted data must exist outside the repository")
        os.environ["W25_PRIVATE_DATA_ROOT"] = str(private)
    sys.argv = [sys.argv[0], *remaining]
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(service))
    from workers.w25.development_probe import main as probe_main

    probe_main()


if __name__ == "__main__":
    main()
