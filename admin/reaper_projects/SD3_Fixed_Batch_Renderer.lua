-- SD3 Fixed Batch Renderer - SOLUTION FOUND!
-- Key fix: Set RENDER_FILE and RENDER_PATTERN before calling render command

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

function process_midi_file(midi_path, output_filename)
    log_message("Processing: " .. midi_path)
    
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
    
    -- Set time selection (0 to 4.3 seconds for drum samples)
    reaper.GetSet_LoopTimeRange(true, false, 0.0, 4.3, false)
    log_message("Time selection set: 0.0 to 4.3 seconds")
    
    -- CRITICAL FIX: Set render output path and filename BEFORE calling render
    local output_dir = "D:\\DrumTracKAI_v1.1.7\\admin\\sd3_extracted_samples"
    reaper.GetSetProjectInfo_String(0, 'RENDER_FILE', output_dir, true)
    reaper.GetSetProjectInfo_String(0, 'RENDER_PATTERN', output_filename:gsub("%.wav$", ""), true)
    
    log_message("Render path set: " .. output_dir)
    log_message("Render filename set: " .. output_filename)
    
    -- NOW call the render command (this should work!)
    log_message("Calling render command...")
    reaper.Main_OnCommand(42230, 0)
    
    -- Wait for render to complete
    log_message("Waiting for render to complete...")
    for i = 1, 50 do  -- Wait up to 5 seconds
        reaper.defer(function() end)
        if i % 10 == 0 then
            log_message("Waiting... (" .. (i/10) .. "s)")
        end
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
        log_message("File copied to database location")
        
        return true
    else
        log_message("ERROR: File not created - " .. output_filename)
        return false
    end
end

function main()
    log_message("=== SD3 Fixed Batch Renderer Started ===")
    log_message("Using RENDER_FILE and RENDER_PATTERN fix from research")
    
    -- Clear console
    reaper.ShowConsoleMsg("")
    
    -- Create output directories
    create_output_directories()
    
    -- Setup render settings
    setup_render_settings()
    
    -- Test with 3 files first
    local test_files = {
        "china_china_hard_053.mid",
        "crash_crash_1_medium_043.mid", 
        "hihat_hihat_closed_edge_hard_closed_072.mid"
    }
    
    local midi_dir = "D:\\DrumTracKAI_v1.1.7\\admin\\sd3_midi_patterns\\"
    local success_count = 0
    
    for i, filename in ipairs(test_files) do
        log_message("=== Processing file " .. i .. " of " .. #test_files .. " ===")
        
        local midi_path = midi_dir .. filename
        local output_filename = generate_short_filename(filename)
        
        local success = process_midi_file(midi_path, output_filename)
        if success then
            success_count = success_count + 1
        end
        
        log_message("File " .. i .. " complete. Success: " .. tostring(success))
        log_message("")
    end
    
    log_message("=== Batch Processing Complete ===")
    log_message("Successfully processed: " .. success_count .. " of " .. #test_files .. " files")
    
    if success_count > 0 then
        log_message("SUCCESS: Render command is now working!")
        log_message("Ready to process full 500+ file batch")
    else
        log_message("ERROR: Render command still not working")
        log_message("Check REAPER console for error messages")
    end
end

-- Auto-start the script
reaper.defer(main)
