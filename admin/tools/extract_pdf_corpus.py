from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

import fitz  # PyMuPDF


def _safe_text(s: str) -> str:
    return (s or "").replace("\r\n", "\n").replace("\r", "\n").strip()


def extract_pdf(
    pdf_path: Path,
    out_dir: Path,
    *,
    render_pages: bool,
    dpi: int,
    max_pages: int | None,
) -> Dict[str, object]:
    if not pdf_path.exists():
        raise FileNotFoundError(str(pdf_path))

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "pages").mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    try:
        n_pages = len(doc)
        if max_pages is not None:
            n_pages = min(n_pages, max_pages)

        records: List[Dict[str, object]] = []
        for i in range(n_pages):
            page = doc.load_page(i)
            text = _safe_text(page.get_text("text") or "")

            page_png: str | None = None
            if render_pages:
                mat = fitz.Matrix(dpi / 72.0, dpi / 72.0)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                page_png = f"pages/page_{i+1:03d}.png"
                pix.save(str(out_dir / page_png))

            records.append(
                {
                    "pdf": str(pdf_path),
                    "page": i + 1,
                    "text": text,
                    "page_png": page_png,
                }
            )

        jsonl_path = out_dir / "pages.jsonl"
        with jsonl_path.open("w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False))
                f.write("\n")

        meta = {
            "pdf": str(pdf_path),
            "pages": len(doc),
            "pages_exported": n_pages,
            "render_pages": render_pages,
            "dpi": dpi,
            "out_dir": str(out_dir),
            "jsonl": str(jsonl_path),
        }
        (out_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return meta
    finally:
        doc.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", type=str)
    ap.add_argument("--out", type=str, required=True)
    ap.add_argument("--render-pages", action="store_true")
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--max-pages", type=int, default=0)
    args = ap.parse_args()

    pdf_path = Path(args.pdf)
    out_dir = Path(args.out)
    max_pages = args.max_pages if args.max_pages and args.max_pages > 0 else None

    meta = extract_pdf(
        pdf_path,
        out_dir,
        render_pages=bool(args.render_pages),
        dpi=int(args.dpi),
        max_pages=max_pages,
    )
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
