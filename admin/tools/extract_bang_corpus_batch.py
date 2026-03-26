from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--pdf-dir",
        default=str(Path("Drum_Education") / "BangTheDrumSchool"),
        help="Directory containing downloaded BangTheDrumSchool PDFs",
    )
    ap.add_argument(
        "--out-root",
        default=str(Path("Drum_Education") / "extracted" / "BangTheDrumSchool"),
        help="Root output directory",
    )
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--limit", type=int, default=25, help="Max PDFs to process this run")
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()

    pdf_dir = Path(args.pdf_dir)
    out_root = Path(args.out_root)
    out_root.mkdir(parents=True, exist_ok=True)

    pdfs = sorted(pdf_dir.glob("*.pdf"))
    print(f"Found {len(pdfs)} pdfs")

    processed = 0
    skipped = 0

    extractor = Path("admin") / "tools" / "extract_pdf_corpus.py"

    for p in pdfs:
        out_dir = out_root / p.stem
        jsonl_path = out_dir / "pages.jsonl"
        if not args.overwrite and jsonl_path.exists() and jsonl_path.stat().st_size > 0:
            skipped += 1
            continue

        cmd = [
            sys.executable,
            str(extractor),
            str(p),
            "--out",
            str(out_dir),
            "--render-pages",
            "--dpi",
            str(int(args.dpi)),
        ]
        subprocess.run(cmd, check=True)
        processed += 1
        print(f"Processed [{processed}] {p.name}")

        if processed >= int(args.limit):
            break

    print(f"Done. processed={processed} skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
