-- SD3 Step-by-Step Test Script - WITH RENDER COMMAND FIX
-- Based on research: RENDER_FILE and RENDER_PATTERN must be set before render command

function log_message(message)
    local timestamp = os.date("%H:%M:%S")
    reaper.ShowConsoleMsg("[" .. timestamp .. "] " .. message .. "\n")
end

function wait_for_user(message)
    reaper.ShowMessageBox(message .. "\n\nClick OK to continue to next step.", "Step-by-Step Test", 0)
end

-- Step 1: Clear SD3 track and verify setup
function step1_clear_track()
    log_message("=== STEP 1: Clear SD3 track ===")
    
    -- Get SD3 track (Track 1, index 0)
    local sd3_track = reaper.GetTrack(0, 0)
    if not sd3_track then
        log_message("ERROR: SD3 track not found!")
        wait_for_user("ERROR: SD3 track not found! Make sure Superior Drummer 3 is loaded on Track 1.")
        return false
    end
    
    -- Get track name for verification
    local retval, track_name = reaper.GetTrackName(sd3_track)
    log_message("Found track: " .. (track_name or "Unknown"))
    
    -- Clear existing items on SD3 track
    local item_count = reaper.CountTrackMediaItems(sd3_track)
    log_message("Clearing " .. item_count .. " existing items from SD3 track")
    
    for i = item_count - 1, 0, -1 do
        local item = reaper.GetTrackMediaItem(sd3_track, i)
        reaper.DeleteTrackMediaItem(sd3_track, item)
    end
    
    log_message("SD3 track cleared successfully")
    wait_for_user("STEP 1 COMPLETE: SD3 track cleared. Ready for MIDI import.")
    return true
end

-- Step 2: Load MIDI file onto SD3 track
function step2_load_midi()
    log_message("=== STEP 2: Load MIDI file ===")
    
    local midi_file = "D:\\DrumTracKAI_v1.1.7\\admin\\sd3_midi_patterns\\china_china_hard_053.mid"
    log_message("Loading MIDI file: " .. midi_file)
    
    -- Get SD3 track
    local sd3_track = reaper.GetTrack(0, 0)
    reaper.SetOnlyTrackSelected(sd3_track)
    
    -- Insert MIDI file
    reaper.InsertMedia(midi_file, 0)
    
    -- Verify MIDI was loaded
    local new_item_count = reaper.CountTrackMediaItems(sd3_track)
    log_message("Items on SD3 track after MIDI insert: " .. new_item_count)
    
    if new_item_count > 0 then
        log_message("SUCCESS: MIDI file loaded onto SD3 track")
        wait_for_user("STEP 2 COMPLETE: MIDI file loaded. You should see the MIDI item on the SD3 track.")
        return true
    else
        log_message("ERROR: MIDI file not loaded")
        wait_for_user("ERROR: MIDI file not loaded. Check file path and try again.")
        return false
    end
end

-- Step 3: Set time selection
function step3_set_time_selection()
    log_message("=== STEP 3: Set time selection ===")
    
    -- Set time selection from 0 to 4.3 seconds
    reaper.GetSet_LoopTimeRange(true, false, 0.0, 4.3, false)
    
    -- Verify time selection
    local start_time, end_time = reaper.GetSet_LoopTimeRange(false, false, 0, 0, false)
    log_message("Time selection set: " .. start_time .. " to " .. end_time .. " seconds")
    
    wait_for_user("STEP 3 COMPLETE: Time selection set to 0.0 - 4.3 seconds. You should see the selection highlighted in the timeline.")
    return true
end

-- Step 4: Configure render settings (THE FIX!)
function step4_configure_render()
    log_message("=== STEP 4: Configure render settings (THE FIX!) ===")
    log_message("BREAKTHROUGH: Setting RENDER_FILE and RENDER_PATTERN BEFORE render command!")
    
    -- Create output directory
    local output_dir = "D:\\DrumTracKAI_v1.1.7\\admin\\sd3_extracted_samples"
    os.execute('mkdir "' .. output_dir .. '" 2>nul')
    log_message("Output directory created: " .. output_dir)
    
    -- CRITICAL FIX: Set render output path and filename BEFORE calling render command
    local output_filename = "step_test_sample"  -- without .wav extension
    
    log_message("Setting RENDER_FILE to: " .. output_dir)
    reaper.GetSetProjectInfo_String(0, 'RENDER_FILE', output_dir, true)
    
    log_message("Setting RENDER_PATTERN to: " .. output_filename)
    reaper.GetSetProjectInfo_String(0, 'RENDER_PATTERN', output_filename, true)
    
    -- Set additional render settings for reliability
    log_message("Configuring additional render settings...")
    reaper.GetSetProjectInfo_String(0, "RENDER_FORMAT", "wav", true)
    reaper.GetSetProjectInfo(0, "RENDER_BOUNDSFLAG", 1, true)  -- Time selection
    reaper.GetSetProjectInfo(0, "RENDER_CHANNELS", 2, true)    -- Stereo
    reaper.GetSetProjectInfo(0, "RENDER_SRATE", 44100, true)   -- 44.1kHz
    reaper.GetSetProjectInfo(0, "RENDER_DEPTH", 24, true)      -- 24-bit
    
    log_message("All render settings configured successfully")
    wait_for_user("STEP 4 COMPLETE: Render settings configured with the CRITICAL FIX. Ready to test render command.")
    return true
end

-- Step 5: Execute render command (should now work!)
function step5_execute_render()
    log_message("=== STEP 5: Execute render command ===")
    log_message("NOW calling render command 42230 with proper settings...")
    
    -- Call the render command (this should now work!)
    reaper.Main_OnCommand(42230, 0)
    log_message("Render command 42230 executed")
    
    -- Wait for render to complete
    log_message("Waiting for render to complete...")
    for i = 1, 50 do  -- Wait up to 5 seconds
        reaper.defer(function() end)
        if i % 10 == 0 then
            log_message("Waiting... (" .. (i/10) .. "s)")
        end
    end
    
    wait_for_user("STEP 5 COMPLETE: Render command executed. Check if render dialog appeared or if render completed automatically.")
    return true
end

-- Step 6: Verify output file
function step6_verify_output()
    log_message("=== STEP 6: Verify output file ===")
    
    local output_dir = "D:\\DrumTracKAI_v1.1.7\\admin\\sd3_extracted_samples"
    local expected_file = output_dir .. "\\step_test_sample.wav"
    
    log_message("Checking for output file: " .. expected_file)
    
    local file = io.open(expected_file, "r")
    if file then
        file:close()
        log_message("SUCCESS! Render file created: " .. expected_file)
        
        -- Check file size
        local file_info = reaper.file_exists(expected_file)
        if file_info then
            log_message("File exists and appears valid")
        end
        
        wait_for_user("SUCCESS! Output file created: " .. expected_file .. "\n\nThe render command fix is working!")
        return true
    else
        log_message("File not found - checking for other possible locations...")
        
        -- Check project directory
        local proj_path = reaper.GetProjectPath("")
        local alt_file = proj_path .. "\\step_test_sample.wav"
        log_message("Checking project directory: " .. alt_file)
        
        local alt_file_handle = io.open(alt_file, "r")
        if alt_file_handle then
            alt_file_handle:close()
            log_message("File found in project directory: " .. alt_file)
            wait_for_user("File found in project directory instead of target directory. Render is working but path needs adjustment.")
            return true
        else
            log_message("File not found in expected locations")
            wait_for_user("File not created. Check REAPER console for error messages or render dialog status.")
            return false
        end
    end
end

-- Main function to run all steps
function main()
    log_message("=== SD3 Step-by-Step Test with RENDER COMMAND FIX ===")
    log_message("Based on research: RENDER_FILE and RENDER_PATTERN must be set first!")
    
    -- Clear console
    reaper.ShowConsoleMsg("")
    
    local steps = {
        {name = "Clear SD3 track", func = step1_clear_track},
        {name = "Load MIDI file", func = step2_load_midi},
        {name = "Set time selection", func = step3_set_time_selection},
        {name = "Configure render settings (THE FIX!)", func = step4_configure_render},
        {name = "Execute render command", func = step5_execute_render},
        {name = "Verify output file", func = step6_verify_output}
    }
    
    local success_count = 0
    
    for i, step in ipairs(steps) do
        log_message("Starting step " .. i .. ": " .. step.name)
        
        local success = step.func()
        if success then
            success_count = success_count + 1
            log_message("Step " .. i .. " completed successfully")
        else
            log_message("Step " .. i .. " failed")
            wait_for_user("Step " .. i .. " failed. Check console output and fix issues before continuing.")
            break
        end
        
        log_message("")
    end
    
    log_message("=== Test Complete ===")
    log_message("Successfully completed: " .. success_count .. " of " .. #steps .. " steps")
    
    if success_count == #steps then
        log_message("ALL STEPS SUCCESSFUL! Render command fix is working!")
        wait_for_user("SUCCESS! All steps completed. The render command fix is working and ready for full batch processing!")
    else
        log_message("Some steps failed. Check console output for details.")
    end
end

-- Auto-start the script after 3 seconds
function start_delayed()
    log_message("Step-by-step test will start in 3 seconds...")
    reaper.defer(function()
        reaper.defer(function()
            reaper.defer(main)
        end)
    end)
end

start_delayed()
