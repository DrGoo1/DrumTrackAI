from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Set


def _read_pages_text(pages_jsonl: Path, max_chars: int = 8000) -> str:
    if not pages_jsonl.exists():
        return ""
    parts: List[str] = []
    try:
        with pages_jsonl.open("r", encoding="utf-8") as f:
            for line in f:
                line = (line or "").strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                t = str(obj.get("text") or "").strip()
                if t:
                    parts.append(t)
                if sum(len(x) for x in parts) >= max_chars:
                    break
    except Exception:
        return ""
    return "\n".join(parts)[:max_chars]


def _tokenize(s: str) -> List[str]:
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return [t for t in s.split() if t]


def _infer_tags(name: str, text: str) -> List[str]:
    tokens = set(_tokenize(name) + _tokenize(text))

    tag_map = {
        # Feel / grid
        "triplet": {"triplet", "triplets"},
        "16ths": {"16th", "16ths", "sixteenth", "sixteenths"},
        "32nds": {"32nd", "32nds", "thirty", "second"},
        "shuffle": {"shuffle"},
        "swing": {"swing", "swung"},
        # Techniques
        "paradiddle": {"paradiddle", "paradiddles"},
        "diddle": {"diddle", "diddles"},
        "flam": {"flam", "flams"},
        "drag": {"drag", "drags"},
        "rudiment": {"rudiment", "rudiments"},
        "linear": {"linear"},
        "roundhouse": {"roundhouse"},
        "rlrf": {"rlrf"},
        "rlrff": {"rlrff"},
        "rll": {"rll"},
        "llrr": {"llrr"},
        "independence": {"independence", "interdependence"},
        # Instruments
        "toms": {"tom", "toms", "hitom", "hi", "floortom", "floor"},
        "snare": {"snare"},
        "kick": {"kick", "bass", "drum"},
        "hihat": {"hihat", "hi", "hat"},
        "crash": {"crash"},
        "ride": {"ride"},
        # Artists / references
        "bonham": {"bonham"},
        "vinnie": {"vinnie", "colaiuta"},
        "gadd": {"gadd"},
        "tony_williams": {"williams", "tony"},
        "philly_joe": {"philly", "joe"},
        "chris_coleman": {"coleman", "chris"},
        # Usage
        "fill": {"fill", "fills"},
        "solo": {"solo", "soloing"},
        "chops": {"chops"},
    }

    tags: Set[str] = set()
    for tag, words in tag_map.items():
        if tokens.intersection(words):
            tags.add(tag)

    # Basic numeric lick tags if present
    m = re.search(r"\b(?:nasty[-_ ]?lick|nl)[-_ ]?(\d{1,3})\b", name.lower())
    if m:
        tags.add(f"nasty_lick_{m.group(1)}")

    return sorted(tags)


def _count_pages(meta_json: Path) -> int:
    if not meta_json.exists():
        return 0
    try:
        obj = json.loads(meta_json.read_text(encoding="utf-8"))
        return int(obj.get("pages") or 0)
    except Exception:
        return 0


def iter_extracted_entries(extracted_root: Path) -> Iterable[Dict[str, object]]:
    for d in sorted([p for p in extracted_root.iterdir() if p.is_dir()]):
        pages_jsonl = d / "pages.jsonl"
        meta_json = d / "meta.json"
        pages_dir = d / "pages"
        page_pngs = sorted([p for p in pages_dir.glob("*.png")]) if pages_dir.exists() else []

        text = _read_pages_text(pages_jsonl)
        tags = _infer_tags(d.name, text)

        yield {
            "id": d.name,
            "source": "bangthedrumschool",
            "pdf_stem": d.name,
            "extracted_dir": str(d),
            "pages_jsonl": str(pages_jsonl) if pages_jsonl.exists() else None,
            "page_count": _count_pages(meta_json),
            "page_png_count": len(page_pngs),
            "preview_png": str(page_pngs[0]) if page_pngs else None,
            "tags": tags,
        }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--extracted-root",
        default=str(Path("Drum_Education") / "extracted" / "BangTheDrumSchool"),
    )
    ap.add_argument(
        "--out-jsonl",
        default=str(Path("Drum_Education") / "extracted" / "BangTheDrumSchool_manifest.jsonl"),
    )
    ap.add_argument(
        "--out-csv",
        default=str(Path("Drum_Education") / "extracted" / "BangTheDrumSchool_manifest.csv"),
    )
    args = ap.parse_args()

    extracted_root = Path(args.extracted_root)
    out_jsonl = Path(args.out_jsonl)
    out_csv = Path(args.out_csv)
    out_jsonl.parent.mkdir(parents=True, exist_ok=True)

    entries = list(iter_extracted_entries(extracted_root))

    with out_jsonl.open("w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False))
            f.write("\n")

    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "id",
                "source",
                "pdf_stem",
                "page_count",
                "page_png_count",
                "preview_png",
                "extracted_dir",
                "pages_jsonl",
                "tags",
            ],
        )
        w.writeheader()
        for e in entries:
            row = dict(e)
            row["tags"] = " ".join(row.get("tags") or [])
            w.writerow(row)

    print(f"Wrote {len(entries)} entries")
    print(out_jsonl)
    print(out_csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
