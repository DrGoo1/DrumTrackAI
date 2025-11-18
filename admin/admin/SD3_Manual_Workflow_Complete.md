# Superior Drummer 3 Manual Extraction Workflow

## Complete Step-by-Step Process for MIDI to WAV Extraction

### Overview
This document provides the exact manual steps to extract audio from Superior Drummer 3 MIDI patterns, based on the user's specified workflow.

### Prerequisites
- Superior Drummer 3 is installed and running
- MIDI files are located at: `H:\DrumTracKAI_v1.1.7\admin\sd3_midi_patterns\`
- Output directory exists: `H:\DrumTracKAI_v1.1.7\admin\sd3_extracted_samples\`

### Files to Process
Total: 579 MIDI files covering:
- China cymbals (hard, medium, soft)
- Crash cymbals (1 & 2, various velocities)
- Hi-hat variations (closed, open, semi-open, pedal, splash, tight)
- Kick drum (center, edge - hard/medium/soft)
- Ride cymbal (bell, bow, crash, edge, shoulder, tip)
- Snare drum (buzz, center, cross stick, ghost, rim shot)
- Splash cymbals
- Toms (floor, high, mid - various velocities)

---

## Manual Workflow Steps

### Step 1: Load MIDI File
1. **Focus Superior Drummer 3 window**
   - Click on SD3 window to make it active
   - Ensure SD3 is responsive

2. **Open File Dialog**
   - Press `Ctrl+O` to open file dialog
   - Navigate to: `H:\DrumTracKAI_v1.1.7\admin\sd3_midi_patterns\`
   - Select desired MIDI file (e.g., `china_china_hard_053.mid`)
   - Press `Enter` to load

3. **Verify MIDI Loaded**
   - Check that MIDI appears in timeline
   - Verify instrument/pattern is visible

### Step 2: Position Timeline at Beat 1.3
**CRITICAL**: MIDI must start at beat 1.3 for proper export

1. **Go to Beginning**
   - Press `Home` key to move cursor to start (beat 1.1)

2. **Move to Beat 1.3**
   - Press `Right Arrow` key 3 times to reach beat 1.3
   - OR manually click on timeline at beat 1.3 position
   - Verify cursor is positioned at beat 1.3

### Step 3: Open Track Menu → Bounce
**CRITICAL**: Must select BOUNCE, not RECORD

1. **Open Track Menu**
   - Press `Alt+T` to open Track menu
   - OR click on "Track" in menu bar

2. **Select Bounce**
   - Press `B` for Bounce option
   - OR click on "Bounce" in Track menu
   - **Verify**: Bounce dialog opens (NOT recording dialog)

### Step 4: Configure Bounce Settings
1. **Navigate to Advanced Tab**
   - Click on "Advanced" tab in bounce dialog
   - OR use Tab key to navigate to Advanced settings

2. **Select Bounce Output Channels**
   - Find "bounce output channels" radio button
   - Select this option to ensure 1 stereo file output
   - **Verify**: Setting shows single stereo output

### Step 5: Set Output Folder and Start Bounce
1. **Set Output Directory**
   - In file path field, enter: `H:\DrumTracKAI_v1.1.7\admin\sd3_extracted_samples\`
   - OR browse to select the output folder

2. **Start Bounce Process**
   - Press `Enter` or click "OK" to start bounce
   - **According to user**: Folder selection triggers the bounce

3. **Monitor Bounce Progress**
   - Watch for bounce progress indicator
   - Wait for completion notification

### Step 6: Wait for Bounce Completion
1. **Monitor Output Folder**
   - Check `H:\DrumTracKAI_v1.1.7\admin\sd3_extracted_samples\` folder
   - Look for file named `Out_1+2.wav`

2. **Verify File Creation**
   - Confirm `Out_1+2.wav` exists and has size > 0 bytes
   - File should contain the bounced audio

### Step 7: Rename Output File
1. **Extract Instrument Name**
   - From MIDI filename: `china_china_hard_053.mid`
   - Remove numeric suffix: `china_china_hard`

2. **Rename File**
   - Rename `Out_1+2.wav` to `china_china_hard.wav`
   - Use Windows Explorer or command line

---

## Batch Processing Strategy

### For Processing All 579 Files:

1. **Create Processing List**
   - List all MIDI files in order
   - Track progress (completed vs remaining)

2. **Systematic Processing**
   - Process files in alphabetical order
   - Check for existing output files to avoid duplicates
   - Log successful and failed extractions

3. **Quality Control**
   - Verify each output file has reasonable size
   - Spot-check audio quality
   - Maintain extraction log

---

## Common Issues and Solutions

### Issue: Recording Starts Instead of Bounce
- **Cause**: Wrong menu selection or key combination
- **Solution**: Ensure Track menu → Bounce (not Record)
- **Verify**: Bounce dialog should show export options, not recording controls

### Issue: Output File Not Created
- **Cause**: Bounce settings incorrect or path invalid
- **Solution**: Check Advanced settings for "bounce output channels"
- **Verify**: Output directory exists and is writable

### Issue: Timeline Not at Beat 1.3
- **Cause**: Cursor positioning incorrect
- **Solution**: Use Home key, then Right arrow 3 times
- **Verify**: Visual confirmation of cursor position

### Issue: MIDI File Not Loading
- **Cause**: File path incorrect or SD3 not focused
- **Solution**: Verify full path and SD3 window focus
- **Verify**: MIDI pattern appears in timeline

---

## Automation Considerations

### Why Direct Automation Failed:
1. **Window Focus Issues**: pyautogui couldn't properly focus SD3 window
2. **Key Event Blocking**: SD3 may not receive automated key presses
3. **Timing Issues**: Commands sent too quickly for SD3 to process

### Alternative Automation Approaches:
1. **Manual with Scripted Helpers**: User performs actions, scripts handle file management
2. **Clipboard Automation**: Use clipboard for file paths
3. **File System Monitoring**: Watch for output files and auto-rename
4. **Batch File Generation**: Create batch scripts for repetitive tasks

---

## File Naming Convention

### Input Files:
- Format: `instrument_component_articulation_velocity_number.mid`
- Example: `china_china_hard_053.mid`

### Output Files:
- Format: `instrument_component_articulation_velocity.wav`
- Example: `china_china_hard.wav`

### Extraction Rules:
- Remove numeric suffix from MIDI filename
- Keep instrument, component, articulation, and velocity information
- Use consistent naming for database organization

---

## Expected Results

### After Complete Processing:
- **579 WAV files** extracted from SD3
- **Organized by instrument type** and articulation
- **Consistent naming convention** for database integration
- **Complete extraction log** with success/failure tracking
- **Audio samples ready** for DrumTracKAI training and analysis

---

## Next Steps

1. **Manual Test**: Process 3-5 files manually to verify workflow
2. **Identify Bottlenecks**: Note which steps are most time-consuming
3. **Develop Helpers**: Create scripts for file management and renaming
4. **Scale Up**: Process all 579 files systematically
5. **Quality Assurance**: Verify all extractions are successful
6. **Database Integration**: Import samples into DrumTracKAI system
