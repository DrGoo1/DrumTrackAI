import json
import zlib
import configparser
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Any, List, Optional

# Adjusted for workspace copy of Jamstix
JAMSTIX_ROOT = Path(r"F:/DrumTracKAI_v1.1.17/Jamstix/Jamstix4").resolve()
DATA_DIR = JAMSTIX_ROOT / "data"

OUTPUT_DIR = Path(__file__).parent
CATALOG_JSON = OUTPUT_DIR / "jamstix_catalog.json"
PLAYERS_CSV = OUTPUT_DIR / "jamstix_players.csv"
STYLES_CSV = OUTPUT_DIR / "jamstix_styles.csv"
FILLS_CSV = OUTPUT_DIR / "jamstix_fills.csv"
STRUCTURES_JSON = OUTPUT_DIR / "jamstix_structures.json"


def maybe_decompress(raw: bytes) -> bytes:
    """Jamstix .jxp/.jxs/.j2d are typically zlib-compressed INI files."""
    if not raw:
        return raw
    # Many zlib streams start with 0x78
    if raw[0] == 0x78:
        try:
            return zlib.decompress(raw)
        except Exception:
            return raw
    return raw


def load_ini(path: Path) -> Optional[configparser.ConfigParser]:
    raw = path.read_bytes()
    data = maybe_decompress(raw)
    try:
        text = data.decode("latin-1", errors="ignore")
    except Exception:
        return None
    # Disable interpolation so Jamstix '%' sequences are treated as literals
    cfg = configparser.ConfigParser(interpolation=None)
    try:
        cfg.read_string(text)
    except Exception:
        return None
    return cfg


@dataclass
class PlayerEntry:
    id: str
    name: str
    category: str
    relative_path: str
    # Bar-length hint from [General]
    bar_nums: Optional[int] = None
    # Placeholder for future inventory/pack tags
    packs: Optional[str] = None
    # Full parsed INI sections so we can inspect per-module parameters
    sections: Dict[str, Any] | None = None


@dataclass
class StyleEntry:
    id: str
    name: str
    category: str
    relative_path: str
    info: str = ""
    accents: Dict[str, Any] | None = None
    groove_generators: Dict[str, Any] | None = None
    packs: Optional[str] = None
    # Optional full parsed sections for deeper analysis
    sections: Dict[str, Any] | None = None


@dataclass
class FillEntry:
    id: str
    category: str
    relative_path: str
    # Optional parsed sections (many fills are very compact but keep for completeness)
    sections: Dict[str, Any] | None = None


def collect_players() -> List[PlayerEntry]:
    players_dir = DATA_DIR / "players"
    entries: List[PlayerEntry] = []
    if not players_dir.exists():
        return entries

    for p in players_dir.rglob("*.jxp"):
        cfg = load_ini(p)
        rel = p.relative_to(JAMSTIX_ROOT).as_posix()
        category = p.parent.name
        if cfg is None:
            name = p.stem
            bar_nums = None
            sections: Dict[str, Any] | None = None
        else:
            name = cfg.get("General", "Name", fallback=p.stem)
            try:
                bar_nums = cfg.getint("General", "BarNums", fallback=None)
            except Exception:
                bar_nums = None
            # Capture all sections/parameters for this player
            sections = {section: dict(cfg.items(section)) for section in cfg.sections()}
        entry_id = f"{category}/{name}"
        entries.append(
            PlayerEntry(
                id=entry_id,
                name=name,
                category=category,
                relative_path=rel,
                bar_nums=bar_nums,
                packs=None,
                sections=sections,
            )
        )
    return entries


def collect_styles() -> List[StyleEntry]:
    styles_dir = DATA_DIR / "styles"
    entries: List[StyleEntry] = []
    if not styles_dir.exists():
        return entries

    for p in styles_dir.rglob("*.jxs"):
        cfg = load_ini(p)
        rel = p.relative_to(JAMSTIX_ROOT).as_posix()
        category = p.parent.name
        if cfg is None:
            name = p.stem
            info = ""
            accents = None
            cg = None
            sections = None
        else:
            name = cfg.get("General", "Name", fallback=p.stem)
            info = cfg.get("General", "Info", fallback="")
            accents = dict(cfg.items("Accents")) if cfg.has_section("Accents") else None
            cg = dict(cfg.items("CGens")) if cfg.has_section("CGens") else None
            sections = {section: dict(cfg.items(section)) for section in cfg.sections()}
        entry_id = f"{category}/{name}"
        entries.append(
            StyleEntry(
                id=entry_id,
                name=name,
                category=category,
                relative_path=rel,
                info=info,
                accents=accents,
                groove_generators=cg,
                packs=None,
                sections=sections,
            )
        )
    return entries


def collect_fills() -> List[FillEntry]:
    fills_dir = DATA_DIR / "fills"
    entries: List[FillEntry] = []
    if not fills_dir.exists():
        return entries

    for p in fills_dir.rglob("*.j2d"):
        cfg = load_ini(p)
        rel = p.relative_to(JAMSTIX_ROOT).as_posix()
        category = p.parent.name
        entry_id = f"{category}/{p.stem}"
        if cfg is None:
            sections = None
        else:
            sections = {section: dict(cfg.items(section)) for section in cfg.sections()}
        entries.append(
            FillEntry(
                id=entry_id,
                category=category,
                relative_path=rel,
                sections=sections,
            )
        )
    return entries


def collect_structures() -> Dict[str, Any]:
    """Parse structures.ini into a simple JSON-serializable dict.

    We don't attempt to deeply interpret all fields; just capture sections and keys
    so they can be inspected / used for tagging later.
    """
    ini_path = DATA_DIR / "structures.ini"
    if not ini_path.exists():
        return {}

    cfg = configparser.ConfigParser()
    try:
        cfg.read(ini_path, encoding="latin-1")
    except Exception:
        return {}

    result: Dict[str, Any] = {}
    for section in cfg.sections():
        result[section] = dict(cfg.items(section))
    return result


def write_csv(path: Path, rows: List[Dict[str, Any]], field_order: List[str]) -> None:
    if not rows:
        return
    import csv

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=field_order, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    if not JAMSTIX_ROOT.exists():
        raise SystemExit(f"JAMSTIX_ROOT does not exist: {JAMSTIX_ROOT}")

    players = collect_players()
    styles = collect_styles()
    fills = collect_fills()
    structures = collect_structures()

    catalog: Dict[str, Any] = {
        "jamstix_root": JAMSTIX_ROOT.as_posix(),
        "players": [asdict(p) for p in players],
        "styles": [asdict(s) for s in styles],
        "fills": [asdict(f) for f in fills],
        "structures": structures,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    CATALOG_JSON.write_text(json.dumps(catalog, indent=2), encoding="utf-8")

    write_csv(PLAYERS_CSV, [asdict(p) for p in players], [
        "id",
        "name",
        "category",
        "relative_path",
        "bar_nums",
        "packs",
    ])

    write_csv(STYLES_CSV, [asdict(s) for s in styles], [
        "id",
        "name",
        "category",
        "relative_path",
        "info",
        "packs",
    ])

    write_csv(FILLS_CSV, [asdict(f) for f in fills], [
        "id",
        "category",
        "relative_path",
    ])

    print(f"Wrote catalog JSON: {CATALOG_JSON}")
    print(f"Players CSV: {PLAYERS_CSV}")
    print(f"Styles CSV:  {STYLES_CSV}")
    print(f"Fills CSV:   {FILLS_CSV}")
    print(f"Structures JSON: {STRUCTURES_JSON}")


if __name__ == "__main__":
    main()
