#!/usr/bin/env python3
"""
DrumTracKAI Windsurf Context Builder

Builds compact, model-safe context packets from selected files or folders.
Use this instead of pasting entire files/repo context into Windsurf.

Examples:
  python tools/context_builder.py --files backend/app/assimilation/microtiming.py backend/app/assimilation/fill_behavior.py
  python tools/context_builder.py --dirs backend/app/assimilation --include "*.py" --max-lines 2200
  python tools/context_builder.py --files path/to/file.py --focus "microtiming offset bug" --out docs/ai_context/context_packet.md
"""

from __future__ import annotations

import argparse
import fnmatch
import os
from pathlib import Path
from typing import Iterable, List, Tuple
import math

DEFAULT_EXCLUDES = {
    ".git", ".venv", "venv", "env", "__pycache__", ".pytest_cache", ".mypy_cache",
    "node_modules", "dist", "build", "coverage", ".next", ".turbo", "DerivedDataCache",
    "Intermediate", "Saved", "Binaries", "target", ".idea", ".vscode",
}

BINARY_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico", ".wav", ".mp3", ".flac",
    ".ogg", ".mp4", ".mov", ".avi", ".mkv", ".zip", ".7z", ".rar", ".pdf", ".exe",
    ".dll", ".pyd", ".so", ".dylib", ".uasset", ".umap", ".fbx", ".pt", ".pth", ".onnx",
    ".sqlite", ".db", ".parquet", ".npy", ".npz",
}

COMMENT_PREFIX = {
    ".py": "#",
    ".js": "//",
    ".jsx": "//",
    ".ts": "//",
    ".tsx": "//",
    ".cpp": "//",
    ".h": "//",
    ".hpp": "//",
    ".cs": "//",
    ".java": "//",
    ".rs": "//",
    ".go": "//",
    ".sql": "--",
    ".md": "<!--",
}


def is_binary_or_ignored(path: Path) -> bool:
    if path.suffix.lower() in BINARY_EXTS:
        return True
    return any(part in DEFAULT_EXCLUDES for part in path.parts)


def discover_files(dirs: Iterable[str], include_patterns: List[str]) -> List[Path]:
    found: List[Path] = []
    for d in dirs:
        root = Path(d)
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if not p.is_file() or is_binary_or_ignored(p):
                continue
            rel = str(p).replace("\\", "/")
            if any(fnmatch.fnmatch(p.name, pat) or fnmatch.fnmatch(rel, pat) for pat in include_patterns):
                found.append(p)
    return sorted(set(found))


def safe_read(path: Path, max_file_lines: int) -> Tuple[str, int, bool]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return f"[Could not read file: {exc}]", 0, False
    lines = text.splitlines()
    truncated = len(lines) > max_file_lines
    if truncated:
        lines = lines[:max_file_lines]
    return "\n".join(lines), len(text.splitlines()), truncated


def extract_summary_header(text: str, suffix: str, max_lines: int = 40) -> str:
    lines = text.splitlines()[:max_lines]
    prefix = COMMENT_PREFIX.get(suffix.lower())
    if not prefix:
        return ""
    summary_lines = []
    capture = False
    for line in lines:
        stripped = line.strip()
        lowered = stripped.lower()
        if "summary:" in lowered or "purpose:" in lowered or "ai context:" in lowered:
            capture = True
        if capture:
            summary_lines.append(line)
        if capture and len(summary_lines) >= 18:
            break
    return "\n".join(summary_lines).strip()


def approx_tokens(text: str) -> int:
    # Rough but useful: 1 token ~= 4 chars for English/code-heavy context.
    return max(1, len(text) // 4)


def _filter_text(text: str, suffix: str, *, strip_comments: bool, max_line_chars: int) -> str:
    lines = text.splitlines()
    prefix = COMMENT_PREFIX.get(suffix.lower())
    out: List[str] = []
    blank_run = 0
    for raw in lines:
        line = raw
        if max_line_chars and max_line_chars > 0 and len(line) > max_line_chars:
            line = line[:max_line_chars]
        if strip_comments and prefix and line.lstrip().startswith(prefix):
            # skip full-line comment
            continue
        if not line.strip():
            blank_run += 1
            if blank_run > 1:
                # collapse multiple blank lines
                continue
        else:
            blank_run = 0
        out.append(line)
    return "\n".join(out)


def build_packet(
    files: List[Path],
    focus: str,
    max_total_lines: int,
    max_file_lines: int,
    *,
    strip_comments: bool = False,
    max_line_chars: int = 0,
) -> str:
    output: List[str] = []
    output.append("# DrumTracKAI Windsurf Context Packet")
    output.append("")
    if focus:
        output.append(f"## Focus\n{focus}\n")
    output.append("## Instructions for AI Agent")
    output.append("- Use only the context below unless you explicitly ask for another small file/range.")
    output.append("- Do not rewrite unrelated systems.")
    output.append("- Prefer surgical patches and explain exact files/functions changed.")
    output.append("- Avoid long-running commands unless they include timeouts and visible progress logs.")
    output.append("- For DrumTracKAI, preserve existing architecture and add modular code only.\n")

    output.append("## Included Files")
    for f in files:
        output.append(f"- `{f}`")
    output.append("")

    remaining = max_total_lines
    for path in files:
        if remaining <= 0:
            output.append("\n[Context stopped: max total line budget reached.]\n")
            break
        text, original_lines, truncated_file = safe_read(path, min(max_file_lines, remaining))
        summary = extract_summary_header(text, path.suffix)
        filtered = _filter_text(text, path.suffix, strip_comments=strip_comments, max_line_chars=max_line_chars)
        shown_lines = len(filtered.splitlines())
        remaining -= shown_lines
        output.append(f"## File: `{path}`")
        output.append(f"Lines included: {shown_lines} / {original_lines}" + (" — truncated" if truncated_file else ""))
        if summary:
            output.append("\n### Existing summary header")
            output.append("```text")
            output.append(summary)
            output.append("```")
        lang = path.suffix.lstrip(".") or "text"
        output.append(f"\n```{lang}")
        output.append(filtered)
        output.append("```")
        output.append("")

    packet = "\n".join(output)
    packet += f"\n---\nApprox tokens: {approx_tokens(packet)}\n"
    return packet


def main() -> int:
    parser = argparse.ArgumentParser(description="Build model-safe context packets for Windsurf.")
    parser.add_argument("--files", nargs="*", default=[], help="Specific files to include.")
    parser.add_argument("--dirs", nargs="*", default=[], help="Directories to scan.")
    parser.add_argument("--include", nargs="*", default=["*.py", "*.ts", "*.tsx", "*.js", "*.jsx", "*.sql", "*.md", "*.json"], help="Include glob patterns.")
    parser.add_argument("--focus", default="", help="Short task focus to include at top of packet.")
    parser.add_argument("--max-lines", type=int, default=2200, help="Maximum total lines in packet.")
    parser.add_argument("--max-file-lines", type=int, default=700, help="Maximum lines per file.")
    parser.add_argument("--out", default="docs/ai_context/context_packet.md", help="Output markdown file (or prefix when splitting).")
    parser.add_argument("--max-tokens", type=int, default=24000, help="Target max tokens (approx). Packet will shrink to fit.")
    parser.add_argument("--strip-comments", action="store_true", help="Drop full-line comments for known languages to save tokens.")
    parser.add_argument("--max-line-chars", type=int, default=1200, help="Trim very long lines to at most this many characters (0 disables).")
    parser.add_argument("--split-packets", type=int, default=1, help="If >1, split the context across N output packets to stay within limits.")
    args = parser.parse_args()

    files = [Path(f) for f in args.files if Path(f).exists() and Path(f).is_file() and not is_binary_or_ignored(Path(f))]
    files.extend(discover_files(args.dirs, args.include))
    files = sorted(set(files))

    if not files:
        raise SystemExit("No files found. Provide --files or --dirs with matching --include patterns.")

    def _adaptive_packet(fs: List[Path], out_path: Path) -> None:
        max_lines = int(args.max_lines)
        max_file_lines = int(args.max_file_lines)
        for _ in range(6):
            packet = build_packet(
                fs,
                args.focus,
                max_lines,
                max_file_lines,
                strip_comments=bool(args.strip_comments),
                max_line_chars=int(args.max_line_chars),
            )
            tokens = approx_tokens(packet)
            if tokens <= int(args.max_tokens):
                break
            ratio = max(1.1, float(tokens) / float(max(1, int(args.max_tokens))))
            max_lines = max(200, int(max_lines / ratio))
            max_file_lines = max(80, int(max_file_lines / ratio))
        else:
            max_lines = max(120, int(args.max_tokens // 6))
            max_file_lines = 80
            packet = build_packet(
                fs,
                args.focus,
                max_lines,
                max_file_lines,
                strip_comments=bool(args.strip_comments),
                max_line_chars=int(args.max_line_chars),
            )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(packet, encoding="utf-8")
        print(f"Wrote {out_path}")
        print(f"Approx tokens: {approx_tokens(packet)} (target <= {int(args.max_tokens)})")

    if int(args.split_packets) <= 1:
        out = Path(args.out)
        _adaptive_packet(files, out)
    else:
        n = int(args.split_packets)
        size = max(1, math.ceil(len(files) / n))
        base = Path(args.out)
        stem = base.stem
        suffix = base.suffix or ".md"
        for i in range(n):
            chunk = files[i * size : (i + 1) * size]
            if not chunk:
                break
            out = base.with_name(f"{stem}_{i+1}{suffix}")
            _adaptive_packet(chunk, out)
    print("Paste the generated markdown into a fresh Windsurf chat, not a long existing thread.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
