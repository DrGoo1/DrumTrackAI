# MVSEP‑Stem Groove Analysis and Drummer Persona Pipeline

This document describes the new analysis pipeline and tools that extract per‑instrument drum events from iconic grooves using MVSEP stems, compute groove style vectors, and aggregate them into drummer personas.

It is **admin‑only** plumbing used to build the drummer "brain" for DrumTracKAI. Nothing here is exposed to end users directly.

---

## 1. Data flow overview

High‑level flow:

1. **Groove archetype import**
   - Script: `admin/tools/import_groove_archetypes.py`
   - Reads WAV files under `DrumBeats/` and creates/updates rows in `groove_archetypes` with:
     - `archetype_id` (e.g. `rosanna`, `fool_in_the_rain`)
     - `song_title`
     - `drum_path` (isolated drum mix path)
     - `original_path` (full mix path, used as MVSEP input)

2. **MVSEP 2‑stage stem extraction (batch)**
   - Script: `admin/tools/extract_mvsep_stems_for_grooves.py`
   - Uses `admin/services/mvsep_service.py` (HDemucs + DrumSep) to produce stems for each archetype with a valid `original_path`.
   - Output structure (per archetype):
     - `admin/data/mvsep_grooves/<archetype_id>/drums.wav` (drum stem from HDemucs)
     - `admin/data/mvsep_grooves/<archetype_id>/drumsep_components/drumsep_*.wav`:
       - `drumsep_kick.wav`
       - `drumsep_snare.wav`
       - `drumsep_hh.wav`
       - `drumsep_ride.wav`
       - `drumsep_crash.wav`
       - `drumsep_toms.wav`
       - `drumsep_drums.wav`
       - `drumsep_residual.wav`

3. **Groove analysis (stems‑only)**
   - Script: `admin/tools/analyze_groove_archetypes.py`
   - Uses:
     - `admin/tools/groove_event_extractor.py` (audio ➜ per‑hit `GrooveEvent` list)
     - `admin/tools/groove_stem_analyzer.py` (per‑stem orchestration into instruments)
     - `admin/tools/groove_style_features.py` (events ➜ aggregate style metrics)
   - Populates DB tables:
     - `groove_events`: one row per hit (bar/step/time/instrument/velocity/timing offset/limb)
     - `groove_style_vectors`: one row per archetype with numeric style features.

4. **Drummer persona aggregation**
   - Script: `admin/tools/aggregate_groove_styles_to_drummer.py`
   - Aggregates `groove_style_vectors` across multiple archetypes to build a simple style summary for a public drummer persona.

5. **Inspection helpers**
   - `show_groove_style_vectors.py` – prints style vectors for selected archetypes.
   - `show_groove_event_counts.py` – prints per‑instrument hit counts per archetype.

---

## 2. Environment and DB configuration

### 2.1 Virtual environment

For all admin tools, use the project venv:

```powershell
cd F:\DrumTracKAI_v1.1.17
& F:/DrumTracKAI_v1.1.17/drumtrackai_env/Scripts/Activate.ps1
```

### 2.2 Admin DB path

The admin DB path is controlled by `DRUMTRACKAI_DB_PATH`:

```powershell
$Env:DRUMTRACKAI_DB_PATH = "F:\DrumTracKAI_v1.1.17\admin\drumtrackai.db"
```

If unset, tools default to `admin/drumtrackai.db` under the project root.

### 2.3 MVSEP API key

Batch stem extraction requires the MVSEP key:

```powershell
$Env:MVSEP_API_KEY = "YOUR_REAL_MVSEP_API_KEY"
```

Do **not** commit this key. Keep it in your local environment only.

---

## 3. MVSEP stem extraction for all grooves

Script: `admin/tools/extract_mvsep_stems_for_grooves.py`

Purpose:

- Iterate over `groove_archetypes`.
- For each row with a non‑null `original_path`, run the full MVSEP pipeline.
- Save stems under `admin/data/mvsep_grooves/<archetype_id>/...`.

Run:

```powershell
cd F:\DrumTracKAI_v1.1.17

& F:/DrumTracKAI_v1.1.17/drumtrackai_env/Scripts/Activate.ps1
$Env:DRUMTRACKAI_DB_PATH = "F:\DrumTracKAI_v1.1.17\admin\drumtrackai.db"
$Env:MVSEP_API_KEY = "YOUR_REAL_MVSEP_API_KEY"

python admin\tools\extract_mvsep_stems_for_grooves.py
```

You should see logs per archetype such as:

```text
=== Processing rosanna | rosanna ===
[          rosanna]   1% Initializing MVSep processing...
[          rosanna]  50% DrumSep: DrumSep: processing (0%)
[          rosanna] 100% Processing complete
```

Stems for a processed archetype live in:

```text
admin/data/mvsep_grooves/<archetype_id>/drumsep_components/drumsep_*.wav
```

---

## 4. Stem-aware groove event extraction

### 4.1 Stem analyzer wrapper

File: `admin/tools/groove_stem_analyzer.py`

Key pieces:

- `find_stems_for_archetype(archetype_id: str) -> Dict[str, str]`
  - Locates `drumsep_*.wav` files under `admin/data/mvsep_grooves/<archetype_id>/drumsep_components`.
  - Returns a mapping like `{ "kick": "/.../drumsep_kick.wav", "snare": "/.../drumsep_snare.wav", ... }`.

- `analyze_from_stems(cfg: GrooveConfig, archetype_id: str) -> List[GrooveEvent]`
  - For each stem (kick/snare/hh/ride/crash/toms/drums/residual):
    - Calls `GrooveAnalyzer.process_audio(path)`.
    - Overwrites `event.instrument` according to the stem key (e.g. `kick` ➜ `"kick"`, `hh` ➜ `"hat_closed"`).
  - Concatenates all per‑stem events and sorts by `time_sec`.

### 4.2 GrooveAnalyzer (audio ➜ events)

File: `admin/tools/groove_event_extractor.py`

Main elements:

- `GrooveConfig`: holds BPM, time signature, grid resolution, onset/velocity config.
- `_load_audio`:
  - Uses **only** `soundfile` + `numpy` (no librosa/numba/soxr).
  - Loads stereo WAV, converts to mono by averaging channels.
  - Warns if sample rate differs from the config target, but does not resample.
  - Normalizes audio to peak 1.0.
- `_detect_onsets`:
  - Simple amplitude‑envelope onset detector:
    - Computes rectified, smoothed energy envelope via moving average.
    - Uses first‑order difference and a statistical threshold.
    - Performs non‑max suppression in a small time window.
  - Returns an array of onset times in seconds.
- `_extract_snippet`, `_estimate_velocity`, `_quantize_time`:
  - Extract a small window around each onset.
  - Estimate velocity from peak dB within [velocity_min_db, velocity_max_db].
  - Quantize to bar/beat/subdivision based on BPM + time signature.
- `DrumClassifier`:
  - Currently using the DSP heuristic path (FFT + band energy + centroid) to classify:
    - `kick`, `snare`, `hat_closed`, `crash`, `tom1`, etc.
  - When driven from stems, the classifier’s label is overwritten by the stem’s known instrument for accuracy.

---

## 5. Stem‑only groove analysis for all archetypes

File: `admin/tools/analyze_groove_archetypes.py`

### 5.1 BPM map

`BPMS_BY_ARCHETYPE` is a manually curated map:

```python
BPMS_BY_ARCHETYPE = {
    "rosanna": 88.0,
    "fool_in_the_rain": 89.0,
    # ... etc for all 20 archetypes
}
```

### 5.2 Stem‑only analyze_one_groove

`analyze_one_groove` is now **stems‑only**:

- It never falls back to the `_drum.wav` mix.
- If stems are missing or analysis fails, the archetype is skipped.

Pseudocode:

```python
def analyze_one_groove(archetype_id, song_title, drum_path):
    print("Analyzing ...")

    bpm = BPMS_BY_ARCHETYPE.get(archetype_id)
    if bpm is None:
        warn and return [], {}

    cfg = GrooveConfig(bpm=bpm, time_signature=(4, 4), subdivisions_per_beat=4)

    try:
        events = analyze_from_stems(cfg, archetype_id)
        print(f"  Used MVSEP stems for {len(events)} events")
    except Exception as e:
        print("  WARNING: stem-based analysis failed or stems missing ...")
        print("  Skipping this archetype (no raw mix fallback).")
        return [], {}

    numeric_features, _ = GrooveFeatureExtractor(cfg).analyze(events)

    features = {
        "bpm": numeric_features.get("bpm"),
        "backbeat_late_ms": numeric_features.get("backbeat_mean_offset_ms"),
        "hat_open_ratio": numeric_features.get("hat_open_ratio"),
        "ghost_snare_ratio": numeric_features.get("ghost_snare_fraction"),
        "kick_density": numeric_features.get("kick_hits_per_bar"),
        "snare_density": numeric_features.get("snare_hits_per_bar"),
        "cymbal_density": numeric_features.get("cymbal_hits_per_bar"),
        "dynamics_spread": numeric_features.get("velocity_std"),
        "swing_amount": None,
        "shuffle_amount": None,
        "notes": None,
    }
    return events, features
```

### 5.3 Running the analysis

```powershell
cd F:\DrumTracKAI_v1.1.17

& F:/DrumTracKAI_v1.1.17/drumtrackai_env/Scripts/Activate.ps1
$Env:DRUMTRACKAI_DB_PATH = "F:\DrumTracKAI_v1.1.17\admin\drumtrackai.db"

python admin\tools\analyze_groove_archetypes.py
```

You should see for each archetype:

- Either:

  ```text
  Used MVSEP stems for N events
  ```

- Or (for missing stems):

  ```text
  WARNING: stem-based analysis failed or stems missing for <id>: No drumsep_components folder ...
  Skipping this archetype (no raw mix fallback).
  ```

At the end:

```text
Analysis pass complete.
```

---

## 6. Inspecting results

### 6.1 Groove style vectors

File: `show_groove_style_vectors.py`

Run:

```powershell
cd F:\DrumTracKAI_v1.1.17
python .\show_groove_style_vectors.py
```

Example output for shuffle grooves:

```text
== rosanna ==
  bpm: 88.0
  backbeat_late_ms: 4.45...
  hat_open_ratio: 0.0
  ghost_snare_ratio: 0.0
  kick_density: 8.5
  snare_density: 12.0
  cymbal_density: 31.125
  dynamics_spread: 14.73...

== fool_in_the_rain ==
  bpm: 89.0
  backbeat_late_ms: 10.97...
  hat_open_ratio: 0.0
  ghost_snare_ratio: 0.0
  kick_density: 11.14...
  snare_density: 12.14...
  cymbal_density: 17.57...
  dynamics_spread: 14.95...
```

These values are derived **only from MVSEP stems**.

### 6.2 Instrument hit counts

File: `show_groove_event_counts.py`

Run:

```powershell
cd F:\DrumTracKAI_v1.1.17
python .\show_groove_event_counts.py
```

Sample output:

```text
== rosanna | rosanna ==
  kick           :  ...
  snare          :  ...
  hat_closed     :  ...
  ride           :  ...
  crash          :  ...
  tom1           :  ...
```

This is useful to confirm that per‑stem orchestration is working as expected.

---

## 7. Aggregating grooves into drummer personas

File: `admin/tools/aggregate_groove_styles_to_drummer.py`

This script aggregates `groove_style_vectors` across a set of archetypes to produce a simple style summary for a public drummer persona.

### 7.1 Human‑readable summary

Example: build a combined "Porcaro shuffle" persona from `rosanna` and `fool_in_the_rain`:

```powershell
cd F:\DrumTracKAI_v1.1.17

python admin\tools\aggregate_groove_styles_to_drummer.py `
  "Porcaro_Shuffle_Persona" `
  rosanna `
  fool_in_the_rain
```

This prints:

- Per‑groove metrics for each archetype.
- An aggregated block:

```text
Aggregated drummer style (simple mean over grooves):
  bpm               : ...
  backbeat_late_ms  : ...
  hat_open_ratio    : ...
  ghost_snare_ratio : ...
  kick_density      : ...
  snare_density     : ...
  cymbal_density    : ...
  dynamics_spread   : ...
```

### 7.2 JSON output for programmatic use

Use `--json` to get a single JSON object suitable for ingestion into a brain table:

```powershell
cd F:\DrumTracKAI_v1.1.17

python admin\tools\aggregate_groove_styles_to_drummer.py `
  "Porcaro_Shuffle_Persona" `
  rosanna `
  fool_in_the_rain `
  --json
```

Sample shape:

```json
{
  "drummer_name": "Porcaro_Shuffle_Persona",
  "archetypes": ["rosanna", "fool_in_the_rain"],
  "aggregated_style": {
    "bpm": 88.5,
    "backbeat_late_ms": 7.7,
    "hat_open_ratio": 0.0,
    "ghost_snare_ratio": 0.0,
    "kick_density": 9.8,
    "snare_density": 12.1,
    "cymbal_density": 24.3,
    "dynamics_spread": 14.8
  }
}
```

You can map `aggregated_style` into `DrummerStyleVector` / `DrummerGenerationBrain` fields when wiring the drummer brain to Drum Creation.

---

## 8. Future work

- Refine onset detection (e.g. per‑instrument thresholds, triplet awareness for shuffles).
- Distinguish open/closed hats explicitly (hat_open_ratio is currently placeholder).
- Derive ghost_snare_ratio from per‑hit velocity distributions.
- Add DB tables / services to persist aggregated drummer personas and expose them via a read‑only API for the frontend drummer profile UI.
- Use these stem‑based vectors as LLM training material for describing drummer styles.
