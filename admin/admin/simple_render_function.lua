-- Simple Render Function Test - Direct API call to render
-- Uses REAPER's RenderFileSection function directly

function msg(text)
    reaper.ShowConsoleMsg(text .. "\n")
end

function main()
    msg("=== SIMPLE RENDER FUNCTION TEST ===")
    msg("Using direct RenderFileSection API call")
    msg("====================================")
    
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
    
    -- Set up render parameters
    local start_time = 0.0
    local end_time = 5.0
    local sample_rate = 44100
    local num_channels = 2
    local timestamp = os.date("%H%M%S")
    local output_file = "D:\\DrumTracKAI_v1.1.7\\admin\\sd3_extracted_samples\\direct_" .. timestamp .. ".wav"
    
    msg("✓ Render settings:")
    msg("  Start: " .. start_time .. "s")
    msg("  End: " .. end_time .. "s")
    msg("  Output: direct_" .. timestamp .. ".wav")
    
    -- Check if file exists before render
    local pre_check = io.open(output_file, "r")
    if pre_check then
        pre_check:close()
        msg("WARNING: File already exists")
    else
        msg("✓ Confirmed file doesn't exist")
    end
    
    -- Update display
    reaper.UpdateArrange()
    
    msg("")
    msg("Attempting direct render...")
    
    -- Try direct render function with proper config
    local render_cfg = "d2F2ZQ==" -- Base64 for WAV format
    local render_success = reaper.RenderFileSection(
        output_file,     -- filename
        render_cfg,      -- cfg (WAV format)
        start_time,      -- startpos
        end_time,        -- endpos
        sample_rate,     -- samplerate
        num_channels,    -- nch
        0,               -- length (0 = use endpos-startpos)
        0                -- flags
    )
    
    if render_success then
        msg("✓ Render function returned success")
    else
        msg("✗ Render function returned failure")
    end
    
    -- Wait a moment then check if file was created
    local wait_time = 0
    local function check_file()
        wait_time = wait_time + 1
        local check = io.open(output_file, "r")
        if check then
            check:close()
            local file_size = reaper.file_exists(output_file)
            msg("")
            msg("RESULT AFTER " .. wait_time .. " SECONDS:")
            msg("✓ SUCCESS: File created! (" .. file_size .. " bytes)")
            msg("✓ Direct rendering works!")
            return
        elseif wait_time < 10 then
            msg("Waiting for render... " .. wait_time .. "s")
            reaper.defer(check_file)
        else
            msg("")
            msg("RESULT AFTER 10 SECONDS:")
            msg("✗ File not created - render failed")
            msg("Direct rendering may not be working")
        end
    end
    
    reaper.defer(check_file)
end

main()
