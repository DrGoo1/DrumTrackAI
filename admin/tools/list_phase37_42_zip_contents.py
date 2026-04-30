import zipfile
from pathlib import Path


def _banner() -> None:
    print("\n" + "=" * 78)
    print("RUN THIS SCRIPT FROM POWERSHELL (PS ...>), NOT FROM PYTHON REPL (>>>).")
    print("If you see >>>, type: exit()  then re-run from PS with: python admin\\tools\\...")
    print("=" * 78 + "\n")


def main() -> int:
    _banner()
    base = Path(r"F:\DrumTracKAI_v1.1.17\ChatGPT_Gap_Analysis\Phase_37-42")
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
