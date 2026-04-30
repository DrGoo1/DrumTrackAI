-- Batch MIDI Render Script for DrumTracKAI
-- ==========================================
-- 
-- Processes ALL MIDI files in the sd3_midi_patterns directory
-- and renders them to individual WAV files for ML training.
--
-- Author: DrumTracKAI v1.1.7
-- Date: July 23, 2025

function msg(text)
    reaper.ShowConsoleMsg(text .. "\n")
end

function get_all_midi_files(midi_dir)
    msg("=== SCANNING FOR MIDI FILES ===")
    msg("Directory: " .. midi_dir)
    
    local midi_files = {}
    local file_count = 0
    
    -- Use Windows dir command to get MIDI files
    local handle = io.popen('dir "' .. midi_dir .. '*.mid" /b 2>nul')
    if handle then
        for filename in handle:lines() do
            if filename and filename ~= "" then
                table.insert(midi_files, midi_dir .. filename)
                file_count = file_count + 1
            end
        end
        handle:close()
    end
    
    msg("Found " .. file_count .. " MIDI files")
    for i, file in ipairs(midi_files) do
        if i <= 5 then  -- Show first 5 files
            local filename = file:match("([^\\]+)$")
            msg("  " .. i .. ". " .. filename)
        elseif i == 6 then
            msg("  ... and " .. (file_count - 5) .. " more files")
            break
        end
    end
    
    return midi_files
end

function extract_instrument_name(midi_filename)
    -- Extract clean instrument name from MIDI filename
    local name = midi_filename:gsub("%.mid$", "")  -- Remove .mid extension
    name = name:gsub("_[0-9]+$", "")  -- Remove trailing numbers like _053
    return name
end

function import_midi_simple(midi_path)
    -- Check if MIDI file exists
    local file = io.open(midi_path, "r")
    if not file then
        msg("ERROR: MIDI file not found - " .. midi_path)
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
    
    -- Clear any existing items on the track
    local item_count = reaper.CountTrackMediaItems(track)
    for i = item_count - 1, 0, -1 do
        local item = reaper.GetTrackMediaItem(track, i)
        reaper.DeleteTrackMediaItem(track, item)
    end
    
    -- Import MIDI file at position 0
    reaper.InsertMedia(midi_path, 0)
    
    -- Get the newly imported item
    item_count = reaper.CountTrackMediaItems(track)
    if item_count == 0 then
        msg("ERROR: No items found after MIDI import!")
        return false
    end
    
    local item = reaper.GetTrackMediaItem(track, item_count - 1)
    return item
end

function position_midi_at_beat_1_3(item)
    if not item then
        return false
    end
    
    -- At 120 BPM, beat 1.3 = 0.25 seconds from start
    local beat_1_3_position = 0.25
    reaper.SetMediaItemPosition(item, beat_1_3_position, false)
    return true
end

function set_render_selection_1_1_to_2_1()
    -- At 120 BPM: beat 1.1 = 0.0 seconds, beat 2.1 = 0.5 seconds
    local render_start = 0.0
    local render_end = 0.5
    reaper.GetSet_LoopTimeRange(true, false, render_start, render_end, false)
    return true
end

function configure_render_simple(output_path, instrument_name)
    -- Set output file path
    local full_output_path = output_path .. "\\" .. instrument_name .. ".wav"
    reaper.GetSetProjectInfo_String(0, "RENDER_FILE", full_output_path, true)
    
    -- Set render format to WAV
    reaper.GetSetProjectInfo_String(0, "RENDER_FORMAT", "wav", true)
    
    -- Set render bounds to time selection
    reaper.GetSetProjectInfo(0, "RENDER_BOUNDSFLAG", 1, true)
    
    -- Set render channels to stereo
    reaper.GetSetProjectInfo(0, "RENDER_CHANNELS", 2, true)
    
    -- Set sample rate to 44.1kHz
    reaper.GetSetProjectInfo(0, "RENDER_SRATE", 44100, true)
    
    return true
end

function render_and_wait()
    -- Start render
    reaper.Main_OnCommand(42230, 0)  -- Render project to file
    
    -- Wait for render to complete
    local wait_time = 15  -- 15 seconds should be plenty for 0.5 seconds of audio
    local start_time = reaper.time_precise()
    while reaper.time_precise() - start_time < wait_time do
        -- Wait for render
    end
    
    return true
end

function cleanup_project_simple()
    -- CRITICAL: Stop playback first
    reaper.Main_OnCommand(1016, 0)  -- Stop playback
    
    -- CRITICAL: Reset timeline cursor to zero
    reaper.SetEditCurPos(0, false, false)
    
    -- Select all items
    reaper.Main_OnCommand(40182, 0)  -- Select all items
    
    -- Delete selected items
    reaper.Main_OnCommand(40006, 0)  -- Delete items
    
    -- Clear time selection
    reaper.Main_OnCommand(40020, 0)  -- Clear time selection
    
    -- CRITICAL: Clear render bounds
    reaper.GetSet_LoopTimeRange(true, false, 0, 0, false)
    
    -- CRITICAL: Reset cursor to zero again after cleanup
    reaper.SetEditCurPos(0, false, false)
    
    -- Update timeline display
    reaper.UpdateTimeline()
    
    return true
end

function process_single_midi_batch(midi_path, output_dir)
    local midi_filename = midi_path:match("([^\\]+)$")  -- Get filename from path
    local instrument_name = extract_instrument_name(midi_filename)
    
    -- Check if output already exists
    local output_file = output_dir .. "\\" .. instrument_name .. ".wav"
    local file = io.open(output_file, "r")
    if file then
        file:close()
        msg("SKIPPING: " .. instrument_name .. " (already exists)")
        return true
    end
    
    msg("PROCESSING: " .. instrument_name)
    
    -- CRITICAL: Ensure timeline starts at zero for each file
    reaper.Main_OnCommand(1016, 0)  -- Stop playback
    reaper.SetEditCurPos(0, false, false)  -- Reset cursor to zero
    reaper.UpdateTimeline()  -- Update display
    
    -- Execute workflow
    local item = import_midi_simple(midi_path)
    if not item then
        msg("FAILED: MIDI import - " .. instrument_name)
        return false
    end
    
    if not position_midi_at_beat_1_3(item) then
        msg("FAILED: MIDI positioning - " .. instrument_name)
        return false
    end
    
    if not set_render_selection_1_1_to_2_1() then
        msg("FAILED: Render selection - " .. instrument_name)
        return false
    end
    
    if not configure_render_simple(output_dir, instrument_name) then
        msg("FAILED: Render config - " .. instrument_name)
        return false
    end
    
    if not render_and_wait() then
        msg("FAILED: Render - " .. instrument_name)
        return false
    end
    
    -- Verify output file was created
    file = io.open(output_file, "r")
    if file then
        file:close()
        msg("SUCCESS: " .. instrument_name .. ".wav")
        cleanup_project_simple()
        return true
    else
        msg("FAILED: Output not created - " .. instrument_name)
        cleanup_project_simple()
        return false
    end
end

function main()
    msg("BATCH MIDI RENDER SCRIPT FOR DRUMTRACKAI")
    msg(string.rep("=", 60))
    msg("Processing ALL MIDI files for Superior Drummer extraction")
    msg(string.rep("=", 60))
    
    -- Configuration
    local midi_dir = "D:\\DrumTracKAI_v1.1.7\\admin\\sd3_midi_patterns\\"
    local output_dir = "D:\\DrumTracKAI_v1.1.7\\admin\\sd3_extracted_samples"
    
    -- Ensure output directory exists
    reaper.RecursiveCreateDirectory(output_dir, 0)
    
    -- Get all MIDI files
    local midi_files = get_all_midi_files(midi_dir)
    local total_files = #midi_files
    
    if total_files == 0 then
        msg("ERROR: No MIDI files found in " .. midi_dir)
        return
    end
    
    msg("\nStarting batch processing of " .. total_files .. " files...")
    msg("Output directory: " .. output_dir)
    
    -- Process all files
    local success_count = 0
    local skip_count = 0
    local fail_count = 0
    
    local start_time = reaper.time_precise()
    
    for i, midi_file in ipairs(midi_files) do
        local progress = math.floor((i / total_files) * 100)
        msg("\n[" .. i .. "/" .. total_files .. " - " .. progress .. "%]")
        
        local result = process_single_midi_batch(midi_file, output_dir)
        
        if result == true then
            success_count = success_count + 1
        else
            fail_count = fail_count + 1
        end
        
        -- Show progress every 10 files
        if i % 10 == 0 or i == total_files then
            local elapsed = reaper.time_precise() - start_time
            local avg_time = elapsed / i
            local remaining = (total_files - i) * avg_time
            
            msg("PROGRESS UPDATE:")
            msg("  Processed: " .. i .. "/" .. total_files .. " (" .. progress .. "%)")
            msg("  Success: " .. success_count .. ", Failed: " .. fail_count)
            msg("  Elapsed: " .. math.floor(elapsed) .. "s, Est. remaining: " .. math.floor(remaining) .. "s")
        end
    end
    
    -- Final summary
    local total_time = reaper.time_precise() - start_time
    msg("\n" .. string.rep("=", 60))
    msg("BATCH PROCESSING COMPLETE!")
    msg(string.rep("=", 60))
    msg("Total files: " .. total_files)
    msg("Successful: " .. success_count)
    msg("Failed: " .. fail_count)
    msg("Total time: " .. math.floor(total_time) .. " seconds")
    msg("Average per file: " .. string.format("%.1f", total_time / total_files) .. " seconds")
    
    if success_count == total_files then
        msg("🎉 ALL FILES PROCESSED SUCCESSFULLY!")
    elseif success_count > 0 then
        msg("⚠️ PARTIAL SUCCESS - " .. success_count .. " files completed")
    else
        msg("❌ BATCH PROCESSING FAILED - No files processed")
    end
    
    msg("\nBatch processing complete!")
end

-- Execute main function
main()
