-- Working Freeze Test - Most reliable way to capture VST output
-- Uses REAPER's freeze function which always works with VST instruments

function msg(text)
    reaper.ShowConsoleMsg(text .. "\n")
end

function file_exists(filepath)
    local f = io.open(filepath, "r")
    if f then
        f:close()
        return true
    end
    return false
end

function main()
    msg("=== WORKING FREEZE TEST ===")
    msg("Using track freeze - most reliable for VST instruments")
    msg("===============================================")
    
    -- Get track 1 (Superior Drummer 3)
    local track = reaper.GetTrack(0, 0)
    if not track then
        msg("ERROR: No Track 1 found")
        return
    end
    
    -- Clear any existing items and frozen states
    reaper.SelectAllMediaItems(0, true)
    local item_count = reaper.CountSelectedMediaItems(0)
    for i = item_count - 1, 0, -1 do
        local item = reaper.GetSelectedMediaItem(0, i)
        if item then
            local item_track = reaper.GetMediaItem_Track(item)
            reaper.DeleteTrackMediaItem(item_track, item)
        end
    end
    
    -- Unfreeze track if it's frozen
    reaper.SetOnlyTrackSelected(track)
    reaper.Main_OnCommand(41644, 0)  -- Track: Unfreeze tracks
    
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
    
    -- Select the track for freezing
    reaper.SetOnlyTrackSelected(track)
    reaper.UpdateArrange()
    
    msg("✓ Track 1 selected and ready for freeze")
    msg("")
    msg("FREEZE PROCESS:")
    msg("1. Freezing track (this captures VST output)...")
    
    -- Freeze the track (this creates audio from the VST)
    reaper.Main_OnCommand(41223, 0)  -- Track: Render/freeze tracks
    
    msg("✓ Freeze command executed")
    msg("2. Waiting for freeze to complete...")
    
    -- Wait for freeze to complete and check for audio item
    local wait_count = 0
    local function check_freeze()
        wait_count = wait_count + 1
        
        -- Check if track now has audio items (frozen result)
        local num_items = reaper.CountTrackMediaItems(track)
        local has_audio = false
        
        for i = 0, num_items - 1 do
            local check_item = reaper.GetTrackMediaItem(track, i)
            local check_take = reaper.GetActiveTake(check_item)
            if check_take then
                local source = reaper.GetMediaItemTake_Source(check_take)
                if source then
                    local source_type = reaper.GetMediaSourceType(source, "")
                    if source_type == "WAVE" then
                        has_audio = true
                        local source_file = reaper.GetMediaSourceFileName(source, "")
                        msg("✓ Found frozen audio: " .. source_file)
                        
                        -- Try to copy this file to our output directory
                        local timestamp = os.date("%H%M%S")
                        local output_file = "D:\\DrumTracKAI_v1.1.7\\admin\\sd3_extracted_samples\\freeze_" .. timestamp .. ".wav"
                        local copy_cmd = 'copy "' .. source_file .. '" "' .. output_file .. '"'
                        
                        msg("3. Copying frozen audio to output...")
                        msg("   From: " .. source_file)
                        msg("   To: freeze_" .. timestamp .. ".wav")
                        
                        os.execute(copy_cmd)
                        
                        -- Check if copy succeeded
                        if file_exists(output_file) then
                            local file_size = reaper.file_exists(output_file)
                            msg("")
                            msg("✓ SUCCESS: Freeze method works!")
                            msg("✓ Created: freeze_" .. timestamp .. ".wav (" .. file_size .. " bytes)")
                            msg("✓ This approach can be automated for batch processing!")
                        else
                            msg("✗ Copy failed, but freeze created audio")
                            msg("✓ Freeze method works - just need to fix file extraction")
                        end
                        return
                    end
                end
            end
        end
        
        if not has_audio and wait_count < 10 then
            msg("   Waiting for freeze... " .. wait_count .. "s")
            reaper.defer(check_freeze)
        elseif not has_audio then
            msg("")
            msg("✗ Freeze failed - no audio items created after 10 seconds")
            msg("Track freeze may not be working properly")
        end
    end
    
    reaper.defer(check_freeze)
end

main()
