-- Working Recording Test - Records SD3 output to new track
-- This approach creates a separate audio track to record the SD3 output

function msg(text)
    reaper.ShowConsoleMsg(text .. "\n")
end

function main()
    msg("=== WORKING RECORDING TEST ===")
    msg("Creating separate recording track for SD3 output")
    msg("===============================")
    
    -- Get track 1 (Superior Drummer 3)
    local sd3_track = reaper.GetTrack(0, 0)
    if not sd3_track then
        msg("ERROR: No Track 1 found")
        return
    end
    
    -- Clear any existing items first
    reaper.SelectAllMediaItems(0, true)
    local item_count = reaper.CountSelectedMediaItems(0)
    for i = item_count - 1, 0, -1 do
        local item = reaper.GetSelectedMediaItem(0, i)
        if item then
            local item_track = reaper.GetMediaItem_Track(item)
            reaper.DeleteTrackMediaItem(item_track, item)
        end
    end
    
    -- Create or get recording track (Track 2)
    local num_tracks = reaper.CountTracks(0)
    local record_track
    
    if num_tracks < 2 then
        -- Create new track for recording
        reaper.InsertTrackAtIndex(1, false)
        record_track = reaper.GetTrack(0, 1)
        reaper.GetSetMediaTrackInfo_String(record_track, "P_NAME", "SD3_Recording", true)
        msg("✓ Created recording track (Track 2)")
    else
        record_track = reaper.GetTrack(0, 1)
        msg("✓ Using existing Track 2 for recording")
    end
    
    -- Set up recording track to receive from SD3 track
    reaper.SetMediaTrackInfo_Value(record_track, "I_RECARM", 1)  -- Arm for recording
    reaper.SetMediaTrackInfo_Value(record_track, "I_RECINPUT", 1024)  -- Receive from track 1
    
    -- Create MIDI item on SD3 track
    local item = reaper.CreateNewMIDIItemInProj(sd3_track, 1.3, 3.3, false)
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
    
    msg("✓ Created china cymbal MIDI on Track 1")
    msg("✓ Track 2 armed to record Track 1 output")
    msg("")
    msg("NOW TRY:")
    msg("1. Press Record (main transport)")
    msg("2. Press Play")
    msg("3. You should see recording on Track 2")
    msg("4. Stop after 5 seconds")
    msg("")
    msg("Track 2 should capture the SD3 audio output!")
    
    -- Set cursor to start
    reaper.SetEditCurPos(0, false, false)
    reaper.UpdateArrange()
end

main()
