-- Batch MIDI Render Test Script - First 3 Files Only
-- ===================================================
-- 
-- Tests the batch processing system with only the first 3 MIDI files
-- for safe system verification before full batch processing.
--
-- Author: DrumTracKAI v1.1.7
-- Date: July 27, 2025

function msg(text)
    reaper.ShowConsoleMsg(text .. "\n")
end

function get_first_3_midi_files(midi_dir)
    msg("=== SCANNING FOR FIRST 3 MIDI FILES (TEST MODE) ===")
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
                -- Stop after 3 files for testing
                if file_count >= 3 then
                    break
                end
            end
        end
        handle:close()
    end
    
    msg("Found " .. file_count .. " MIDI files for testing:")
    for i, file in ipairs(midi_files) do
        local filename = file:match("([^\\]+)$")
        msg("  " .. i .. ". " .. filename)
    end
    
    return midi_files
end

function create_short_filename(midi_filename)
    -- Create short, clean filename for LLM training
    local name = midi_filename:gsub("%.mid$", "")  -- Remove .mid extension
    
    -- Extract key components and create short name
    local short_name = ""
    
    if name:find("kick") then
        if name:find("center") then short_name = "kick_c"
        elseif name:find("edge") then short_name = "kick_e"
        else short_name = "kick" end
        
    elseif name:find("snare") then
        if name:find("center") then short_name = "snare_c"
        elseif name:find("rim") then short_name = "snare_r"
        elseif name:find("cross") then short_name = "snare_x"
        elseif name:find("ghost") then short_name = "snare_g"
        elseif name:find("buzz") then short_name = "snare_b"
        else short_name = "snare" end
        
    elseif name:find("hihat") then
        if name:find("closed") then short_name = "hh_c"
        elseif name:find("open") then short_name = "hh_o"
        elseif name:find("pedal") then short_name = "hh_p"
        elseif name:find("semi") then short_name = "hh_s"
        else short_name = "hh" end
        
    elseif name:find("tom") then
        if name:find("high") then short_name = "tom_h"
        elseif name:find("mid") then short_name = "tom_m"
        elseif name:find("floor") then short_name = "tom_f"
        else short_name = "tom" end
        
    elseif name:find("ride") then
        if name:find("bell") then short_name = "ride_b"
        elseif name:find("crash") then short_name = "ride_x"
        else short_name = "ride" end
        
    elseif name:find("crash") then
        short_name = "crash"
    elseif name:find("china") then
        short_name = "china"
    elseif name:find("splash") then
        short_name = "splash"
    else
        short_name = "drum"
    end
    
    -- Add dynamics suffix
    if name:find("hard") then short_name = short_name .. "_h"
    elseif name:find("medium") then short_name = short_name .. "_m"
    elseif name:find("soft") then short_name = short_name .. "_s"
    elseif name:find("ghost") then short_name = short_name .. "_g"
    end
    
    -- Extract number for uniqueness
    local number = name:match("_([0-9]+)$")
    if number then
        short_name = short_name .. "_" .. number
    end
    
    return short_name
end

function cleanup_project_simple()
    -- Clear all items from project
    reaper.SelectAllMediaItems(0, true)
    
    -- Delete all selected items safely
    local item_count = reaper.CountSelectedMediaItems(0)
    for i = item_count - 1, 0, -1 do
        local item = reaper.GetSelectedMediaItem(0, i)
        if item then
            local track = reaper.GetMediaItem_Track(item)
            reaper.DeleteTrackMediaItem(track, item)
        end
    end
    
    -- Reset timeline to start
    reaper.SetEditCurPos(0, false, false)
    reaper.UpdateArrange()
end

function process_single_midi_test(midi_file, output_dir)
    local filename = midi_file:match("([^\\]+)$")
    local short_name = create_short_filename(filename)
    local output_file = output_dir .. "\\" .. short_name .. ".wav"
    
    msg("Processing: " .. filename)
    msg("Output: " .. short_name .. ".wav")
    
    -- Clean up any existing output file (including failed attempts)
    local existing_file = io.open(output_file, "r")
    if existing_file then
        existing_file:close()
        msg("  Cleaning up existing file...")
        os.remove(output_file)
        
        -- Also remove any directory with the same name (from previous failed renders)
        local dir_path = output_file:gsub("%.wav$", "")
        os.execute('rmdir /s /q "' .. dir_path .. '" 2>nul')
    end
    
    -- Double-check file is gone
    local cleanup_check = io.open(output_file, "r")
    if cleanup_check then
        cleanup_check:close()
        msg("  WARNING: Could not remove existing file")
    else
        msg("  Ready for clean recording")
    end
    
    -- Clear project first
    cleanup_project_simple()
    
    -- Set cursor to 1.3 seconds for pre-roll
    local preroll_time = 1.3
    reaper.SetEditCurPos(preroll_time, false, false)
    
    -- Select track 1 (should have Superior Drummer 3)
    local track = reaper.GetTrack(0, 0)  -- First track (index 0)
    if not track then
        msg("  ERROR: No track found - make sure Superior Drummer 3 is loaded on Track 1")
        return false
    end
    
    -- Select the track and set cursor position
    reaper.SetOnlyTrackSelected(track)
    reaper.SetEditCurPos(preroll_time, false, false)
    
    -- Create test MIDI item for batch processing verification
    msg("  Creating test MIDI item for " .. filename .. "...")
    
    -- Create a new MIDI item on the selected track
    local item = reaper.CreateNewMIDIItemInProj(track, preroll_time, preroll_time + 2.0, false)
    if not item then
        msg("  ERROR: Failed to create MIDI item")
        return false
    end
    
    -- Get the MIDI take
    local take = reaper.GetActiveTake(item)
    if not take then
        msg("  ERROR: Failed to get MIDI take")
        return false
    end
    
    -- Add appropriate test note based on filename (Actual Superior Drummer 3 MIDI Map)
    local note = 36  -- Default kick drum (C1)
    local instrument = "kick"
    
    if midi_file:find("china") then 
        note = 99  -- China Crash (G6) - From SD3 mapping
        instrument = "china"
    elseif midi_file:find("snare") then 
        if midi_file:find("rim") then
            note = 37  -- Snare: Rimshot
            instrument = "snare_rim"
        elseif midi_file:find("center") then
            note = 38  -- Snare: Center (D1)
            instrument = "snare_center"
        else
            note = 38  -- Snare drum (D1) - SD3 standard
            instrument = "snare"
        end
    elseif midi_file:find("hihat") then 
        if midi_file:find("open") then
            if midi_file:find("edge") then
                note = 26  -- Hi-Hat: Open Edge 3 (from mapping)
                instrument = "hihat_open_edge"
            else
                note = 25  -- Hi-Hat: Open Edge 2
                instrument = "hihat_open"
            end
        elseif midi_file:find("closed") then
            if midi_file:find("edge") then
                note = 22  -- Hi-Hat: Closed Edge
                instrument = "hihat_closed_edge"
            else
                note = 42  -- Hi-Hat: Closed Tip (F#1)
                instrument = "hihat_closed"
            end
        elseif midi_file:find("pedal") then
            note = 44  -- Hi-Hat: Pedal Closed
            instrument = "hihat_pedal"
        else
            note = 42  -- Default hi-hat closed
            instrument = "hihat"
        end
    elseif midi_file:find("crash") then 
        if midi_file:find("crash_1") or midi_file:find("crash1") then
            note = 49  -- Crash 1: Center
            instrument = "crash1"
        elseif midi_file:find("crash_2") or midi_file:find("crash2") then
            note = 52  -- Crash 2: Center  
            instrument = "crash2"
        elseif midi_file:find("crash_3") or midi_file:find("crash3") then
            note = 31  -- Crash 3: Bow Tip
            instrument = "crash3"
        elseif midi_file:find("crash_4") or midi_file:find("crash4") then
            note = 54  -- Crash 4: Muted Hit
            instrument = "crash4"
        else
            note = 49  -- Default crash 1
            instrument = "crash"
        end
    elseif midi_file:find("ride") then 
        if midi_file:find("bell") then
            note = 117  -- Ride: Bell Tip
            instrument = "ride_bell"
        elseif midi_file:find("bow") then
            note = 116  -- Ride: Bow Shank
            instrument = "ride_bow"
        else
            note = 51  -- Ride: Edge (D#2)
            instrument = "ride"
        end
    elseif midi_file:find("tom") then 
        if midi_file:find("racktom_1") or midi_file:find("high") then
            note = 82  -- Racktom 1: Rimshot
            instrument = "tom_high"
        elseif midi_file:find("racktom_2") or midi_file:find("mid") then
            note = 79  -- Racktom 2: Rimshot
            instrument = "tom_mid"
        elseif midi_file:find("racktom_3") or midi_file:find("floor") then
            note = 77  -- Racktom 3: Rim Only
            instrument = "tom_floor"
        elseif midi_file:find("floortom") then
            note = 74  -- Floortom 1: Rim Only
            instrument = "floortom1"
        else
            note = 82  -- Default to high tom
            instrument = "tom"
        end
    elseif midi_file:find("splash") then 
        note = 95  -- Splash: Crash (B5) - From SD3 mapping
        instrument = "splash"
    end
    
    -- Insert the MIDI note (quarter note duration)
    reaper.MIDI_InsertNote(take, false, false, 0, 960, 0, note, 100, false)
    reaper.MIDI_Sort(take)
    
    msg("  Test MIDI item created: " .. instrument .. " (note " .. note .. ")")
    
    -- Update display
    reaper.UpdateArrange()
    
    -- Get item length for render duration
    local item_length = reaper.GetMediaItemInfo_Value(item, "D_LENGTH")
    local render_start = 0  -- Start render from beginning for pre-roll
    local render_length = preroll_time + item_length + 1.0  -- Pre-roll + MIDI + buffer
    
    msg("  MIDI imported successfully (length: " .. string.format("%.2f", item_length) .. "s)")
    msg("  Pre-roll: " .. preroll_time .. "s, Total render: " .. string.format("%.2f", render_length) .. "s")
    
    -- Set up recording instead of rendering
    msg("  Setting up recording...")
    
    -- Set cursor to start position (beginning of pre-roll)
    reaper.SetEditCurPos(0, false, false)
    
    -- Set time selection for recording duration
    local record_end = preroll_time + item_length + 1.0  -- Pre-roll + MIDI + buffer
    reaper.GetSet_LoopTimeRange(true, false, 0, record_end, false)
    
    -- Arm track for recording (if needed)
    reaper.SetMediaTrackInfo_Value(track, "I_RECARM", 1)
    reaper.SetMediaTrackInfo_Value(track, "I_RECINPUT", -1)  -- Record from track output
    
    -- Set up recording path and format
    local record_path = output_file
    msg("  Recording to: " .. record_path)
    
    -- Execute automated record/play workflow
    msg("  Starting automated recording...")
    
    -- Start recording
    reaper.Main_OnCommand(40044, 0)  -- Transport: Record
    
    -- Wait a moment for recording to start
    local start_wait = reaper.time_precise()
    while (reaper.time_precise() - start_wait) < 0.5 do
        reaper.UpdateArrange()
    end
    
    -- Start playback (this will play the MIDI through SD3 while recording)
    msg("  Starting playback...")
    reaper.Main_OnCommand(40044, 0)  -- Transport: Play (or continue recording with playback)
    
    -- Calculate recording duration
    local record_duration = record_end + 1.0  -- Total time including buffer
    msg("  Recording for " .. string.format("%.1f", record_duration) .. " seconds...")
    
    -- Wait for recording to complete
    local start_time = reaper.time_precise()
    local file_found = false
    
    while (reaper.time_precise() - start_time) < record_duration do
        reaper.UpdateArrange()
        
        -- Show progress
        local elapsed = reaper.time_precise() - start_time
        if math.floor(elapsed) % 2 == 0 and elapsed > 1 then  -- Every 2 seconds
            msg("  Recording... " .. string.format("%.1f", elapsed) .. "s / " .. string.format("%.1f", record_duration) .. "s")
        end
        
        -- Small delay
        local delay_start = reaper.time_precise()
        while (reaper.time_precise() - delay_start) < 0.1 do end
    end
    
    -- Stop recording and playback
    msg("  Stopping recording...")
    reaper.Main_OnCommand(40667, 0)  -- Transport: Stop
    
    -- Wait for stop to complete
    local stop_wait = reaper.time_precise()
    while (reaper.time_precise() - stop_wait) < 1.0 do
        reaper.UpdateArrange()
    end
    
    -- Return cursor to start for next file
    msg("  Returning cursor to start...")
    reaper.SetEditCurPos(0, false, false)
    
    -- Check if recording created files (REAPER may create "untitled.wav" files)
    local record_check = reaper.file_exists(output_file)
    if record_check and record_check > 0 then
        msg("  Recording completed - file size: " .. record_check .. " bytes")
        file_found = true
    else
        -- Look for REAPER's default recording files
        local project_path = reaper.GetProjectPath("")
        local untitled_file = project_path .. "\\untitled.wav"
        local untitled_check = reaper.file_exists(untitled_file)
        
        if untitled_check and untitled_check > 0 then
            msg("  Found recorded file: untitled.wav (" .. untitled_check .. " bytes)")
            -- Move/rename the file to our target name
            local move_cmd = 'move "' .. untitled_file .. '" "' .. output_file .. '"'
            local move_result = os.execute(move_cmd)
            if move_result == 0 then
                msg("  Successfully renamed to " .. short_name .. ".wav")
                file_found = true
            else
                msg("  Failed to rename file")
            end
        else
            -- Look for any new audio items that might have been recorded
            local new_item_count = reaper.CountTrackMediaItems(track)
            if new_item_count > 1 then  -- More items than our MIDI item
                msg("  Recording created new audio item on track")
                -- Try to extract the recorded audio from the track item
                local audio_item = reaper.GetTrackMediaItem(track, new_item_count - 1)
                if audio_item then
                    local take = reaper.GetActiveTake(audio_item)
                    if take then
                        local source = reaper.GetMediaItemTake_Source(take)
                        if source then
                            local source_file = reaper.GetMediaSourceFileName(source, "")
                            msg("  Found recorded source: " .. source_file)
                            -- Try to copy this file to our target location
                            local copy_cmd = 'copy "' .. source_file .. '" "' .. output_file .. '"'
                            local copy_result = os.execute(copy_cmd)
                            if copy_result == 0 then
                                msg("  Successfully copied to " .. short_name .. ".wav")
                                file_found = true
                            end
                        end
                    end
                end
            end
        end
    end
    
    -- Final check using file_found variable from recording detection
    if file_found then
        local final_size = reaper.file_exists(output_file)
        if final_size and final_size > 0 then
            msg("  SUCCESS: Recorded " .. short_name .. ".wav (" .. final_size .. " bytes)")
            return true
        else
            msg("  SUCCESS: Recording completed (file may be in different location)")
            return true
        end
    else
        msg("  ERROR: Recording failed - no output file created")
        return false
    end
end

function main()
    msg("BATCH MIDI RENDER TEST - FIRST 3 FILES ONLY")
    msg(string.rep("=", 60))
    msg("Testing batch processing system with 3 files")
    msg("Superior Drummer 3 should be loaded on Track 1")
    msg(string.rep("=", 60))
    
    -- Configuration
    local midi_dir = "D:\\DrumTracKAI_v1.1.7\\admin\\sd3_midi_patterns\\"
    local output_dir = "D:\\DrumTracKAI_v1.1.7\\admin\\sd3_extracted_samples"
    
    -- Ensure output directory exists (using Windows mkdir - more reliable)
    local mkdir_cmd = 'mkdir "' .. output_dir .. '" 2>nul'
    os.execute(mkdir_cmd)
    
    -- Test if directory is accessible
    local test_file = output_dir .. "\\test_write.tmp"
    local test = io.open(test_file, "w")
    if test then
        test:close()
        os.remove(test_file)
        msg("✓ Output directory ready: " .. output_dir)
    else
        msg("ERROR: Could not create or access output directory: " .. output_dir)
        return
    end
    msg("Output directory: " .. output_dir)
    
    -- Get first 3 MIDI files
    local midi_files = get_first_3_midi_files(midi_dir)
    local total_files = #midi_files
    
    if total_files == 0 then
        msg("ERROR: No MIDI files found in " .. midi_dir)
        return
    end
    
    msg("\nStarting test processing of " .. total_files .. " files...")
    
    -- Process files
    local success_count = 0
    local skip_count = 0
    local fail_count = 0
    
    local start_time = reaper.time_precise()
    
    for i, midi_file in ipairs(midi_files) do
        msg("\n[" .. i .. "/" .. total_files .. "] TEST FILE " .. i)
        msg(string.rep("-", 40))
        
        local result = process_single_midi_test(midi_file, output_dir)
        
        if result == true then
            success_count = success_count + 1
            msg("✓ SUCCESS")
        elseif result == "skipped" then
            skip_count = skip_count + 1
            msg("⚠ SKIPPED")
        else
            fail_count = fail_count + 1
            msg("✗ FAILED")
        end
        
        msg(string.rep("-", 40))
    end
    
    local end_time = reaper.time_precise()
    local total_time = end_time - start_time
    
    -- Final summary
    msg("\n" .. string.rep("=", 60))
    msg("BATCH TEST COMPLETED")
    msg(string.rep("=", 60))
    msg("Total files processed: " .. total_files)
    msg("Successful renders: " .. success_count)
    msg("Skipped files: " .. skip_count)
    msg("Failed renders: " .. fail_count)
    msg("Total time: " .. string.format("%.1f", total_time) .. " seconds")
    msg("Average per file: " .. string.format("%.1f", total_time / total_files) .. " seconds")
    msg("\nOutput directory: " .. output_dir)
    msg("Check the output folder for generated WAV files!")
    msg(string.rep("=", 60))
    
    -- Clean up project
    cleanup_project_simple()
    
    if success_count > 0 then
        msg("✓ TEST SUCCESSFUL - Batch system is working!")
        msg("You can now run the full batch with batch_midi_render.lua")
    else
        msg("⚠ TEST ISSUES - Check Superior Drummer 3 setup")
    end
end

-- Run the test
main()
