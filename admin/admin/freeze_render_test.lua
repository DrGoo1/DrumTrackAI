-- Freeze Render Test - Use REAPER's track freeze to render SD3 output
-- This approach freezes the track which creates an audio file

function msg(text)
    reaper.ShowConsoleMsg(text .. "\n")
end

function main()
    msg("=== FREEZE RENDER TEST ===")
    msg("Using REAPER's track freeze to capture SD3 output")
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
    
    -- Select the track
    reaper.SetOnlyTrackSelected(track)
    
    -- Update display
    reaper.UpdateArrange()
    
    msg("✓ Track 1 selected")
    msg("")
    msg("FREEZE RENDER TEST:")
    msg("1. Right-click on Track 1")
    msg("2. Select 'Render/freeze tracks...'")
    msg("3. Choose 'Freeze tracks (render in place)'")
    msg("4. This should create an audio item on the track")
    msg("5. The audio item will contain the SD3 output")
    msg("")
    msg("OR try the automated freeze:")
    msg("I'll attempt to freeze the track automatically...")
    
    -- Try automated freeze
    reaper.Main_OnCommand(41223, 0)  -- Track: Render/freeze tracks
    
    msg("✓ Freeze command sent")
    msg("")
    msg("Check if an audio item appears on Track 1!")
    msg("If it works, we can extract that audio to WAV files.")
end

main()
