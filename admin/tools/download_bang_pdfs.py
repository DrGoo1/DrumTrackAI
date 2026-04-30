from __future__ import annotations

import argparse
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path


def _fetch_html(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) DrumTracKAI/1.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(req) as resp:
        data = resp.read()
    return data.decode("utf-8", errors="ignore")


def _extract_pdf_urls(page_url: str, html: str) -> list[str]:
    urls = set(re.findall(r"https?://[^\"\s>]+?\.pdf", html, flags=re.IGNORECASE))
    urls |= {
        urllib.parse.urljoin(page_url, u)
        for u in re.findall(r"/wp-content/uploads/[^\"\s>]+?\.pdf", html, flags=re.IGNORECASE)
    }
    return sorted(urls)


def _download(url: str, dest: Path) -> None:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) DrumTracKAI/1.0",
            "Accept": "application/pdf,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(req) as resp:
        dest.write_bytes(resp.read())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--page",
        default="https://bangthedrumschool.com/the-nasty-licks-series-drum-fills-chops-and-soloing-ideas-on-pdf/",
    )
    ap.add_argument("--out", default=str(Path("Drum_Education") / "BangTheDrumSchool"))
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    html = _fetch_html(args.page)
    urls = _extract_pdf_urls(args.page, html)
    print(f"Found {len(urls)} PDF links")

    ok = 0
    failed = 0
    skipped = 0

    for u in urls:
        fname = Path(urllib.parse.urlparse(u).path).name
        if not fname.lower().endswith(".pdf"):
            continue
        dest = out_dir / fname
        if dest.exists() and dest.stat().st_size > 0 and not args.overwrite:
            skipped += 1
            continue
        try:
            _download(u, dest)
            if dest.exists() and dest.stat().st_size > 0:
                ok += 1
                print(f"Downloaded: {fname}")
            else:
                failed += 1
                print(f"Failed (empty): {fname}")
        except Exception as e:
            failed += 1
            print(f"Failed: {fname} :: {e}")

    print(f"Done. ok={ok} skipped={skipped} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
