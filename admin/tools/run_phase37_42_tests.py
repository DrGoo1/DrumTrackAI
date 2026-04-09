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

    # Run all phase37-42 tests by default. If none exist yet, error clearly.
    tests_dir = repo_root / "backend" / "tests"
    candidates = sorted(tests_dir.glob("test_phase3[7-9]*.py")) + sorted(tests_dir.glob("test_phase4[0-2]*.py"))
    if not candidates:
        print(f"ERROR: no phase37-42 tests found under: {tests_dir}")
        return 3

    args = ["-q", *[str(p) for p in candidates]]
    return int(pytest.main(args))


if __name__ == "__main__":
    raise SystemExit(main())
