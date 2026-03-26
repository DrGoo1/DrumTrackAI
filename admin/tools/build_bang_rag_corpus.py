from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List


def _load_manifest(manifest_jsonl: Path) -> List[Dict[str, object]]:
    entries: List[Dict[str, object]] = []
    with manifest_jsonl.open("r", encoding="utf-8") as f:
        for line in f:
            line = (line or "").strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except Exception:
                continue
    return entries


def _read_pages(pages_jsonl: Path) -> List[Dict[str, object]]:
    pages: List[Dict[str, object]] = []
    if not pages_jsonl.exists():
        return pages
    with pages_jsonl.open("r", encoding="utf-8") as f:
        for line in f:
            line = (line or "").strip()
            if not line:
                continue
            try:
                pages.append(json.loads(line))
            except Exception:
                continue
    return pages


def _clean_text(text: str) -> str:
    t = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"\n{3,}", "\n\n", t)
    t = re.sub(r"[ \t]{2,}", " ", t)
    return t.strip()


def _chunks(text: str, max_chars: int) -> List[str]:
    text = _clean_text(text)
    if not text:
        return []

    paras = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
    out: List[str] = []
    buf: List[str] = []

    def flush() -> None:
        if not buf:
            return
        out.append("\n\n".join(buf).strip())
        buf.clear()

    for p in paras:
        if not buf:
            buf.append(p)
            continue
        if sum(len(x) for x in buf) + len(p) + 2 <= max_chars:
            buf.append(p)
        else:
            flush()
            if len(p) <= max_chars:
                buf.append(p)
            else:
                for i in range(0, len(p), max_chars):
                    out.append(p[i : i + max_chars])

    flush()
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--manifest",
        default=str(Path("Drum_Education") / "extracted" / "BangTheDrumSchool_manifest.jsonl"),
    )
    ap.add_argument(
        "--out",
        default=str(Path("Drum_Education") / "extracted" / "BangTheDrumSchool_rag.jsonl"),
    )
    ap.add_argument("--max-chars", type=int, default=900)
    ap.add_argument("--max-pages-per-pdf", type=int, default=10)
    args = ap.parse_args()

    manifest = Path(args.manifest)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    entries = _load_manifest(manifest)

    written = 0
    with out.open("w", encoding="utf-8") as f:
        for e in entries:
            pages_path = Path(str(e.get("pages_jsonl") or ""))
            if not pages_path.exists():
                continue

            pages = _read_pages(pages_path)
            if args.max_pages_per_pdf and args.max_pages_per_pdf > 0:
                pages = pages[: int(args.max_pages_per_pdf)]

            tags = list(e.get("tags") or [])
            doc_id = str(e.get("id") or pages_path.parent.name)
            preview_png = e.get("preview_png")

            for p in pages:
                page_num = int(p.get("page") or 0)
                text = str(p.get("text") or "")
                for idx, chunk in enumerate(_chunks(text, int(args.max_chars))):
                    rec = {
                        "doc_id": doc_id,
                        "chunk_id": f"{doc_id}:p{page_num}:c{idx+1}",
                        "source": "bangthedrumschool",
                        "source_ref": {
                            "pdf": str(p.get("pdf") or ""),
                            "page": page_num,
                            "pages_jsonl": str(pages_path),
                            "preview_png": preview_png,
                        },
                        "tags": tags,
                        "text": chunk,
                    }
                    f.write(json.dumps(rec, ensure_ascii=False))
                    f.write("\n")
                    written += 1

    print(f"Wrote {written} chunks")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
