import os
import zipfile
from pathlib import Path


BASE_DIR = Path(r"F:\DrumTracKAI_v1.1.17\ChatGPT_Gap_Analysis\Phase_32-36")
REPO_ROOT = Path(r"F:\DrumTracKAI_v1.1.17")


def _banner() -> None:
    print("\n" + "=" * 78)
    print("RUN THIS SCRIPT FROM POWERSHELL (PS ...>), NOT FROM PYTHON REPL (>>>).")
    print("If you see >>>, type: exit()  then re-run from PS with: python admin\\tools\\...")
    print("=" * 78 + "\n")


def _map_member_to_repo_path(member: str) -> Path | None:
    member = str(member or "")
    if not member or member.endswith("/"):
        return None

    # members look like:
    #   phase32/backend/backend/drummerbrain/foo.py
    #   phase32/backend/backend/tests/test_*.py
    #   phase32/docs/PHASE32_*.md
    parts = member.split("/")
    if len(parts) < 2:
        return None

    # Strip leading phase folder (phase32/phase33/etc)
    phase_prefix = parts[0]
    rel_parts = parts[1:]

    # docs
    if rel_parts and rel_parts[0] == "docs":
        # phaseXX/docs/<file> -> docs/<file>
        return REPO_ROOT / "docs" / "/".join(rel_parts[1:])

    # backend modules/tests
    # phaseXX/backend/backend/drummerbrain/... -> backend/drummerbrain/...
    # phaseXX/backend/backend/tests/... -> backend/tests/...
    if len(rel_parts) >= 3 and rel_parts[0] == "backend" and rel_parts[1] == "backend":
        sub = rel_parts[2:]
        return REPO_ROOT / "backend" / "/".join(sub)

    # Unknown mapping: keep under ChatGPT_Gap_Analysis for inspection
    return REPO_ROOT / "ChatGPT_Gap_Analysis" / "Phase_32-36" / "_unmapped" / phase_prefix / "/".join(rel_parts)


def main() -> int:
    _banner()
    if not BASE_DIR.exists():
        print(f"ERROR: base folder not found: {BASE_DIR}")
        return 2

    zips = sorted(BASE_DIR.glob("*.zip"))
    if not zips:
        print(f"No .zip files found in: {BASE_DIR}")
        return 0

    planned: list[tuple[Path, str, str]] = []  # (dest, zip, member)
    collisions: list[Path] = []

    for zp in zips:
        with zipfile.ZipFile(zp, "r") as z:
            for member in z.namelist():
                if member.endswith("/"):
                    continue
                dest = _map_member_to_repo_path(member)
                if dest is None:
                    continue
                planned.append((dest, zp.name, member))
                if dest.exists():
                    collisions.append(dest)

    if collisions:
        print("ABORT: one or more target files already exist. Option 1 selected (no overwrite).")
        for p in sorted(set(collisions)):
            print(f"- {p}")
        print("\nIf you want to overwrite, rerun after deleting/moving those files, or tell me to implement overwrite mode.")
        return 3

    wrote = 0
    for dest, zip_name, member in planned:
        dest.parent.mkdir(parents=True, exist_ok=True)
        zip_path = BASE_DIR / zip_name
        with zipfile.ZipFile(zip_path, "r") as z:
            data = z.read(member)
        # Write bytes (handles both .py and .md)
        with open(dest, "wb") as f:
            f.write(data)
        wrote += 1
        print(f"WROTE {dest}  <=  {zip_name}:{member}")

    print(f"\nDone. Wrote {wrote} files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
