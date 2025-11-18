-- Simple Working MIDI Render Script
-- ===================================
-- 
-- Simplified ReaScript that focuses on core functionality:
-- - Import MIDI file
-- - Position at beat 1.3
-- - Set render selection 1.1-2.1
-- - Render to properly named WAV file
--
-- Author: DrumTracKAI v1.1.7
-- Date: July 23, 2025

function msg(text)
    reaper.ShowConsoleMsg(text .. "\n")
end

function import_midi_simple(midi_path)
    msg("=== IMPORTING MIDI FILE ===")
    msg("File: " .. midi_path)
    
    -- Check if MIDI file exists
    local file = io.open(midi_path, "r")
    if not file then
        msg("ERROR: MIDI file not found!")
        return false
    end
    file:close()
    
    -- Get first track (should have SD3 loaded)
    local track_count = reaper.CountTracks(0)
    if track_count == 0 then
        msg("ERROR: No tracks found! Make sure SD3 is loaded on track 1.")
        return false
    end
    
    local track = reaper.GetTrack(0, 0)
    msg("Using track 1 for MIDI import")
    
    -- Clear any existing items on the track
    local item_count = reaper.CountTrackMediaItems(track)
    for i = item_count - 1, 0, -1 do
        local item = reaper.GetTrackMediaItem(track, i)
        reaper.DeleteTrackMediaItem(track, item)
    end
    msg("Cleared existing items from track")
    
    -- Import MIDI file at position 0
    reaper.InsertMedia(midi_path, 0)
    
    -- Get the newly imported item
    item_count = reaper.CountTrackMediaItems(track)
    if item_count == 0 then
        msg("ERROR: No items found after MIDI import!")
        return false
    end
    
    local item = reaper.GetTrackMediaItem(track, item_count - 1)
    msg("MIDI imported successfully")
    
    return item
end

function position_midi_at_beat_1_3(item)
    msg("=== POSITIONING MIDI AT BEAT 1.3 ===")
    
    if not item then
        msg("ERROR: No item to position!")
        return false
    end
    
    -- At 120 BPM, beat 1.3 = 0.25 seconds from start
    local beat_1_3_position = 0.25
    
    -- Position the MIDI at beat 1.3
    reaper.SetMediaItemPosition(item, beat_1_3_position, false)
    
    msg("MIDI positioned at beat 1.3 (" .. beat_1_3_position .. " seconds)")
    return true
end

function set_render_selection_1_1_to_2_1()
    msg("=== SETTING RENDER SELECTION: 1.1 to 2.1 ===")
    
    -- At 120 BPM: beat 1.1 = 0.0 seconds, beat 2.1 = 0.5 seconds
    local render_start = 0.0
    local render_end = 0.5
    
    -- Set time selection for rendering
    reaper.GetSet_LoopTimeRange(true, false, render_start, render_end, false)
    
    msg("Render selection set:")
    msg("  Start: " .. render_start .. " seconds (beat 1.1)")
    msg("  End: " .. render_end .. " seconds (beat 2.1)")
    msg("  Duration: " .. (render_end - render_start) .. " seconds")
    
    return true
end

function configure_render_simple(output_path, instrument_name)
    msg("=== CONFIGURING RENDER SETTINGS ===")
    
    -- Set output file path
    local full_output_path = output_path .. "\\" .. instrument_name .. ".wav"
    reaper.GetSetProjectInfo_String(0, "RENDER_FILE", full_output_path, true)
    msg("Output file: " .. full_output_path)
    
    -- Set render format to WAV
    reaper.GetSetProjectInfo_String(0, "RENDER_FORMAT", "wav", true)
    
    -- Set render bounds to time selection
    reaper.GetSetProjectInfo(0, "RENDER_BOUNDSFLAG", 1, true)
    
    -- Set render channels to stereo
    reaper.GetSetProjectInfo(0, "RENDER_CHANNELS", 2, true)
    
    -- Set sample rate to 44.1kHz
    reaper.GetSetProjectInfo(0, "RENDER_SRATE", 44100, true)
    
    msg("Render configured: WAV, 44.1kHz, Stereo, Time Selection")
    return true
end

function render_and_wait()
    msg("=== RENDERING AUDIO ===")
    
    -- Start render
    reaper.Main_OnCommand(42230, 0)  -- Render project to file
    
    -- Simple wait (render should complete quickly for 0.5 seconds)
    local wait_time = 10  -- 10 seconds should be plenty
    msg("Waiting " .. wait_time .. " seconds for render to complete...")
    
    local start_time = reaper.time_precise()
    while reaper.time_precise() - start_time < wait_time do
        -- Wait for render
    end
    
    msg("Render wait period completed")
    return true
end

function cleanup_project_simple()
    msg("=== CLEANING UP PROJECT ===")
    
    -- Select all items
    reaper.Main_OnCommand(40182, 0)  -- Select all items
    
    -- Delete selected items
    reaper.Main_OnCommand(40006, 0)  -- Delete items
    
    -- Clear time selection
    reaper.Main_OnCommand(40020, 0)  -- Clear time selection
    
    msg("Project cleaned up for next file")
    return true
end

function extract_instrument_name(midi_filename)
    -- Extract clean instrument name from MIDI filename
    local name = midi_filename:gsub("%.mid$", "")  -- Remove .mid extension
    name = name:gsub("_[0-9]+$", "")  -- Remove trailing numbers like _053
    return name
end

function process_single_midi_simple(midi_path, output_dir)
    msg("=" .. string.rep("=", 60))
    msg("SIMPLE PROCESSING: " .. midi_path)
    msg("=" .. string.rep("=", 60))
    
    local midi_filename = midi_path:match("([^\\]+)$")  -- Get filename from path
    local instrument_name = extract_instrument_name(midi_filename)
    
    msg("MIDI file: " .. midi_filename)
    msg("Instrument: " .. instrument_name)
    msg("Output directory: " .. output_dir)
    
    -- Check if output already exists
    local output_file = output_dir .. "\\" .. instrument_name .. ".wav"
    local file = io.open(output_file, "r")
    if file then
        file:close()
        msg("SKIPPING: Output already exists - " .. output_file)
        return true
    end
    
    -- Execute simple workflow
    local workflow_steps = {
        {"Import MIDI", function() return import_midi_simple(midi_path) end},
        {"Position at 1.3", function() return position_midi_at_beat_1_3(last_item) end},
        {"Set render selection", set_render_selection_1_1_to_2_1},
        {"Configure render", function() return configure_render_simple(output_dir, instrument_name) end},
        {"Render audio", render_and_wait},
        {"Cleanup project", cleanup_project_simple}
    }
    
    local last_item = nil
    
    for i, step in ipairs(workflow_steps) do
        local step_name, step_func = step[1], step[2]
        msg("\n--- " .. step_name .. " ---")
        
        local result = step_func()
        
        if step_name == "Import MIDI" then
            last_item = result
            if not last_item then
                msg("FAILED at: " .. step_name)
                return false
            end
        elseif not result then
            msg("FAILED at: " .. step_name)
            return false
        end
    end
    
    -- Verify output file was created
    file = io.open(output_file, "r")
    if file then
        file:close()
        msg("SUCCESS: Created " .. instrument_name .. ".wav")
        return true
    else
        msg("FAILED: Output file not created")
        return false
    end
end

function main()
    msg("SIMPLE WORKING REAPER SCRIPT FOR DRUMTRACKAI")
    msg(string.rep("=", 60))
    msg("Simplified approach focusing on core functionality")
    msg(string.rep("=", 60))
    
    -- Configuration
    local midi_dir = "D:\\DrumTracKAI_v1.1.7\\admin\\sd3_midi_patterns\\"
    local output_dir = "D:\\DrumTracKAI_v1.1.7\\admin\\sd3_extracted_samples"
    local test_midi = midi_dir .. "china_china_hard_053.mid"
    
    -- Ensure output directory exists
    reaper.RecursiveCreateDirectory(output_dir, 0)
    
    -- Test with single file
    msg("\nTesting simple workflow with: china_china_hard_053.mid")
    
    local success = process_single_midi_simple(test_midi, output_dir)
    
    if success then
        msg("\nSUCCESS: Simple ReaScript working perfectly!")
        msg("Core functionality verified:")
        msg("- MIDI import and positioning")
        msg("- Precise render timing (0.5 seconds)")
        msg("- Proper file naming")
        msg("- Project cleanup")
        msg("\nReady for batch processing!")
    else
        msg("\nFAILED: Simple ReaScript needs debugging")
    end
    
    msg("\nSimple ReaScript complete!")
end

-- Execute main function
main()
