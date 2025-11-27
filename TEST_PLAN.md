# DrumTracKAI Test Plan Checklist

Use this checklist to validate the DCSM DAW, articulation flow, and plugin-specific export.

Legend: `[ ]` = not run, `[x]` = passed, `[-]` = failed/needs work.

| ID   | Area                      | Test Description                                                                                   | Status | Date | Notes |
|------|---------------------------|----------------------------------------------------------------------------------------------------|--------|------|-------|
| T-1  | Backend / Startup         | Backend boots without errors; `/healthz` returns `{ ok: true }`.                                  | [ ]    |      |       |
| T-2  | Backend / Rust Core       | `/bench/generate?bpm=120&bars=4&style=rock` returns `rust_ms` and `notes` without `rust_error`.   | [ ]    |      |       |
| T-3  | Frontend / Startup        | `npm start` loads WebDAW/DCSM without console errors.                                             | [ ]    |      |       |
| T-4  | Analysis / Upload         | Audio upload works; waveform appears on timeline.                                                 | [ ]    |      |       |
| T-5  | Analysis / Tempo          | Tempo/onset analysis works; beats/onsets appear where expected.                                   | [ ]    |      |       |
| T-6  | Analysis / Sectionize     | Sectionization (simple or smart) produces reasonable song sections on the timeline.              | [ ]    |      |       |
| T-7  | DCSM / Drum Editor        | Drum Editor panel appears under Mixer in DCSM DAW.                                                | [ ]    |      |       |
| T-8  | DCSM / Default MIDI       | A `drums` track and `Main Groove` clip are auto-created (or existing drums track is reused).      | [ ]    |      |       |
| T-9  | DCSM / Generate Groove    | Clicking **Generate Groove** fills the current drums clip with notes (no errors).                | [ ]    |      |       |
| T-10 | DCSM / Timing             | Generated notes line up sensibly in DrumGrid (correct bar range, no absurd lengths).             | [ ]    |      |       |
| T-11 | Articulation / Backend    | `/dcsm/generate` response includes `articulationId` for hats/ride/snare/toms/crashes.            | [ ]    |      |       |
| T-12 | Articulation / Grid UI    | DrumGrid shows H/R/S/T/C labels on notes with articulation IDs; unlabeled notes still editable.  | [ ]    |      |       |
| T-13 | Articulation / Inspector  | Selecting a note updates the inspector; dropdown options match the instrument family.            | [ ]    |      |       |
| T-14 | Articulation / Single Edit| Changing one note's articulation updates its `articulationId` only (timing/vel unchanged).       | [ ]    |      |       |
| T-15 | Articulation / Multi Edit | Changing articulation with multiple notes selected updates all of them correctly.                | [ ]    |      |       |
| T-16 | Export / Modes            | Export dialog shows **Stereo**, **Stems**, **Drums MIDI (articulated, plugin-specific)** modes.  | [ ]    |      |       |
| T-17 | Export / MIDI Mode UI     | Drums MIDI mode shows plugin dropdown (Jamstix/SD3/SSD5) and helper text.                        | [ ]    |      |       |
| T-18 | Export / No Drums Clip    | With no drums clip, Drums MIDI export shows a friendly error (no crash).                         | [ ]    |      |       |
| T-19 | Export / API Payload      | Drums MIDI export posts to `/dcsm/export_midi` with `plugin`, `ppq`, and notes + `articulationId`.| [ ]    |      |       |
| T-20 | Export / Download         | Successful export downloads a `.mid` file with expected filename.                                | [ ]    |      |       |
| T-21 | Plugin / Jamstix          | Jamstix-target MIDI plays correctly (hats, ride, snare articulations behave as mapped).          | [ ]    |      |       |
| T-22 | Plugin / SD3              | SD3-target MIDI plays correctly with stock SD3 mapping and articulations.                        | [ ]    |      |       |
| T-23 | Plugin / SSD5             | SSD5-target MIDI plays correctly with SSD5 mapping and articulations.                            | [ ]    |      |       |
| T-24 | Docs / User Manual        | `USER_MANUAL.md` steps can be followed exactly in the UI without contradiction.                  | [ ]    |      |       |
| T-25 | Docs / Admin Guide        | Endpoints and config paths in `ADMIN_GUIDE.md` match the running system.                         | [ ]    |      |       |
| T-26 | Docs / Technical Design   | Module responsibilities in `TECHNICAL_DESIGN.md` match actual implementation.                    | [ ]    |      |       |
| T-27 | Regression / Legacy UI    | Legacy WebDAW / non-DCSM flows still work; no crashes due to `articulationId` being optional.    | [ ]    |      |       |
| T-28 | Error Handling            | Stopping backend then using Generate/Export shows clean error messages, no unhandled exceptions. | [ ]    |      |       |
