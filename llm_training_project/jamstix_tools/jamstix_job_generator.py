import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path(__file__).parent
CATALOG_JSON = BASE_DIR / "jamstix_catalog.json"
PERSONA_SEED_JSON = BASE_DIR / "jamstix_persona_seed.json"
JOBS_JSONL = BASE_DIR / "jamstix_jobs.jsonl"

# Limits for initial dataset
MAX_PLAYERS = 10
MAX_STYLES = 25


@dataclass
class PersonaSeed:
    persona_id: str
    display_name: str
    jamstix_player_id: str
    jamstix_category: str
    jamstix_relative_path: str
    style_ids: List[str]


@dataclass
class JobSpec:
    job_id: str
    player_id: str
    style_id: str
    tempo_bpm: int
    bars: int
    variation_index: int


def load_catalog() -> Dict[str, Any]:
    if not CATALOG_JSON.exists():
        raise SystemExit(f"Catalog not found: {CATALOG_JSON}. Run jamstix_catalog_extractor.py first.")
    return json.loads(CATALOG_JSON.read_text(encoding="utf-8"))


def select_players(catalog: Dict[str, Any]) -> List[Dict[str, Any]]:
    players = catalog.get("players", [])
    # Simple, deterministic ordering: by category then name
    players_sorted = sorted(players, key=lambda p: (p.get("category", ""), p.get("name", "")))
    return players_sorted[:MAX_PLAYERS]


def select_styles(catalog: Dict[str, Any]) -> List[Dict[str, Any]]:
    styles = catalog.get("styles", [])
    # Prefer styles with some CGens/Accents info, then by category/name
    def score(style: Dict[str, Any]) -> tuple:
        accents = style.get("accents") or {}
        cg = style.get("groove_generators") or {}
        richness = len(accents) + len(cg)
        return (-richness, style.get("category", ""), style.get("name", ""))

    styles_sorted = sorted(styles, key=score)
    return styles_sorted[:MAX_STYLES]


def build_persona_seeds(players: List[Dict[str, Any]], styles: List[Dict[str, Any]]) -> List[PersonaSeed]:
    # For now, keep it simple: associate each player with all selected styles.
    # Later we can filter by compatible categories.
    style_ids = [s["id"] for s in styles]
    seeds: List[PersonaSeed] = []

    for p in players:
        pid = p["id"]  # e.g. "Rock/Phil"
        name = p.get("name") or pid.split("/", 1)[-1]
        category = p.get("category", "")
        rel_path = p.get("relative_path", "")
        persona_id = f"jamstix.{category}.{name}".replace(" ", "_")

        seeds.append(
            PersonaSeed(
                persona_id=persona_id,
                display_name=name,
                jamstix_player_id=pid,
                jamstix_category=category,
                jamstix_relative_path=rel_path,
                style_ids=style_ids,
            )
        )

    return seeds


def build_jobs(players: List[Dict[str, Any]], styles: List[Dict[str, Any]]) -> List[JobSpec]:
    tempos = [60, 80, 100, 120]
    bars = 16
    variations = [1, 2]  # keep small for now

    jobs: List[JobSpec] = []
    job_counter = 0

    for p in players:
        player_id = p["id"]
        for s in styles:
            style_id = s["id"]
            for tempo in tempos:
                for var in variations:
                    job_counter += 1
                    jobs.append(
                        JobSpec(
                            job_id=f"J{job_counter:05d}",
                            player_id=player_id,
                            style_id=style_id,
                            tempo_bpm=tempo,
                            bars=bars,
                            variation_index=var,
                        )
                    )

    return jobs


def main() -> None:
    catalog = load_catalog()

    players = select_players(catalog)
    styles = select_styles(catalog)

    persona_seeds = build_persona_seeds(players, styles)
    jobs = build_jobs(players, styles)

    # Write persona seeds
    PERSONA_SEED_JSON.write_text(
        json.dumps([asdict(p) for p in persona_seeds], indent=2),
        encoding="utf-8",
    )

    # Write jobs as JSONL for future automation / labeling
    with JOBS_JSONL.open("w", encoding="utf-8") as f:
        for j in jobs:
            f.write(json.dumps(asdict(j)) + "\n")

    print(f"Selected {len(players)} players and {len(styles)} styles.")
    print(f"Wrote persona seeds: {PERSONA_SEED_JSON}")
    print(f"Wrote jobs JSONL:   {JOBS_JSONL}")


if __name__ == "__main__":
    main()
