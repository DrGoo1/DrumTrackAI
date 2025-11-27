# 🎯 Run Phase 1 Test with Peg - Manual Instructions

**Backend is confirmed RUNNING** ✅ (tested at port 8000)

## Quick Run (Copy & Paste into PowerShell):

```powershell
cd f:\DrumTracKAI_v1.1.16_Clean
.\drumtrackai_env\Scripts\activate
python test_phase1_complete_workflow.py "f:\Audio_Test_Files\Peg_No_Drums.mp3"
```

## Or use the batch file:

**Open Command Prompt (not PowerShell) and run:**
```cmd
cd f:\DrumTracKAI_v1.1.16_Clean
run_peg_test.bat
```

## What the test will do:

1. ✅ Check backend health (ALREADY CONFIRMED WORKING)
2. ✅ List 10 drummers
3. ✅ Get Studio Groove Master details
4. ✅ Check Rust audio-core
5. 📤 Upload Peg_No_Drums.mp3
6. 🎵 Analyze tempo (should detect ~161 BPM)
7. 📊 Detect sections (should find ~7 sections)
8. 🥁 Generate drums with Jeff Porcaro style
9. 🎹 Validate MIDI notes

## Expected Results:

```
✓ Backend is healthy: {'ok': True, 'ts': ...}
✓ Found 10 drummers
✓ Loaded: Studio Groove Master
  Ghost notes: 0.75
  Swing comfort: 0.85
  Pocket mastery: 0.98
✓ Found Rust audio-core: audio-core/target/release/audio-core.exe
✓ File uploaded: uploads/peg_no_drums_xxx.mp3
✓ Tempo detected: 161.0 BPM (confidence: 0.85)
✓ Detected 7 sections
  1. Intro        0.0s - 10.5s  (conf: 0.90)
  2. Verse       10.5s - 28.3s  (conf: 0.88)
  3. Chorus      28.3s - 45.1s  (conf: 0.92)
  ...
✓ Generated 487 MIDI notes
  kick        142 notes
  snare       98 notes
  hihat       187 notes
  tom         34 notes
  ride        26 notes
✓ MIDI notes in correct format

TEST SUMMARY:
  Passed:   8 / 8
  Warnings: 0

Phase 1 is READY FOR PRODUCTION! 🎉
```

## Troubleshooting:

If test fails, check:
- Backend still running at http://localhost:8000
- Virtual environment activated
- Peg file exists at f:\Audio_Test_Files\Peg_No_Drums.mp3
- Sufficient disk space for upload

## What to do after test completes:

1. Review test output
2. Check for any warnings or failures
3. If all pass → Ready for Phase 2!
4. If failures → Document and we'll fix them
