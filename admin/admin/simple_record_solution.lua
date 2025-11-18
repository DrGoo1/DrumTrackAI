-- Simple Record Solution - Just record the MIDI output directly
-- This is the most straightforward approach

function msg(text)
    reaper.ShowConsoleMsg(text .. "\n")
end

function main()
    msg("=== SIMPLE RECORD SOLUTION ===")
    msg("Recording MIDI output directly - the right way")
    msg("===========================================")
    
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
    
    -- Set up recording path and filename
    local timestamp = os.date("%H%M%S")
    local output_dir = "D:\\DrumTracKAI_v1.1.7\\admin\\sd3_extracted_samples\\"
    local output_file = "record_" .. timestamp .. ".wav"
    local full_path = output_dir .. output_file
    
    -- Set project recording path
    reaper.GetSetProjectInfo_String(0, "RECORD_PATH", output_dir, true)
    
    -- Set recording format to WAV
    reaper.GetSetProjectInfo(0, "RECORD_FORMAT", 1819048051, true) -- WAV format
    
    msg("✓ Set recording path: " .. output_dir)
    msg("✓ Set recording format: WAV")
    
    -- Arm track for recording (record its output)
    reaper.SetMediaTrackInfo_Value(track, "I_RECARM", 1)
    reaper.SetMediaTrackInfo_Value(track, "I_RECMODE", 2) -- Record output (stereo)
    
    msg("✓ Armed Track 1 for output recording")
    
    -- Set cursor to start and time selection
    reaper.SetEditCurPos(0, false, false)
    reaper.GetSet_LoopTimeRange(true, false, 0, 5.0, false)
    
    msg("✓ Set cursor to start, time selection 0-5 seconds")
    msg("")
    msg("RECORDING SETUP COMPLETE!")
    msg("Now you just need to:")
    msg("1. Press the Record button (transport)")
    msg("2. Press Play")
    msg("3. Let it record for 5 seconds")
    msg("4. Press Stop")
    msg("")
    msg("The file will be saved as: " .. output_file)
    msg("In directory: " .. output_dir)
    msg("")
    msg("This is the simple, direct approach that should work!")
    
    -- Update display
    reaper.UpdateArrange()
end

main()
