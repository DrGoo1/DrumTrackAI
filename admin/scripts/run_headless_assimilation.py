import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from admin.services.youtube_llm_learning_service import YouTubeLLMLearningPipeline


def parse_args():
    p = argparse.ArgumentParser(description="Run headless YouTube assimilation pipeline")
    p.add_argument("--drummer", required=True, help="Drummer name, e.g. 'Buddy Rich'")
    p.add_argument("--style", default="rock", help="Style, e.g. rock, jazz, funk")
    p.add_argument("--max-videos", type=int, default=3, help="Max videos to process")
    p.add_argument("--quality-threshold", type=float, default=0.0, help="Min quality (0-1), 0 disables filter")
    p.add_argument("--start-training", action="store_true", help="Start LLM training after dataset build")
    p.add_argument("--ingest-to-drummerbrain", action="store_true", help="Ingest audio into DrummerBrain DB")
    p.add_argument("--drummerbrain-limit", type=int, default=0, help="Limit for DrummerBrain ingest (0=no limit)")
    p.add_argument("--urls", default="", help="Comma-separated YouTube URLs to use instead of search")
    return p.parse_args()


def main():
    args = parse_args()

    urls = [u.strip() for u in (args.urls or "").split(",") if u.strip()] or None

    pipeline = YouTubeLLMLearningPipeline()
    result = pipeline.run_complete_pipeline(
        drummer_name=args.drummer,
        style=args.style,
        max_videos=int(args.max_videos),
        start_training=bool(args.start_training),
        ingest_to_drummerbrain=bool(args.ingest_to_drummerbrain),
        drummerbrain_limit=int(args.drummerbrain_limit or 0),
        urls=urls,
        quality_threshold=float(args.quality_threshold or 0.0),
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
