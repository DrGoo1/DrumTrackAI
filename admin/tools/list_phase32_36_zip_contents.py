import zipfile
from pathlib import Path


def main() -> int:
    base = Path(r"F:\DrumTracKAI_v1.1.17\ChatGPT_Gap_Analysis\Phase_32-36")
    if not base.exists():
        print(f"ERROR: folder not found: {base}")
        return 2

    zips = sorted(base.glob("*.zip"))
    if not zips:
        print(f"No .zip files found in: {base}")
        return 0

    for p in zips:
        print(f"\n== {p.name} ==")
        try:
            with zipfile.ZipFile(p, "r") as z:
                for n in z.namelist():
                    if n.endswith("/"):
                        continue
                    info = z.getinfo(n)
                    print(f"{n} ({info.file_size} bytes)")
        except Exception as e:
            print(f"ERROR reading {p}: {e}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
