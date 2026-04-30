from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY = PROJECT_ROOT / "admin" / "data" / "knowledge_sources" / "registry.json"
DEFAULT_OUT = PROJECT_ROOT / "llm_training_project" / "knowledge_corpus" / "knowledge_corpus.jsonl"


@dataclass
class Source:
    id: str
    type: str
    path: str
    tags: List[str]
    notes: str = ""


def _clean_text(text: str) -> str:
    t = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"\n{3,}", "\n\n", t)
    t = re.sub(r"[ \t]{2,}", " ", t)
    return t.strip()


def _chunks(text: str, max_chars: int) -> List[str]:
    text = _clean_text(text)
    if not text:
        return []

    if max_chars <= 0:
        return [text]

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


def _load_registry(path: Path) -> List[Source]:
    data = json.loads(path.read_text(encoding="utf-8"))
    sources_raw = data.get("sources") or []
    out: List[Source] = []
    for s in sources_raw:
        out.append(
            Source(
                id=str(s.get("id") or "").strip(),
                type=str(s.get("type") or "").strip(),
                path=str(s.get("path") or "").strip(),
                tags=list(s.get("tags") or []),
                notes=str(s.get("notes") or ""),
            )
        )
    return [s for s in out if s.id and s.type and s.path]


def _iter_pdf_pages(pdf_path: Path) -> Iterable[Dict[str, Any]]:
    try:
        import fitz  # PyMuPDF
    except Exception as e:
        raise RuntimeError("PyMuPDF (fitz) is required to ingest PDFs") from e

    doc = fitz.open(pdf_path)
    try:
        for i in range(len(doc)):
            page = doc.load_page(i)
            text = (page.get_text("text") or "").replace("\r\n", "\n").replace("\r", "\n").strip()
            yield {
                "page": i + 1,
                "text": text,
            }
    finally:
        doc.close()


def _read_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = (line or "").strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if isinstance(obj, dict):
                yield obj


def _emit_record(f_out, rec: Dict[str, Any]) -> None:
    f_out.write(json.dumps(rec, ensure_ascii=False))
    f_out.write("\n")


def ingest(
    *,
    registry_path: Path,
    out_path: Path,
    include_source_ids: Optional[List[str]] = None,
    limit_per_source: int = 0,
    max_chunk_chars: int = 900,
) -> Dict[str, Any]:
    include_set = {s.strip() for s in (include_source_ids or []) if s and s.strip()}

    sources = _load_registry(registry_path)
    if include_set:
        sources = [s for s in sources if s.id in include_set]

    out_path.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    per_source: Dict[str, int] = {}

    with out_path.open("w", encoding="utf-8") as f_out:
        for src in sources:
            src_count = 0
            src_path = (PROJECT_ROOT / src.path).resolve() if not Path(src.path).is_absolute() else Path(src.path)

            doc_id = src.id

            if src.type == "jsonl_file":
                if not src_path.exists():
                    continue
                for obj in _read_jsonl(src_path):
                    text_value = ""
                    if isinstance(obj.get("text"), str):
                        text_value = str(obj.get("text") or "")
                    else:
                        text_value = json.dumps(obj, ensure_ascii=False)

                    for idx, chunk in enumerate(_chunks(text_value, int(max_chunk_chars))):
                        chunk_id = f"{doc_id}:l{src_count+1}:c{idx+1}"
                        rec = {
                            "doc_id": doc_id,
                            "chunk_id": chunk_id,
                            "text": chunk,
                            "tags": src.tags,
                            "source": {
                                "source_id": src.id,
                                "source_type": src.type,
                                "source_path": str(src.path),
                                "line": src_count + 1,
                            },
                            "payload": obj,
                        }
                        _emit_record(f_out, rec)
                        written += 1
                        src_count += 1
                        if limit_per_source and src_count >= limit_per_source:
                            break

                    if limit_per_source and src_count >= limit_per_source:
                        break

            elif src.type == "pdf_file":
                if not src_path.exists():
                    continue
                for page in _iter_pdf_pages(src_path):
                    page_num = int(page.get("page") or 0)
                    text_value = str(page.get("text") or "")
                    for idx, chunk in enumerate(_chunks(text_value, int(max_chunk_chars))):
                        chunk_id = f"{doc_id}:p{page_num}:c{idx+1}"
                        rec = {
                            "doc_id": doc_id,
                            "chunk_id": chunk_id,
                            "text": chunk,
                            "tags": src.tags,
                            "source": {
                                "source_id": src.id,
                                "source_type": src.type,
                                "source_path": str(src.path),
                                "pdf": str(src.path),
                                "page": page_num,
                            },
                            "payload": {"pdf": str(src.path), **page},
                        }
                        _emit_record(f_out, rec)
                        written += 1
                        src_count += 1
                        if limit_per_source and src_count >= limit_per_source:
                            break

                    if limit_per_source and src_count >= limit_per_source:
                        break

            elif src.type == "pdf_dir":
                if not src_path.exists() or not src_path.is_dir():
                    continue
                pdfs = sorted([p for p in src_path.glob("*.pdf") if p.is_file()])
                for pdf in pdfs:
                    for page in _iter_pdf_pages(pdf):
                        page_num = int(page.get("page") or 0)
                        text_value = str(page.get("text") or "")
                        pdf_ref = str(pdf.relative_to(PROJECT_ROOT)) if pdf.is_relative_to(PROJECT_ROOT) else str(pdf)
                        for idx, chunk in enumerate(_chunks(text_value, int(max_chunk_chars))):
                            chunk_id = f"{doc_id}:{pdf.stem}:p{page_num}:c{idx+1}"
                            rec = {
                                "doc_id": doc_id,
                                "chunk_id": chunk_id,
                                "text": chunk,
                                "tags": src.tags,
                                "source": {
                                    "source_id": src.id,
                                    "source_type": src.type,
                                    "source_path": str(src.path),
                                    "pdf": pdf_ref,
                                    "page": page_num,
                                },
                                "payload": {"pdf": pdf_ref, **page},
                            }
                            _emit_record(f_out, rec)
                            written += 1
                            src_count += 1
                            if limit_per_source and src_count >= limit_per_source:
                                break
                    if limit_per_source and src_count >= limit_per_source:
                        break

            per_source[src.id] = src_count

    return {
        "registry": str(registry_path),
        "out": str(out_path),
        "sources": [s.id for s in sources],
        "written": written,
        "per_source": per_source,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", type=str, default=str(DEFAULT_REGISTRY))
    ap.add_argument("--out", type=str, default=str(DEFAULT_OUT))
    ap.add_argument("--only", type=str, default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--max-chars", type=int, default=900)
    args = ap.parse_args()

    registry_path = Path(args.registry)
    out_path = Path(args.out)

    include = [s.strip() for s in (args.only or "").split(",") if s.strip()]

    result = ingest(
        registry_path=registry_path,
        out_path=out_path,
        include_source_ids=include or None,
        limit_per_source=int(args.limit) if args.limit and args.limit > 0 else 0,
        max_chunk_chars=int(args.max_chars) if args.max_chars and args.max_chars > 0 else 0,
    )

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
