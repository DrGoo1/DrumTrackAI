-- Direct Render Test - Render MIDI track output directly to WAV file
-- This is the simplest approach: MIDI → SD3 → WAV file

function msg(text)
    reaper.ShowConsoleMsg(text .. "\n")
end

function main()
    msg("=== DIRECT RENDER TEST ===")
    msg("Rendering Track 1 (SD3) output directly to WAV file")
    msg("=================================")
    
    -- Get track 1 (Superior Drummer 3)
    local track = reaper.GetTrack(0, 0)
    if not track then
        msg("ERROR: No Track 1 found")
        return
    end
    
    -- Clear any existing items
    reaper.SelectAllMediaItems(0, true)
    local item_count = reaper.CountSelectedMediaItems(0)
    for i = item_count - 1, 0, -1 do
        local item = reaper.GetSelectedMediaItem(0, i)
        if item then
            local item_track = reaper.GetMediaItem_Track(item)
            reaper.DeleteTrackMediaItem(item_track, item)
        end
    end
    
    -- Create MIDI item with china cymbal
    local item = reaper.CreateNewMIDIItemInProj(track, 1.3, 3.3, false)
    if not item then
        msg("ERROR: Failed to create MIDI item")
        return
    end
    
    local take = reaper.GetActiveTake(item)
    if not take then
        msg("ERROR: Failed to get MIDI take")
        return
    end
    
    -- Add china cymbal note (note 99)
    reaper.MIDI_InsertNote(take, false, false, 0, 960, 0, 99, 100, false)
    reaper.MIDI_Sort(take)
    
    msg("✓ Created china cymbal MIDI item")
    
    -- Set up render bounds (0 to 5 seconds to include pre-roll)
    reaper.GetSet_LoopTimeRange(true, false, 0, 5.0, false)
    
    -- Set render settings
    local output_file = "D:\\DrumTracKAI_v1.1.7\\admin\\sd3_extracted_samples\\test_china.wav"
    
    -- Clear any existing test file
    os.remove(output_file)
    
    msg("✓ Set render bounds: 0 to 5 seconds")
    msg("✓ Output file: test_china.wav")
    msg("")
    msg("MANUAL RENDER TEST:")
    msg("1. Go to File → Render")
    msg("2. Set output to: " .. output_file)
    msg("3. Make sure 'Time selection' is selected")
    msg("4. Click 'Render'")
    msg("5. Check if test_china.wav is created")
    msg("")
    msg("This will tell us if manual rendering works!")
    msg("If it works, we can automate it.")
    
    -- Update display
    reaper.UpdateArrange()
    
    -- Show render dialog
    msg("Opening render dialog...")
    reaper.Main_OnCommand(42230, 0)  -- File: Render project
end

main()
