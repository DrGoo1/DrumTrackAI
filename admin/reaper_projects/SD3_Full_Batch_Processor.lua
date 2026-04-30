-- SD3 Full Batch Processor - Complete 500+ File Automation
-- Incorporates all proven fixes: RENDER_FILE/RENDER_PATTERN + MIDI positioning + dual output

function log_message(message)
    local timestamp = os.date("%H:%M:%S")
    reaper.ShowConsoleMsg("[" .. timestamp .. "] " .. message .. "\n")
end

function create_output_directories()
    log_message("Creating output directories...")
    
    local local_dir = "D:\\DrumTracKAI_v1.1.7\\admin\\sd3_extracted_samples"
    local db_dir = "E:\\DrumTracKAI_Database\\sd3_extracted_samples"
    
    -- Use Windows mkdir command (from memory fix)
    os.execute('mkdir "' .. local_dir .. '" 2>nul')
    os.execute('mkdir "' .. db_dir .. '" 2>nul')
    
    log_message("Output directories created")
end

function scan_midi_files(directory)
    log_message("Scanning MIDI files in: " .. directory)
    
    local midi_files = {}
    local scan_command = 'dir /b "' .. directory .. '\\*.mid"'
    
    local handle = io.popen(scan_command)
    if handle then
        for filename in handle:lines() do
            if filename:match("%.mid$") then
                table.insert(midi_files, filename)
            end
        end
        handle:close()
    end
    
    log_message("Found " .. #midi_files .. " MIDI files")
    return midi_files
end

function generate_short_filename(midi_filename)
    -- Convert long MIDI filename to short WAV filename
    local short_name = midi_filename:gsub("%.mid$", "")
    
    -- Extract key components and create short name
    if short_name:find("china") then
        local intensity = short_name:match("hard") and "h" or (short_name:match("medium") and "m" or "s")
        local number = short_name:match("(%d+)")
        return "china_" .. intensity .. "_" .. (number or "001") .. ".wav"
    elseif short_name:find("crash") then
        local intensity = short_name:match("hard") and "h" or (short_name:match("medium") and "m" or "s")
        local number = short_name:match("(%d+)")
        return "crash_" .. intensity .. "_" .. (number or "001") .. ".wav"
    elseif short_name:find("hihat") then
        local intensity = short_name:match("hard") and "h" or (short_name:match("medium") and "m" or "s")
        local number = short_name:match("(%d+)")
        return "hihat_" .. intensity .. "_" .. (number or "001") .. ".wav"
    elseif short_name:find("kick") then
        local intensity = short_name:match("hard") and "h" or (short_name:match("medium") and "m" or "s")
        local number = short_name:match("(%d+)")
        return "kick_" .. intensity .. "_" .. (number or "001") .. ".wav"
    elseif short_name:find("snare") then
        local intensity = short_name:match("hard") and "h" or (short_name:match("medium") and "m" or "s")
        local number = short_name:match("(%d+)")
        return "snare_" .. intensity .. "_" .. (number or "001") .. ".wav"
    elseif short_name:find("tom") then
        local intensity = short_name:match("hard") and "h" or (short_name:match("medium") and "m" or "s")
        local number = short_name:match("(%d+)")
        return "tom_" .. intensity .. "_" .. (number or "001") .. ".wav"
    elseif short_name:find("ride") then
        local intensity = short_name:match("hard") and "h" or (short_name:match("medium") and "m" or "s")
        local number = short_name:match("(%d+)")
        return "ride_" .. intensity .. "_" .. (number or "001") .. ".wav"
    else
        -- Generic fallback
        local number = short_name:match("(%d+)")
        return "drum_" .. (number or "001") .. ".wav"
    end
end

function setup_render_settings()
    log_message("Setting up render parameters...")
    
    -- Set render format to WAV
    reaper.GetSetProjectInfo_String(0, "RENDER_FORMAT", "wav", true)
    
    -- Set render bounds to time selection
    reaper.GetSetProjectInfo(0, "RENDER_BOUNDSFLAG", 1, true)
    
    -- Set render channels to stereo
    reaper.GetSetProjectInfo(0, "RENDER_CHANNELS", 2, true)
    
    -- Set sample rate to 44100
    reaper.GetSetProjectInfo(0, "RENDER_SRATE", 44100, true)
    
    -- Set bit depth to 24
    reaper.GetSetProjectInfo(0, "RENDER_DEPTH", 24, true)
    
    log_message("Render settings configured")
end

function process_midi_file(midi_path, output_filename, file_index, total_files)
    log_message("=== Processing file " .. file_index .. " of " .. total_files .. " ===")
    log_message("Input: " .. midi_path)
    log_message("Output: " .. output_filename)
    
    -- Get SD3 track (Track 1, index 0)
    local sd3_track = reaper.GetTrack(0, 0)
    if not sd3_track then
        log_message("ERROR: SD3 track not found!")
        return false
    end
    
    -- Clear existing items on SD3 track
    local item_count = reaper.CountTrackMediaItems(sd3_track)
    for i = item_count - 1, 0, -1 do
        local item = reaper.GetTrackMediaItem(sd3_track, i)
        reaper.DeleteTrackMediaItem(sd3_track, item)
    end
    
    -- Insert MIDI file onto SD3 track
    reaper.SetOnlyTrackSelected(sd3_track)
    reaper.InsertMedia(midi_path, 0)
    
    -- Get the newly inserted item and move it to position 1.3 seconds
    local new_item_count = reaper.CountTrackMediaItems(sd3_track)
    if new_item_count > 0 then
        local new_item = reaper.GetTrackMediaItem(sd3_track, new_item_count - 1)
        reaper.SetMediaItemPosition(new_item, 1.3, false)  -- Move to 1.3 seconds
    else
        log_message("ERROR: MIDI file not loaded")
        return false
    end
    
    -- Set time selection to capture the drum hit (1.3 to 5.6 seconds = 4.3 second duration)
    reaper.GetSet_LoopTimeRange(true, false, 1.3, 5.6, false)
    
    -- CRITICAL FIX: Set render output path and filename BEFORE calling render
    local output_dir = "D:\\DrumTracKAI_v1.1.7\\admin\\sd3_extracted_samples"
    reaper.GetSetProjectInfo_String(0, 'RENDER_FILE', output_dir, true)
    reaper.GetSetProjectInfo_String(0, 'RENDER_PATTERN', output_filename:gsub("%.wav$", ""), true)
    
    -- NOW call the render command (this should work!)
    reaper.Main_OnCommand(42230, 0)
    
    -- Wait for render to complete
    for i = 1, 50 do  -- Wait up to 5 seconds
        reaper.defer(function() end)
    end
    
    -- Check if file was created
    local output_path = output_dir .. "\\" .. output_filename
    local file = io.open(output_path, "r")
    if file then
        file:close()
        log_message("SUCCESS: File created - " .. output_filename)
        
        -- Copy to database location
        local db_path = "E:\\DrumTracKAI_Database\\sd3_extracted_samples\\" .. output_filename
        local copy_cmd = 'copy "' .. output_path .. '" "' .. db_path .. '"'
        os.execute(copy_cmd)
        
        return true
    else
        log_message("ERROR: File not created - " .. output_filename)
        return false
    end
end

function save_progress_report(success_count, total_files, failed_files, processing_time)
    local report_content = string.format([[
=== SD3 Full Batch Processing Report ===
Date: %s
Processing Time: %.1f minutes (%.1f seconds)

SUMMARY:
- Total Files: %d
- Successful: %d
- Failed: %d
- Success Rate: %.1f%%
- Average Time per File: %.2f seconds

PERFORMANCE:
- Files per minute: %.1f
- Estimated time for 500 files: %.1f minutes

OUTPUT LOCATIONS:
- Local: D:\DrumTracKAI_v1.1.7\admin\sd3_extracted_samples\
- Database: E:\DrumTracKAI_Database\sd3_extracted_samples\

FAILED FILES:
%s

SYSTEM CONFIGURATION:
- REAPER Version: 7.42
- Superior Drummer 3 on Track 1
- Render Settings: 44.1kHz, 24-bit, stereo WAV
- Duration: 4.3 seconds per sample
- MIDI Position: 1.3 seconds
]], 
    os.date("%Y-%m-%d %H:%M:%S"),
    processing_time / 60,
    processing_time,
    total_files,
    success_count,
    total_files - success_count,
    (success_count / total_files) * 100,
    processing_time / total_files,
    total_files / (processing_time / 60),
    500 * (processing_time / total_files) / 60,
    table.concat(failed_files, "\n")
    )
    
    local report_path = "D:\\DrumTracKAI_v1.1.7\\admin\\sd3_extracted_samples\\batch_processing_report.txt"
    local report_file = io.open(report_path, "w")
    if report_file then
        report_file:write(report_content)
        report_file:close()
        log_message("Processing report saved: " .. report_path)
    end
end

function main()
    log_message("=== SD3 FULL BATCH PROCESSOR STARTED ===")
    log_message("Processing ALL MIDI files with proven automation fixes")
    
    -- Clear console
    reaper.ShowConsoleMsg("")
    
    -- Create output directories
    create_output_directories()
    
    -- Setup render settings
    setup_render_settings()
    
    -- Scan for all MIDI files
    local midi_dir = "D:\\DrumTracKAI_v1.1.7\\admin\\sd3_midi_patterns\\"
    local midi_files = scan_midi_files(midi_dir)
    
    if #midi_files == 0 then
        log_message("ERROR: No MIDI files found!")
        return
    end
    
    -- Processing variables
    local success_count = 0
    local failed_files = {}
    local start_time = reaper.time_precise()
    
    -- Progress tracking
    log_message("")
    log_message("=== STARTING FULL BATCH PROCESSING ===")
    log_message("Total files to process: " .. #midi_files)
    log_message("Estimated time: " .. string.format("%.1f", (#midi_files * 1.2) / 60) .. " minutes")
    log_message("")
    
    -- Process each MIDI file
    for i, filename in ipairs(midi_files) do
        local midi_path = midi_dir .. filename
        local output_filename = generate_short_filename(filename)
        
        -- Progress indicator
        if i % 10 == 0 or i == 1 then
            local progress = (i / #midi_files) * 100
            local elapsed = reaper.time_precise() - start_time
            local estimated_total = elapsed * (#midi_files / i)
            local remaining = estimated_total - elapsed
            
            log_message("")
            log_message("=== PROGRESS UPDATE ===")
            log_message("Completed: " .. (i-1) .. " of " .. #midi_files .. " (" .. string.format("%.1f", progress) .. "%)")
            log_message("Successful: " .. success_count .. " files")
            log_message("Elapsed time: " .. string.format("%.1f", elapsed / 60) .. " minutes")
            log_message("Estimated remaining: " .. string.format("%.1f", remaining / 60) .. " minutes")
            log_message("")
        end
        
        local success = process_midi_file(midi_path, output_filename, i, #midi_files)
        if success then
            success_count = success_count + 1
        else
            table.insert(failed_files, filename)
        end
        
        -- Brief pause to prevent system overload
        for j = 1, 1000 do end
    end
    
    local end_time = reaper.time_precise()
    local total_time = end_time - start_time
    
    log_message("")
    log_message("=== FULL BATCH PROCESSING COMPLETE ===")
    log_message("Total files processed: " .. #midi_files)
    log_message("Successfully processed: " .. success_count)
    log_message("Failed: " .. (#midi_files - success_count))
    log_message("Success rate: " .. string.format("%.1f", (success_count / #midi_files) * 100) .. "%")
    log_message("Total processing time: " .. string.format("%.1f", total_time / 60) .. " minutes")
    log_message("Average time per file: " .. string.format("%.2f", total_time / #midi_files) .. " seconds")
    
    -- Save detailed report
    save_progress_report(success_count, #midi_files, failed_files, total_time)
    
    -- Final status
    if success_count == #midi_files then
        log_message("")
        log_message("🎉 COMPLETE SUCCESS! All files processed successfully!")
        log_message("✅ DrumTracKAI training dataset generation complete")
        log_message("✅ " .. success_count .. " drum samples ready for training")
        
        -- Show success dialog
        reaper.ShowMessageBox("🎉 BATCH PROCESSING COMPLETE!\n\n" ..
                             "Successfully processed: " .. success_count .. " of " .. #midi_files .. " files\n" ..
                             "Processing time: " .. string.format("%.1f", total_time / 60) .. " minutes\n\n" ..
                             "DrumTracKAI training dataset is ready!\n\n" ..
                             "Files saved to:\n" ..
                             "• D:\\DrumTracKAI_v1.1.7\\admin\\sd3_extracted_samples\\\n" ..
                             "• E:\\DrumTracKAI_Database\\sd3_extracted_samples\\", 
                             "Batch Processing Complete", 0)
    else
        log_message("")
        log_message("⚠️ Batch completed with some failures")
        log_message("Check processing report for details on failed files")
        
        -- Show partial success dialog
        reaper.ShowMessageBox("Batch Processing Complete\n\n" ..
                             "Successfully processed: " .. success_count .. " of " .. #midi_files .. " files\n" ..
                             "Failed: " .. (#midi_files - success_count) .. " files\n" ..
                             "Success rate: " .. string.format("%.1f", (success_count / #midi_files) * 100) .. "%\n\n" ..
                             "Check batch_processing_report.txt for details.", 
                             "Batch Processing Results", 0)
    end
end

-- Auto-start the script after 5 seconds
function start_delayed()
    log_message("Full batch processing will start in 5 seconds...")
    log_message("Make sure Superior Drummer 3 is loaded on Track 1")
    log_message("This will process ALL " .. "500+" .. " MIDI files")
    log_message("Estimated processing time: 10-15 minutes")
    log_message("")
    
    -- 5 second countdown
    for i = 5, 1, -1 do
        log_message("Starting in " .. i .. " seconds...")
        reaper.defer(function() end)
        for j = 1, 10000 do end  -- Brief delay
    end
    
    main()
end

start_delayed()
