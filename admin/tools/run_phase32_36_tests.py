from __future__ import annotations

import sys
from pathlib import Path


def _banner() -> None:
    print("\n" + "=" * 78)
    print("RUN THIS SCRIPT FROM POWERSHELL (PS ...>), NOT FROM PYTHON REPL (>>>).")
    print("If you see >>>, type: exit()  then re-run from PS with: python admin\\tools\\...")
    print("=" * 78 + "\n")


def main() -> int:
    _banner()
    try:
        import pytest  # type: ignore
    except Exception as e:
        print(f"ERROR: pytest is not available in this environment: {e}")
        return 2

    repo_root = Path(__file__).resolve().parents[2]
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)
    tests = [
        repo_root / "backend" / "tests" / "test_phase32_rudiments.py",
        repo_root / "backend" / "tests" / "test_phase33_rudiment_generation.py",
        repo_root / "backend" / "tests" / "test_phase34_rudiment_runtime.py",
        repo_root / "backend" / "tests" / "test_phase35_rudiment_library_extended.py",
        repo_root / "backend" / "tests" / "test_phase36_extended_rudiment_runtime.py",
    ]

    missing = [str(p) for p in tests if not p.exists()]
    if missing:
        print("ERROR: missing expected test files:")
        for p in missing:
            print(f"- {p}")
        return 3

    args = ["-q", *[str(p) for p in tests]]
    return int(pytest.main(args))


if __name__ == "__main__":
    raise SystemExit(main())
