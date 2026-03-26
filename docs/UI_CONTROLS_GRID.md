# UI Controls Grid
 
 This file is the canonical, git-reviewed control catalog.
 
 Evidence is written automatically by Playwright runs under:
 
 `frontend/test-results/ui-control-validation/<controlId>/evidence.json`
 
 Optional artifacts:
 
 - `frontend/test-results/ui-control-validation/<controlId>/screenshot.png`
 - Playwright trace/video files (when enabled) captured alongside `test-results`

| Control | UI Location | Hidden? | Designed Effect | How to Test (summary) | Verification Status | Evidence | Source |
|---|---|---|---|---|---|---|---|
| Style | Drum Builder / Generation panel | No | Select musical genre for generation | Change style, generate, confirm groove style changes but stays musical | Not yet |  | DRUM_BUILDER_COMPLETE_ARCHITECTURE.md |
| Drummer | Drum Builder / Generation panel | No | Select drummer profile/persona | Change drummer, generate, confirm feel changes (timing/vel) without corruption | Not yet | frontend/test-results/ui-control-validation/legacy_drummer_selection_groove_source_built_in/evidence.json | DRUM_BUILDER_COMPLETE_ARCHITECTURE.md |
| Intensity | Drum Builder / Generation panel | No | Increase/decrease overall energy/loudness | Increase, generate, confirm avg velocity and density increase within bounds | Not yet |  | DRUM_BUILDER_COMPLETE_ARCHITECTURE.md |
| Variation | Drum Builder / Generation panel | No | Increase pattern variation | Increase, generate twice, confirm higher structural variation without random glitches | Not yet |  | DRUM_BUILDER_COMPLETE_ARCHITECTURE.md |
| Generation Mode | Drum Builder / Generation panel | No | Choose pattern source (template/AI/etc.) | Switch modes, generate, confirm response metadata + musical output | Not yet |  | DRUM_BUILDER_COMPLETE_ARCHITECTURE.md |
| Humanize (toggle) | Drum Builder / Generation panel | No | Enable performance layer | Toggle off/on, generate, confirm microtiming=0 when off, nonzero when on | Not yet |  | DRUM_BUILDER_COMPLETE_ARCHITECTURE.md |
| Fill Type | Drum Builder / Generation panel (fills) | No | Choose fill style | Set fill type, generate, confirm fills appear at transitions and match type | Not yet |  | DRUM_BUILDER_COMPLETE_ARCHITECTURE.md |
| Fill Locations | Drum Builder / Generation panel (fills) | Sometimes | Choose where fills occur | Force fill locations, generate, confirm fills occur only in specified measures | Not yet |  | DRUM_BUILDER_COMPLETE_ARCHITECTURE.md |
| Measure Range | Section generation controls | No | Limit generation range | Change range, generate, confirm notes exist only in range | Not yet |  | DRUM_BUILDER_COMPLETE_ARCHITECTURE.md |
| Humanize Amount | Drum Builder / Performance controls | No | Scale micro-timing variance | Increase, generate, check microTimingMs distribution widens but stays within limits | Not yet |  | DRUM_BUILDER_COMPLETE_ARCHITECTURE.md |
| Ghost Note Amount | Drum Builder / Performance controls | No | Scale ghost note density | Increase, generate, confirm ghost count increases and velocities remain low | Not yet |  | DRUM_BUILDER_COMPLETE_ARCHITECTURE.md |
| Swing Amount | Drum Builder / Performance controls | No | Apply swing feel | Increase, generate, confirm offbeat timing shifts consistently | Not yet |  | DRUM_BUILDER_COMPLETE_ARCHITECTURE.md |
| Build Scope | Drum Builder / Toolbar | No | Full song vs selected section | Toggle, generate, confirm only target region changes and locks respected | Not yet |  | DRUM_BUILDER_COMPLETE_ARCHITECTURE.md |
| Guide Enabled | Drum Builder / Guide controls | Sometimes | Use guide track influence | Enable, generate, verify kick aligns with guide energy/accent without glitches | Not yet |  | DRUM_BUILDER_COMPLETE_ARCHITECTURE.md |
| Guide Instrument | Drum Builder / Guide controls | Yes (when Guide disabled) | Choose guide source | Enable guide, change instrument, generate, verify different influence | Not yet |  | DRUM_BUILDER_COMPLETE_ARCHITECTURE.md |
| Velocity (Volume) > Drums | Drum Options Panel > Velocity (Volume) | No | Master volume for kick/snare/toms | Raise/lower, apply/generate, verify drum velocities scale without clipping | Not yet |  | DrumOptionsPanel.tsx |
| Velocity (Volume) > Cymbals | Drum Options Panel > Velocity (Volume) | No | Master volume for hats/crash/ride | Raise/lower, verify cymbal velocities scale | Not yet |  | DrumOptionsPanel.tsx |
| Velocity (Volume) > Individual Instrument Volumes | Drum Options Panel > Velocity (Volume) details | Yes (collapsed by default) | Per-instrument velocity scaling | Change Kick/Snare/etc, verify only that instrument’s velocities change | Not yet |  | DrumOptionsPanel.tsx |
| Instrument Density (Complexity) > Drums | Drum Options Panel > Instrument Density (Complexity) | No | How busy drums are | Increase, verify drum note count increases but stays musical | Not yet |  | DrumOptionsPanel.tsx |
| Instrument Density (Complexity) > Cymbals | Drum Options Panel > Instrument Density (Complexity) | No | How busy cymbals are | Increase, verify cymbal note count increases | Not yet |  | DrumOptionsPanel.tsx |
| Individual Cymbal Density | Drum Options Panel > Instrument Density details | Yes (collapsed by default) | Per-cymbal density scaling | Change Hi-Hat/Ride/Crash density, verify only that lane changes | Not yet |  | DrumOptionsPanel.tsx |
| Fill Options > Fill Type | Drum Options Panel > Fill Options | No | Fill type preset | Change type, verify fill instrumentation changes | Not yet |  | DrumOptionsPanel.tsx |
| Fill Options > Fill Density | Drum Options Panel > Fill Options | No | Fill complexity | Increase, verify fill note density increases without absurd bursts | Not yet |  | DrumOptionsPanel.tsx |
| Fill Options > Fill Location | Drum Options Panel > Fill Options | No | Fill placement in measure | Change location, verify fill notes move accordingly | Not yet |  | DrumOptionsPanel.tsx |
| Fill Options > Fill Frequency | Drum Options Panel > Fill Options | No | How often fills occur | Change, verify fills at expected periodicity | Not yet |  | DrumOptionsPanel.tsx |
| Groove Options > Swing Preset | Drum Options Panel > Groove Options | No | Coarse swing preset | Change, verify timing feel changes | Not yet |  | DrumOptionsPanel.tsx |
| Groove Options > Fine Swing Amount | Drum Options Panel > Groove Options | No | Fine swing adjustment | Change, verify incremental timing shifts | Not yet |  | DrumOptionsPanel.tsx |
| Groove Options > Velocity Pattern | Drum Options Panel > Groove Options | No | Accent/velocity pattern | Change, verify velocity distribution changes predictably | Not yet |  | DrumOptionsPanel.tsx |
| Hi-Hat Articulation > Presets | Drum Options Panel > Hi-Hat Articulation | No | Set hat pattern/open ratio/complexity | Click preset, verify hat articulation distribution changes | Not yet |  | DrumOptionsPanel.tsx |
| Hi-Hat Complexity | Drum Options Panel > Hi-Hat Articulation | No | Adds embellishments | Increase, verify more hat subdivisions without timing errors | Not yet |  | DrumOptionsPanel.tsx |
| Hi-Hat Pattern | Drum Options Panel > Hi-Hat Articulation | No | Select hat sticking logic | Change pattern, verify phrasing changes | Not yet |  | DrumOptionsPanel.tsx |
| Hi-Hat Open Ratio | Drum Options Panel > Hi-Hat Articulation | No | Closed vs open mix | Increase, verify more open hat articulations | Not yet |  | DrumOptionsPanel.tsx |
| Hi-Hat Ghost Notes | Drum Options Panel > Hi-Hat Articulation | No | Feathered strokes | Increase, verify low-velocity hat notes appear between pulses | Not yet |  | DrumOptionsPanel.tsx |
| Ride Cymbal Dynamics > Presets | Drum Options Panel > Ride Cymbal Dynamics | No | Set ride pattern/bell/mix | Click preset, verify ride/bell usage changes | Not yet |  | DrumOptionsPanel.tsx |
| Ride Complexity | Drum Options Panel > Ride Cymbal Dynamics | No | Syncopation/skip beats | Increase, verify more ride activity without chaos | Not yet |  | DrumOptionsPanel.tsx |
| Ride Pattern | Drum Options Panel > Ride Cymbal Dynamics | No | Ride phrasing style | Change, verify ride phrasing changes | Not yet |  | DrumOptionsPanel.tsx |
| Ride vs Hat | Drum Options Panel > Ride Cymbal Dynamics | No | Crossfade ride vs hat timekeeping | Increase, verify ride replaces hat progressively | Not yet |  | DrumOptionsPanel.tsx |
| Bell Ratio | Drum Options Panel > Ride Cymbal Dynamics | No | Bell vs bow strikes | Increase, verify more bell articulations | Not yet |  | DrumOptionsPanel.tsx |
| Low-End Lock > Bass Line Mode | Drum Options Panel > Low-End Lock | No | Kick-bass relationship mode | Change, verify kick aligns/complements bass differently | Not yet |  | DrumOptionsPanel.tsx |
| Low-End Lock > Kick-Bass Sync | Drum Options Panel > Low-End Lock | No | Strength of kick locking to bass accents | Increase, verify more kick hits coincide with bass accents | Not yet |  | DrumOptionsPanel.tsx |
| Low-End Lock > Lock Kick to Bass Downbeats | Drum Options Panel > Low-End Lock | No | Force downbeat alignment | Enable, verify downbeat kick consistency | Not yet |  | DrumOptionsPanel.tsx |
| Additional Controls > Tom Usage | Drum Options Panel > Additional Controls | No | Tom frequency | Increase, verify more tom notes, no instrument errors | Not yet |  | DrumOptionsPanel.tsx |
| Additional Controls > Crash Frequency | Drum Options Panel > Additional Controls | No | Crash usage | Increase, verify more crashes at transitions | Not yet |  | DrumOptionsPanel.tsx |
| Additional Controls > Ghost Note Density | Drum Options Panel > Additional Controls | No | Ghost note density | Increase, verify more ghost notes w/ low velocity | Not yet |  | DrumOptionsPanel.tsx |
| Additional Controls > Dynamic Range | Drum Options Panel > Additional Controls | No | Soft vs loud contrast | Increase, verify velocity range widens without clipping | Not yet |  | DrumOptionsPanel.tsx |
| Drum Performance Editor > View filter (ALL/GROOVE/ACCENT/FILL) | Drum Performance Editor toolbar | No | Filter visible notes by aspect | Toggle filters, confirm only matching aspects shown | Not yet |  | error-context snapshots / UI |
| Drum Performance Editor > Grid resolution (16th/32nd/64th) | Drum Performance Editor toolbar | No | Change quantization grid for editing | Switch, confirm snapping and grid lines change | Not yet |  | error-context snapshots / UI |
| Note Inspector > Velocity | Note Inspector panel | No | Adjust selected note velocities | Edit value, confirm only selected notes’ velocities change | Not yet |  | INTEGRATION_READY_CHECKLIST.md |
| Note Inspector > Timing Offset | Note Inspector panel | No | Adjust per-note timing | Edit, confirm micro timing changes without breaking order | Not yet |  | INTEGRATION_READY_CHECKLIST.md |
| Note Inspector > Hat Open Level | Note Inspector panel | Contextual | Adjust hat openness | Change, confirm articulation/CC mapping updates | Not yet |  | INTEGRATION_READY_CHECKLIST.md |
| Note Inspector > Limb | Note Inspector panel | No | Assign limbId | Change, confirm limbId changes only | Not yet |  | INTEGRATION_READY_CHECKLIST.md |
| Note Inspector > Hit Style | Note Inspector panel | No | Single/double/bounce etc. | Change, confirm hitStyle changes only | Not yet |  | INTEGRATION_READY_CHECKLIST.md |
| Note Inspector > Lock | Note Inspector panel | No | Prevent regeneration overwriting | Lock, regenerate, verify locked notes/section preserved | Not yet |  | INTEGRATION_READY_CHECKLIST.md |
| Note Inspector > Flags (ghost/accent/flam/drag) | Note Inspector panel | No | Toggle flags | Toggle, confirm flag changes and UI reflects it | Not yet |  | INTEGRATION_READY_CHECKLIST.md |

| DCSM Drum Editor > Generate Groove | DCSM DAW > Drum Editor panel header | No | Calls `/dcsm/generate` and populates the drums clip | Click, wait for notes to appear in DrumGrid and for no console/network errors | Not yet |  | USER_MANUAL.md |
| DrumGrid > Select notes | DCSM DAW > DrumGrid canvas | No | Select single/multi notes for editing | Click/drag select, confirm selection count + inspector appears | Not yet |  | USER_MANUAL.md |
| DrumGrid > Move notes | DCSM DAW > DrumGrid canvas | No | Move notes in time or change lane | Drag, confirm tick/lane changes only (no unintended deletions) | Not yet |  | USER_MANUAL.md |
| DrumGrid > Resize notes | DCSM DAW > DrumGrid canvas | No | Change note duration | Drag edges, confirm `t1-t0` changes only | Not yet |  | USER_MANUAL.md |
| DrumGrid > Velocity lane visibility | Legacy DrumGrid editor | No | Toggle velocity lane render | Toggle show/hide velocity lane; confirm lane appears/disappears without affecting notes | Not yet |  | frontend/src/midi/ui/DrumGrid.tsx |
| DrumGrid > Quantization setting | Legacy DrumGrid editor | No | Set note quantization grid | Change quantization, add notes, verify start ticks snap accordingly | Not yet |  | frontend/src/midi/ui/DrumGrid.tsx |

| Drum Performance Editor > View filter (ALL/GROOVE/ACCENT/FILL) | Drum Performance Editor toolbar | No | Filter visible notes by aspect | Toggle, confirm only matching aspects shown | Not yet |  | frontend/src/components/drums/DrumEditorPane.tsx |
| Drum Performance Editor > Grid resolution (16th/32nd/64th) | Drum Performance Editor toolbar | No | Set edit snap grid | Switch, confirm snapping/grid lines change | Not yet |  | frontend/src/components/drums/DrumEditorPane.tsx |

| Note Inspector > Nudge earlier/later (grid step) | Note Inspector panel | Yes (requires gridResolution + handler) | Move selected notes by one grid step | Click +/- buttons, confirm ticks shift by expected step | Not yet |  | frontend/src/components/drums/NoteInspector.tsx |
| Note Inspector > Priority | Note Inspector panel | No | Adjust conflict resolution priority | Change slider, confirm `priority` updates only | Not yet |  | frontend/src/components/drums/NoteInspector.tsx |
| Note Inspector > Timing Offset (ms) | Note Inspector panel | No | Adjust per-note micro timing | Change, confirm `timingOffsetMs` updates only | Not yet |  | frontend/src/components/drums/NoteInspector.tsx |
| Note Inspector > Close (×) | Note Inspector panel header | No | Close inspector UI | Click ×, confirm inspector hides but selection clears only | Not yet |  | frontend/src/components/drums/NoteInspector.tsx |

| Re-Humanize > Preset buttons | Re-Humanize panel | No | Apply preset feel parameters | Click preset, Apply, confirm microtiming/velocity distribution changes | Not yet |  | frontend/src/components/RehumanizePanel.tsx |
| Re-Humanize > Micro-Timing slider | Re-Humanize panel | No | Scale micro-timing randomness | Adjust, Apply, confirm `microTimingMs` deltas scale | Not yet |  | frontend/src/components/RehumanizePanel.tsx |
| Re-Humanize > Feel (Tight/Loose) slider | Re-Humanize panel | No | Push/pull feel around beat | Adjust, Apply, confirm timing bias shifts | Not yet |  | frontend/src/components/RehumanizePanel.tsx |
| Re-Humanize > Velocity Variation slider | Re-Humanize panel | No | Scale velocity variance | Adjust, Apply, confirm velocity variance changes | Not yet |  | frontend/src/components/RehumanizePanel.tsx |
| Re-Humanize > Swing slider | Re-Humanize panel | No | Apply swing feel client-side | Adjust, Apply, confirm offbeats shift | Not yet |  | frontend/src/components/RehumanizePanel.tsx |
| Re-Humanize > Ghost Note Density slider | Re-Humanize panel | No | Add/scale ghost note density client-side | Adjust, Apply, confirm ghost notes/flags/vels change as designed | Not yet |  | frontend/src/components/RehumanizePanel.tsx |
| Re-Humanize > Show/Hide Groove Controls | Re-Humanize panel | No | Toggle advanced groove controls UI | Toggle, confirm LaidBack/Pocket controls appear/disappear | Not yet |  | frontend/src/components/RehumanizePanel.tsx |
| Re-Humanize > Groove: Laid Back / Pushed | Re-Humanize panel (advanced) | Yes (collapsed by default) | Bias timing later/earlier | Adjust, Apply, confirm consistent timing bias | Not yet |  | frontend/src/components/RehumanizePanel.tsx |
| Re-Humanize > Groove: Pocket Depth | Re-Humanize panel (advanced) | Yes (collapsed by default) | Increase groove depth effect | Adjust, Apply, confirm stronger groove timing/velocity shaping | Not yet |  | frontend/src/components/RehumanizePanel.tsx |
| Re-Humanize > Apply | Re-Humanize panel | No | Apply changes to selection or whole track | Click, confirm track updates immediately and no network call occurs | Not yet |  | frontend/src/components/RehumanizePanel.tsx |
| Re-Humanize > Reset | Re-Humanize panel | No | Restore original track snapshot | Click, confirm prior track state restored | Not yet |  | frontend/src/components/RehumanizePanel.tsx |

| Musical Arrangement > Expand/Collapse | Musical Arrangement panel header | No | Show/hide section list | Click chevron area, confirm panel expands/collapses | Not yet |  | frontend/src/components/SectionControls.tsx |
| Musical Arrangement > Add Section | Musical Arrangement panel | No | Create new manual section at playhead | Click, confirm new section inserted and selectable | Not yet |  | frontend/src/components/SectionControls.tsx |
| Musical Arrangement > Select Section | Musical Arrangement panel list | No | Set current/active section in UI | Click section row, confirm selection highlight changes | Not yet |  | frontend/src/components/SectionControls.tsx |
| Musical Arrangement > Rename Section | Musical Arrangement panel list | No | Rename section label | Click ✏️, edit, Enter/blur, confirm label updates | Not yet |  | frontend/src/components/SectionControls.tsx |
| Musical Arrangement > Delete Section | Musical Arrangement panel list | No | Remove a section from arrangement | Click 🗑️, confirm prompt, verify section removed (not last section) | Not yet |  | frontend/src/components/SectionControls.tsx |

| Manual Arrangement Entry > Global Tempo (BPM) | Manual Arrangement Entry modal | No | Set global tempo for manual arrangement | Change value, Apply Arrangement, confirm tempo propagates | Not yet |  | frontend/src/components/ManualArrangementModal.tsx |
| Manual Arrangement Entry > Time Signature (numerator) | Manual Arrangement Entry modal | No | Set beats per bar | Change, Apply Arrangement, confirm time signature changes | Not yet |  | frontend/src/components/ManualArrangementModal.tsx |
| Manual Arrangement Entry > Time Signature (denominator) | Manual Arrangement Entry modal | No | Set beat unit | Change, Apply Arrangement, confirm time signature changes | Not yet |  | frontend/src/components/ManualArrangementModal.tsx |
| Manual Arrangement Entry > Add Section | Manual Arrangement Entry modal | No | Add a song section definition | Click + Add Section, confirm new section row appears | Not yet |  | frontend/src/components/ManualArrangementModal.tsx |
| Manual Arrangement Entry > Section Type dropdown | Manual Arrangement Entry modal | No | Set section label/type | Change dropdown, Apply, verify section type stored | Not yet |  | frontend/src/components/ManualArrangementModal.tsx |
| Manual Arrangement Entry > Start Measure | Manual Arrangement Entry modal | No | Set section start measure | Change, verify calculated time updates and arrangement applies | Not yet |  | frontend/src/components/ManualArrangementModal.tsx |
| Manual Arrangement Entry > # Measures | Manual Arrangement Entry modal | No | Set section length | Change, verify calculated time updates and arrangement applies | Not yet |  | frontend/src/components/ManualArrangementModal.tsx |
| Manual Arrangement Entry > Different tempo for this section | Manual Arrangement Entry modal | No | Enable per-section tempo override | Toggle, set BPM, Apply, verify override stored | Not yet |  | frontend/src/components/ManualArrangementModal.tsx |
| Manual Arrangement Entry > Import MIDI Tempo Map (.mid/.midi) | Manual Arrangement Entry modal | No | Select MIDI file for tempo-map import | Choose MIDI file, confirm selection accepted (parsing TODO) | Not yet |  | frontend/src/components/ManualArrangementModal.tsx |
| Manual Arrangement Entry > Cancel | Manual Arrangement Entry modal | No | Close modal without changes | Click Cancel, confirm no arrangement changes | Not yet |  | frontend/src/components/ManualArrangementModal.tsx |
| Manual Arrangement Entry > Apply Arrangement | Manual Arrangement Entry modal | No | Commit manual arrangement | Click Apply, confirm arrangement applied | Not yet |  | frontend/src/components/ManualArrangementModal.tsx |

| Export > Open Export dialog | DCSM DAW toolbar | No | Opens export options | Click Export, confirm dialog opens | Not yet |  | USER_MANUAL.md |
| Export > Mode: Stereo mixdown | Export dialog | No | Queue stereo audio export | Select mode, run export, confirm backend job queued and file produced | Not yet |  | USER_MANUAL.md |
| Export > Mode: Stems (multi-track) | Export dialog | No | Queue stem exports | Select mode, run export, confirm stems produced | Not yet |  | USER_MANUAL.md |
| Export > Mode: Drums MIDI (articulated, plugin-specific) | Export dialog | No | Export MIDI with articulations mapped to plugin | Select mode, pick plugin, export, confirm `.mid` downloaded | Not yet |  | USER_MANUAL.md |
| Export > Target plugin (Jamstix/SD3/SSD5) | Export dialog | Contextual | Select articulation map target | Change plugin, export, confirm MIDI keyswitch/CC mapping matches selected target | Not yet |  | USER_MANUAL.md |

| V3 Drummer Picker > Open/Close modal | V3 UI | No | Toggle drummer picker modal | Open, confirm list loads; close, confirm returns to UI | Not yet |  | frontend/src/components/v3/V3DrummerPickerModal.tsx |
| V3 Drummer Picker > Select drummer card | V3 Drummer Picker modal | No | Set global/section drummer and auto-apply default preset stack | Select drummer, confirm defaults update and auto-generation triggers | Not yet |  | frontend/src/components/v3/V3DrummerPickerModal.tsx |
| V3 Drummer Picker > Select preset per drummer (tiered) | V3 Drummer Picker modal | Yes (depends on preset availability) | Apply a specific preset (song/flavor/utility) | Pick preset, select drummer, confirm preset stored/applied | Not yet |  | frontend/src/components/v3/V3DrummerPickerModal.tsx |
