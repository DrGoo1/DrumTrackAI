import zipfile
from pathlib import Path


def main() -> int:
    base = Path(r"F:\DrumTracKAI_v1.1.17\ChatGPT_Gap_Analysis\Phase_32-36")
    out = base / "_extracted"

    if not base.exists():
        print(f"ERROR: folder not found: {base}")
        return 2

    zips = sorted(base.glob("*.zip"))
    if not zips:
        print(f"No .zip files found in: {base}")
        return 0

    out.mkdir(parents=True, exist_ok=True)

    for p in zips:
        print(f"Extracting: {p.name}")
        try:
            with zipfile.ZipFile(p, "r") as z:
                z.extractall(out)
        except Exception as e:
            print(f"ERROR extracting {p}: {e}")
            return 3

    print(f"Extracted to: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
