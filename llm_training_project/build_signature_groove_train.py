#!/usr/bin/env python3
"""Build LLM training dataset from signature groove corpus.

Each example asks the model to pick/use the appropriate reference groove
(archetype_id) given a style profile, so the LLM learns how to utilize
these grooves for similar songs.
"""
import json
from pathlib import Path

# This file lives in: <repo_root>/llm_training_project/
# We want CORPUS_PATH to be: <repo_root>/llm_training_project/groove_corpus/llm_groove_corpus.jsonl
PROJECT_ROOT = Path(__file__).resolve().parent  # llm_training_project/
CORPUS_PATH = PROJECT_ROOT / "groove_corpus" / "llm_groove_corpus.jsonl"
OUT_PATH = PROJECT_ROOT / "training_datasets" / "signature_groove_train.jsonl"


def build_signature_groove_train() -> None:
    if not CORPUS_PATH.exists():
        print(f"❌ Corpus not found: {CORPUS_PATH}")
        return

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    num = 0
    with CORPUS_PATH.open("r", encoding="utf-8") as f_in, OUT_PATH.open(
        "w", encoding="utf-8"
    ) as f_out:
        for line in f_in:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)

            archetype_id = rec.get("archetype_id")
            song_title = rec.get("song_title")
            style = rec.get("style_features", {}) or {}

            # Build a compact natural-language-ish prompt that a general LLM can use
            # to learn how to select / reference this groove for similar songs.
            style_desc = {
                k: v
                for k, v in style.items()
                if v is not None
            }

            prompt = {
                "instruction": "Given this groove style profile, choose the best matching reference groove archetype to use for a similar song.",
                "style_profile": style_desc,
            }

            example = {
                "task": "signature_groove_selection",
                "input": json.dumps(prompt),
                "output": archetype_id,
                "meta": {
                    "source": "signature_groove_corpus",
                    "archetype_id": archetype_id,
                    "song_title": song_title,
                },
            }

            f_out.write(json.dumps(example))
            f_out.write("\n")
            num += 1

    print(f"Exported {num} signature groove training examples to {OUT_PATH}")


if __name__ == "__main__":
    build_signature_groove_train()
