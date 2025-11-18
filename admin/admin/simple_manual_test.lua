-- Simple Manual Recording Test for Superior Drummer 3
-- This script just creates MIDI items and lets you manually record

function msg(text)
    reaper.ShowConsoleMsg(text .. "\n")
end

function main()
    msg("=== SIMPLE MANUAL RECORDING TEST ===")
    msg("This script will:")
    msg("1. Create a china cymbal MIDI note on Track 1")
    msg("2. Set up for manual recording")
    msg("3. You manually press Record and Play")
    msg("=====================================")
    
    -- Get track 1
    local track = reaper.GetTrack(0, 0)
    if not track then
        msg("ERROR: No Track 1 found - make sure Superior Drummer 3 is loaded")
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
    
    -- Set cursor to 1.3 seconds (pre-roll)
    reaper.SetEditCurPos(1.3, false, false)
    
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
    
    -- Add china cymbal note (note 99 from your SD3 mapping)
    reaper.MIDI_InsertNote(take, false, false, 0, 960, 0, 99, 100, false)
    reaper.MIDI_Sort(take)
    
    msg("✓ Created china cymbal MIDI item at 1.3 seconds")
    msg("✓ MIDI note 99 (china cymbal) added")
    msg("")
    msg("MANUAL STEPS:")
    msg("1. Arm Track 1 for recording (click the red record button on the track)")
    msg("2. Press the main Record button in transport")
    msg("3. Press Play - you should hear the china cymbal and see recording")
    msg("4. Let it record for about 5 seconds")
    msg("5. Press Stop")
    msg("")
    msg("If you hear the china cymbal, Superior Drummer 3 is working!")
    msg("If you see recording levels, the recording setup is working!")
    
    -- Set cursor back to start for recording
    reaper.SetEditCurPos(0, false, false)
    
    -- Update display
    reaper.UpdateArrange()
    
    msg("Ready for manual recording test!")
end

main()
