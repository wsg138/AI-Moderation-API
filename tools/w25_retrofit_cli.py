"""Launch the offline W25 saved-bundle audit on Windows without PYTHONPATH setup."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--private-data-root", type=Path, required=True)
    args, remaining = parser.parse_known_args()
    root = args.private_data_root.resolve()
    if not root.is_dir() or root == repo or repo in root.parents:
        raise ValueError("Explicit private approved source directory required")
    os.environ["W25_PRIVATE_DATA_ROOT"] = str(root)
    sys.path.insert(0, str(repo))
    sys.path.insert(0, str(repo / "service"))
    sys.argv = [sys.argv[0], *remaining]
    from workers.w25.retrofit_dev_artifacts import main as audit

    audit()


if __name__ == "__main__":
    main()
