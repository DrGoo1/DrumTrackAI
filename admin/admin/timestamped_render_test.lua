-- Timestamped Render Test - Uses unique filename to verify rendering
-- This will create a file with timestamp so we know if it's new

function msg(text)
    reaper.ShowConsoleMsg(text .. "\n")
end

function main()
    msg("=== TIMESTAMPED RENDER TEST ===")
    msg("Creating unique filename to verify rendering works")
    msg("===============================================")
    
    -- Get current time for unique filename
    local timestamp = os.date("%H%M%S")
    local output_file = "D:\\DrumTracKAI_v1.1.7\\admin\\sd3_extracted_samples\\test_" .. timestamp .. ".wav"
    
    msg("Unique test file: test_" .. timestamp .. ".wav")
    
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
    
    -- Set up render bounds (0 to 5 seconds)
    reaper.GetSet_LoopTimeRange(true, false, 0, 5.0, false)
    
    -- Check if file already exists (it shouldn't with timestamp)
    local existing_check = io.open(output_file, "r")
    if existing_check then
        existing_check:close()
        msg("WARNING: File already exists (this shouldn't happen)")
    else
        msg("✓ Confirmed file doesn't exist yet")
    end
    
    msg("✓ Set render bounds: 0 to 5 seconds")
    msg("")
    msg("BEFORE RENDERING:")
    msg("File exists: NO")
    msg("")
    msg("MANUAL RENDER STEPS:")
    msg("1. The render dialog should open automatically")
    msg("2. Set output filename to: test_" .. timestamp .. ".wav")
    msg("3. Make sure 'Time selection' is checked")
    msg("4. Click 'Render'")
    msg("5. After rendering, I'll check if the file was created")
    msg("")
    msg("Opening render dialog now...")
    
    -- Update display
    reaper.UpdateArrange()
    
    -- Show render dialog
    reaper.Main_OnCommand(42230, 0)  -- File: Render project
    
    -- Wait a moment then check if file was created
    reaper.defer(function()
        local check_file = io.open(output_file, "r")
        if check_file then
            check_file:close()
            local file_size = reaper.file_exists(output_file)
            msg("")
            msg("AFTER RENDERING:")
            msg("✓ SUCCESS: File created! (" .. file_size .. " bytes)")
            msg("✓ Rendering is working correctly!")
        else
            msg("")
            msg("AFTER RENDERING:")
            msg("✗ File not found - rendering may have failed")
            msg("Check if you completed the render dialog steps")
        end
    end)
end

main()
