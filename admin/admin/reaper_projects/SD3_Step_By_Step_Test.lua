-- SD3 Step-by-Step Test with Progress Dialogs
-- Each step waits for user confirmation before proceeding

reaper.ShowConsoleMsg("=== SD3 Step-by-Step Test with Progress Dialogs ===\n")

-- Configuration
local midi_folder = "D:\\DrumTracKAI_v1.1.7\\admin\\sd3_midi_patterns"
local output_local = "D:\\DrumTracKAI_v1.1.7\\admin\\sd3_extracted_samples"
local output_database = "E:\\DrumTracKAI_Database\\sd3_extracted_samples"

-- Test files
local test_files = {
    "china_china_hard_053.mid",
    "crash_crash_1_medium_043.mid", 
    "hihat_hihat_closed_edge_hard_closed_072.mid"
}

-- Generate short filename
function generate_short_filename(midi_filename)
    local base_name = midi_filename:gsub("%.mid$", "")
    
    local instrument = "drum"
    if base_name:find("china") then instrument = "china"
    elseif base_name:find("crash") then instrument = "crash"
    elseif base_name:find("hihat") then instrument = "hihat"
    end
    
    local velocity = "m"
    if base_name:find("hard") then velocity = "h"
    elseif base_name:find("medium") then velocity = "m"
    elseif base_name:find("soft") then velocity = "s"
    elseif base_name:find("ghost") then velocity = "g"
    end
    
    local number = base_name:match("(%d%d%d)$") or "001"
    
    return instrument .. "_" .. velocity .. "_" .. number .. ".wav"
end

-- Progress dialog function
function show_progress_dialog(title, message)
    local result = reaper.MB(message, title, 1)  -- OK/Cancel dialog
    return result == 1  -- Returns true if OK clicked, false if Cancel
end

-- Step 1: Clear previous clip
function clear_previous_clip()
    reaper.ShowConsoleMsg("STEP 1: Clearing previous clip...\n")
    
    -- Get SD3 track
    local track = reaper.GetTrack(0, 0)
    if not track then
        reaper.ShowConsoleMsg("ERROR: SD3 Track 1 not found\n")
        return false
    end
    
    -- Clear only items on this track
    local num_items = reaper.CountTrackMediaItems(track)
    reaper.ShowConsoleMsg("Found " .. num_items .. " items to clear\n")
    
    for i = num_items - 1, 0, -1 do
        local item = reaper.GetTrackMediaItem(track, i)
        if item then
            reaper.DeleteTrackMediaItem(track, item)
        end
    end
    
    reaper.UpdateArrange()
    reaper.ShowConsoleMsg("Previous clip cleared successfully\n")
    return true
end

-- Step 2: Install new clip at 1.3
function install_clip_at_position(midi_file)
    local midi_path = midi_folder .. "\\" .. midi_file
    reaper.ShowConsoleMsg("STEP 2: Installing " .. midi_file .. " at position 1.3...\n")
    
    -- Get SD3 track
    local track = reaper.GetTrack(0, 0)
    if not track then
        reaper.ShowConsoleMsg("ERROR: SD3 Track 1 not found\n")
        return false
    end
    
    -- Add new MIDI item at position 1.3
    local item = reaper.AddMediaItemToTrack(track)
    if not item then
        reaper.ShowConsoleMsg("ERROR: Could not create media item\n")
        return false
    end
    
    local take = reaper.AddTakeToMediaItem(item)
    if not take then
        reaper.ShowConsoleMsg("ERROR: Could not create take\n")
        return false
    end
    
    local source = reaper.PCM_Source_CreateFromFile(midi_path)
    if not source then
        reaper.ShowConsoleMsg("ERROR: Could not load MIDI file: " .. midi_path .. "\n")
        return false
    end
    
    reaper.SetMediaItemTake_Source(take, source)
    reaper.SetMediaItemPosition(item, 1.3, false)  -- Position at 1.3 seconds
    reaper.SetMediaItemLength(item, 2.7, false)    -- 2.7 seconds length
    
    -- Set time selection for render bounds
    reaper.GetSet_LoopTimeRange2(0, true, false, 0.0, 4.3, false)
    
    reaper.UpdateArrange()
    reaper.ShowConsoleMsg("Clip installed at position 1.3 successfully\n")
    return true
end

-- Step 3: Send Ctrl+Alt+R to open Render window
function open_render_window()
    reaper.ShowConsoleMsg("STEP 3: Sending Ctrl+Alt+R to open Render window...\n")
    
    -- Try the specific command for opening render dialog
    reaper.Main_OnCommand(40015, 0)  -- File: Render project to disk
    
    -- Brief pause for dialog to appear
    local start_time = reaper.time_precise()
    while (reaper.time_precise() - start_time) < 2 do
        reaper.defer(function() end)
    end
    
    reaper.ShowConsoleMsg("Render window command sent\n")
    return true
end

-- Step 4: Click "Render 1 file" button
function try_render_button()
    reaper.ShowConsoleMsg("=== Step 4: Trying FIXED render command ===")
    reaper.ShowConsoleMsg("CRITICAL FIX: Setting RENDER_FILE and RENDER_PATTERN first!")
    
    -- BREAKTHROUGH: Set render output path and filename BEFORE calling render command
    local output_dir = "D:\\DrumTracKAI_v1.1.7\\admin\\sd3_extracted_samples"
    local output_filename = "step_test_sample"  -- without .wav extension
    
    reaper.ShowConsoleMsg("Setting RENDER_FILE to: " .. output_dir)
    reaper.GetSetProjectInfo_String(0, 'RENDER_FILE', output_dir, true)
        method()
        local pause_start = reaper.time_precise()
        while (reaper.time_precise() - pause_start) < 0.5 do
            reaper.defer(function() end)
        end
    end
    
    reaper.ShowConsoleMsg("REAPER commands attempted. Now trying mouse click...\n")
    
    -- Create simple mouse click script
    local mouse_script_content = [[
#NoEnv
#SingleInstance Force
SendMode Input

; Simple mouse click for render button
Sleep, 1000

; Try clicking at common render button locations
Click, 500, 400
Sleep, 500
Click, 600, 450
Sleep, 500
Click, 550, 425
Sleep, 500

; Try Enter as backup
Send, {Enter}
Sleep, 1000

; Exit
ExitApp
]]
    
    -- Write mouse click script
    local script_path = "D:\\DrumTracKAI_v1.1.7\\admin\\reaper_projects\\test_mouse_click.ahk"
    local file = io.open(script_path, "w")
    if file then
        file:write(mouse_script_content)
        file:close()
        reaper.ShowConsoleMsg("Mouse click script created: " .. script_path .. "\n")
        
        -- Execute mouse click script
        reaper.ShowConsoleMsg("Executing mouse click script...\n")
        local cmd = '"' .. script_path .. '"'
        local result = os.execute(cmd)
        
        if result == 0 then
            reaper.ShowConsoleMsg("Mouse click script executed\n")
        else
            reaper.ShowConsoleMsg("Mouse click script execution failed\n")
        end
    else
        reaper.ShowConsoleMsg("Could not create mouse click script\n")
    end
    
    reaper.ShowConsoleMsg("All render button methods attempted (REAPER + mouse)\n")
    return true
end

-- Step 5: Close render progress window
function close_render_window()
    reaper.ShowConsoleMsg("STEP 5: Attempting to close render progress window...\n")
    
    -- Wait a moment for render to potentially start
    local start_time = reaper.time_precise()
    while (reaper.time_precise() - start_time) < 2 do
        reaper.defer(function() end)
    end
    
    -- Try Escape to close any dialogs
    reaper.Main_OnCommand(40001, 0)  -- Escape/Cancel
    
    reaper.ShowConsoleMsg("Close window command sent\n")
    return true
end

-- Wait for render completion
function wait_for_render_completion(output_path, timeout_seconds)
    reaper.ShowConsoleMsg("STEP 6: Waiting for render completion...\n")
    reaper.ShowConsoleMsg("Expected output: " .. output_path .. "\n")
    
    local start_time = reaper.time_precise()
    while (reaper.time_precise() - start_time) < timeout_seconds do
        if reaper.file_exists(output_path) then
            reaper.ShowConsoleMsg("SUCCESS: Output file created!\n")
            return true
        end
        
        -- Brief pause
        local pause_start = reaper.time_precise()
        while (reaper.time_precise() - pause_start) < 1 do
            reaper.defer(function() end)
        end
    end
    
    reaper.ShowConsoleMsg("No output file detected after " .. timeout_seconds .. " seconds\n")
    return false
end

-- Copy to database location
function copy_to_database(output_path, db_path)
    reaper.ShowConsoleMsg("STEP 7: Copying to database location...\n")
    
    local copy_cmd = 'copy "' .. output_path .. '" "' .. db_path .. '"'
    local result = os.execute(copy_cmd)
    if result == 0 then
        reaper.ShowConsoleMsg("Copied to database location successfully\n")
        return true
    else
        reaper.ShowConsoleMsg("WARNING: Failed to copy to database\n")
        return false
    end
end

-- Process single file with step-by-step dialogs
function process_file_step_by_step(midi_file)
    local short_name = generate_short_filename(midi_file)
    local output_path = output_local .. "\\" .. short_name
    local db_path = output_database .. "\\" .. short_name
    
    reaper.ShowConsoleMsg("\n=== Processing: " .. midi_file .. " -> " .. short_name .. " ===\n")
    
    -- Configure render settings
    reaper.GetSetProjectInfo_String(0, "RENDER_FILE", output_path, true)
    reaper.GetSetProjectInfo(0, "RENDER_BOUNDSFLAG", 1, true)  -- Time selection
    reaper.GetSetProjectInfo(0, "RENDER_CHANNELS", 2, true)    -- Stereo
    reaper.GetSetProjectInfo(0, "RENDER_SRATE", 48000, true)   -- 48kHz
    
    -- Step 1: Clear previous clip
    if not show_progress_dialog("Step 1", "Ready to clear previous clip?\n\nClick OK to proceed, Cancel to stop.") then
        return false
    end
    
    if not clear_previous_clip() then
        reaper.MB("Failed to clear previous clip!", "Error", 0)
        return false
    end
    
    -- Step 2: Install new clip
    if not show_progress_dialog("Step 2", "Ready to install new MIDI clip at position 1.3?\n\nFile: " .. midi_file .. "\n\nClick OK to proceed, Cancel to stop.") then
        return false
    end
    
    if not install_clip_at_position(midi_file) then
        reaper.MB("Failed to install MIDI clip!", "Error", 0)
        return false
    end
    
    -- Step 3: Open render window
    if not show_progress_dialog("Step 3", "Ready to open Render window (Ctrl+Alt+R)?\n\nClick OK to proceed, Cancel to stop.") then
        return false
    end
    
    if not open_render_window() then
        reaper.MB("Failed to open render window!", "Error", 0)
        return false
    end
    
    -- Step 4: Click render button
    if not show_progress_dialog("Step 4", "Ready to click 'Render 1 file' button?\n\nMake sure render dialog is open.\n\nClick OK to proceed, Cancel to stop.") then
        return false
    end
    
    if not click_render_button() then
        reaper.MB("Failed to click render button!", "Error", 0)
        return false
    end
    
    -- Step 5: Close render window
    if not show_progress_dialog("Step 5", "Ready to close render progress window?\n\nClick OK to proceed, Cancel to stop.") then
        return false
    end
    
    if not close_render_window() then
        reaper.MB("Failed to close render window!", "Error", 0)
        return false
    end
    
    -- Step 6: Wait for completion
    if not show_progress_dialog("Step 6", "Ready to wait for render completion?\n\nWill wait up to 30 seconds for output file.\n\nClick OK to proceed, Cancel to stop.") then
        return false
    end
    
    local render_success = wait_for_render_completion(output_path, 30)
    
    if render_success then
        -- Step 7: Copy to database
        if show_progress_dialog("Step 7", "Render successful! Ready to copy to database?\n\nOutput: " .. short_name .. "\n\nClick OK to proceed, Cancel to skip.") then
            copy_to_database(output_path, db_path)
        end
        
        reaper.MB("File processed successfully!\n\nOutput: " .. short_name, "Success", 0)
        return true
    else
        reaper.MB("Render failed - no output file created!\n\nExpected: " .. short_name, "Render Failed", 0)
        return false
    end
end

-- Main step-by-step function
function run_step_by_step_test()
    reaper.ShowConsoleMsg("Starting step-by-step test with progress dialogs...\n")
    
    -- Create output directories
    os.execute('mkdir "' .. output_local .. '" 2>nul')
    os.execute('mkdir "' .. output_database .. '" 2>nul')
    
    local success_count = 0
    local total_files = #test_files
    
    -- Show initial dialog
    if not show_progress_dialog("SD3 Step-by-Step Test", "Ready to start step-by-step batch processing?\n\nWill process " .. total_files .. " test files with progress dialogs.\n\nClick OK to start, Cancel to abort.") then
        reaper.ShowConsoleMsg("Test cancelled by user\n")
        return
    end
    
    for i, midi_file in ipairs(test_files) do
        reaper.ShowConsoleMsg("\n=== File " .. i .. "/" .. total_files .. " ===\n")
        
        -- Show file progress dialog
        if not show_progress_dialog("File " .. i .. "/" .. total_files, "Ready to process next file?\n\nFile: " .. midi_file .. "\n\nClick OK to proceed, Cancel to stop batch.") then
            reaper.ShowConsoleMsg("Batch stopped by user at file " .. i .. "\n")
            break
        end
        
        -- Process file with step-by-step dialogs
        if process_file_step_by_step(midi_file) then
            success_count = success_count + 1
        end
    end
    
    -- Final results
    reaper.ShowConsoleMsg("\n=== STEP-BY-STEP TEST COMPLETE ===\n")
    reaper.ShowConsoleMsg("Processed: " .. success_count .. "/" .. total_files .. " files\n")
    
    reaper.MB("Step-by-step test complete!\n\nProcessed: " .. success_count .. "/" .. total_files .. " files\n\nCheck console for detailed logs.", "Test Complete", 0)
end

-- Export function
_G.run_step_by_step_test = run_step_by_step_test

-- Show instructions
reaper.ShowConsoleMsg("\n=== STEP-BY-STEP TEST INSTRUCTIONS ===\n")
reaper.ShowConsoleMsg("This script will process each file with progress dialogs between steps\n")
reaper.ShowConsoleMsg("You can observe each step and confirm it's working correctly\n")
reaper.ShowConsoleMsg("Click OK to proceed with each step, or Cancel to stop\n")
reaper.ShowConsoleMsg("\nScript will auto-start in 3 seconds...\n")

-- Auto-start after brief delay
local start_time = reaper.time_precise()
while (reaper.time_precise() - start_time) < 3 do
    reaper.defer(function() end)
end

reaper.ShowConsoleMsg("Starting step-by-step test now!\n")
run_step_by_step_test()
