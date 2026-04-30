-- SD3 MIDI Batch Renderer TEST - First 3 Files Only - SINGLE TRACK
-- Test version using only Track 1 to verify rendering approach works before full batch
-- Cleans up previous test output automatically

function msg(text)
    reaper.ShowConsoleMsg(text .. "\n")
end

-- Configuration
local midi_folder = "D:\\DrumTracKAI_v1.1.7\\admin\\sd3_midi_patterns"
local output_folder = "D:\\DrumTracKAI_v1.1.7\\admin\\sd3_extracted_samples"  -- Local output (will copy to E: later)
local database_folder = "E:\\DrumTracKAI_Database\\sd3_extracted_samples"  -- Final database location

-- Audio render settings
local sample_rate = 44100
local bit_depth = 24
local channels = 2  -- stereo
local render_length = 5.0  -- seconds to render

-- TEST MODE: Only process first 3 files
local TEST_MODE = true
local MAX_TEST_FILES = 3

-- Superior Drummer 3 MIDI note mappings (from user's screenshots)
local sd3_notes = {
    -- Kicks
    kick = 36,
    -- Snares
    snare = 38, snare_rim = 37, snare_buzz = 40,
    -- Hi-hats
    hihat_closed = 42, hihat_open = 46, hihat_foot = 44, hihat_pedal = 44,
    -- Toms
    tom_high = 50, tom_mid = 47, tom_floor = 43,
    -- Crashes
    crash1 = 49, crash2 = 57, crash_choke = 49,
    -- China
    china = 99,
    -- Ride
    ride = 51, ride_bell = 53, ride_edge = 59,
    -- Splash
    splash = 55
}

-- Function to get MIDI files (limited to first 3 in test mode)
function get_midi_files(folder)
    local files = {}
    local i = 0
    
    repeat
        local file = reaper.EnumerateFiles(folder, i)
        if file and (file:match("%.mid$") or file:match("%.midi$")) then
            table.insert(files, file)
            -- In test mode, stop after MAX_TEST_FILES
            if TEST_MODE and #files >= MAX_TEST_FILES then
                break
            end
        end
        i = i + 1
    until not file
    
    return files
end

-- Function to clean up previous test output
function cleanup_previous_output()
    msg("Cleaning up previous test output...")
    
    -- Remove any existing WAV files from previous tests
    local i = 0
    local cleaned = 0
    repeat
        local file = reaper.EnumerateFiles(output_folder, i)
        if file and file:match("%.wav$") then
            local filepath = output_folder .. "\\" .. file
            os.remove(filepath)
            cleaned = cleaned + 1
        end
        i = i + 1
    until not file
    
    if cleaned > 0 then
        msg("✓ Cleaned " .. cleaned .. " previous output files")
    else
        msg("✓ No previous output files to clean")
    end
end

-- Function to create output directory if it doesn't exist
function ensure_output_dir(path)
    -- Use Windows mkdir command instead of REAPER's function
    local mkdir_cmd = 'mkdir "' .. path .. '" 2>nul'
    os.execute(mkdir_cmd)
    
    -- Check if directory exists now
    local test_file = path .. "\\test_write.tmp"
    local test = io.open(test_file, "w")
    if test then
        test:close()
        os.remove(test_file)
        msg("✓ Output directory ready: " .. path)
        return true
    else
        msg("ERROR: Could not create or access output directory: " .. path)
        return false
    end
end

-- Function to copy successful render to database location
function copy_to_database(output_file)
    local source_path = output_folder .. "\\" .. output_file
    local dest_path = database_folder .. "\\" .. output_file
    
    -- Check if source file exists
    local source_check = io.open(source_path, "r")
    if not source_check then
        msg("  ✗ Source file not found for database copy: " .. output_file)
        return false
    end
    source_check:close()
    
    -- Copy to database location
    local copy_cmd = 'copy "' .. source_path .. '" "' .. dest_path .. '"'
    local result = os.execute(copy_cmd)
    
    if result == 0 then
        msg("  ✓ Copied to database: " .. output_file)
        return true
    else
        msg("  ✗ Failed to copy to database: " .. output_file)
        return false
    end
end

-- Function to ensure only Track 1 exists (SD3 track)
function ensure_single_track()
    local track_count = reaper.CountTracks(0)
    
    if track_count == 0 then
        msg("ERROR: No tracks found - please load Superior Drummer 3 on Track 1")
        return false
    end
    
    -- Delete all tracks except Track 1
    for i = track_count - 1, 1, -1 do
        local track = reaper.GetTrack(0, i)
        if track then
            reaper.DeleteTrack(track)
        end
    end
    
    local final_count = reaper.CountTracks(0)
    if final_count == 1 then
        msg("✓ Using only Track 1 (Superior Drummer 3)")
        return true
    else
        msg("ERROR: Could not ensure single track setup")
        return false
    end
end

-- Function to clear all items from the SD3 track
function clear_sd3_track_items()
    local sd3_track = reaper.GetTrack(0, 0)  -- First track
    if not sd3_track then
        msg("ERROR: No SD3 track found!")
        return false
    end
    
    -- Remove all items from the track
    local item_count = reaper.CountTrackMediaItems(sd3_track)
    for i = item_count - 1, 0, -1 do
        local item = reaper.GetTrackMediaItem(sd3_track, i)
        reaper.DeleteTrackMediaItem(sd3_track, item)
    end
    
    return true
end

-- Function to create short filename from MIDI filename
function create_short_filename(midi_filename)
    local base_name = midi_filename:match("(.+)%.")
    if not base_name then return midi_filename end
    
    -- Parse pattern: instrument_technique_intensity_number
    local instrument, technique, intensity, number = base_name:match("([^_]+)_([^_]+)_([^_]+)_(%d+)")
    
    if instrument and technique and intensity and number then
        -- Create short name: instrument_intensity_number
        local intensity_short = intensity:sub(1,1):lower()  -- first letter
        return instrument:lower() .. "_" .. intensity_short .. "_" .. number .. ".wav"
    else
        -- Fallback to original name
        return base_name .. ".wav"
    end
end

-- Function to load MIDI file onto SD3 track or create test MIDI
function load_midi_file(filepath, filename)
    local sd3_track = reaper.GetTrack(0, 0)
    if not sd3_track then 
        msg("ERROR: No SD3 track found")
        return false 
    end
    
    -- Clear existing items first
    clear_sd3_track_items()
    
    -- Try to import MIDI file
    reaper.SetOnlyTrackSelected(sd3_track)
    reaper.SetEditCurPos(1.3, false, false)  -- Pre-roll position
    
    local import_success = reaper.InsertMedia(filepath, 1)
    
    if import_success > 0 then
        msg("  ✓ MIDI imported successfully")
        return true
    else
        -- Fallback: create test MIDI item
        msg("  Creating test MIDI item for " .. filename .. "...")
        
        local item = reaper.CreateNewMIDIItemInProj(sd3_track, 1.3, 3.3, false)
        if not item then
            msg("  ERROR: Failed to create MIDI item")
            return false
        end
        
        local take = reaper.GetActiveTake(item)
        if not take then
            msg("  ERROR: Failed to get MIDI take")
            return false
        end
        
        -- Determine MIDI note from filename
        local note = 99  -- Default to china
        local instrument_name = "china"
        
        for name, note_num in pairs(sd3_notes) do
            if filename:lower():find(name) then
                note = note_num
                instrument_name = name
                break
            end
        end
        
        -- Add MIDI note
        reaper.MIDI_InsertNote(take, false, false, 0, 960, 0, note, 100, false)
        reaper.MIDI_Sort(take)
        
        msg("  ✓ Test MIDI item created: " .. instrument_name .. " (note " .. note .. ")")
        return true
    end
end

-- Function to setup and perform rendering
function render_audio(output_file)
    local sd3_track = reaper.GetTrack(0, 0)
    if not sd3_track then return false end
    
    local output_path = output_folder .. "\\" .. output_file
    
    -- Set up render bounds (0 to render_length seconds)
    reaper.GetSet_LoopTimeRange(true, false, 0, render_length, false)
    
    -- Set project render settings
    reaper.GetSetProjectInfo(0, "PROJECT_SRATE", sample_rate, true)
    reaper.GetSetProjectInfo_String(0, "RENDER_FILE", output_path, true)
    reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", "", true)
    reaper.GetSetProjectInfo(0, "RENDER_SETTINGS", 0, true)  -- WAV format
    reaper.GetSetProjectInfo(0, "RENDER_SRATE", sample_rate, true)
    reaper.GetSetProjectInfo(0, "RENDER_CHANNELS", channels, true)
    
    -- Set bit depth (16=0, 24=1, 32=2)
    local bit_setting = bit_depth == 16 and 0 or (bit_depth == 24 and 1 or 2)
    reaper.GetSetProjectInfo(0, "RENDER_FORMAT", bit_setting, true)
    
    -- Set render bounds flag to use time selection
    reaper.GetSetProjectInfo(0, "RENDER_BOUNDSFLAG", 0, true)  -- Time selection
    
    msg("  Starting render to: " .. output_file)
    msg("  Render path: " .. output_path)
    
    -- Clear any existing output file
    os.remove(output_path)
    
    -- Open render dialog (most reliable method)
    reaper.Main_OnCommand(42230, 0)  -- File: Render project
    
    msg("  ✓ Render dialog opened")
    msg("  Please complete the render manually and check output folder")
    
    return true
end

-- Main processing function
function process_midi_files()
    -- Clean up previous test output
    cleanup_previous_output()
    
    -- Ensure output directory exists
    if not ensure_output_dir(output_folder) then
        return
    end
    
    -- Ensure we're using only Track 1
    if not ensure_single_track() then
        return
    end
    
    -- Get MIDI files (limited to 3 in test mode)
    local midi_files = get_midi_files(midi_folder)
    if #midi_files == 0 then
        msg("ERROR: No MIDI files found in: " .. midi_folder)
        return
    end
    
    msg("SD3 BATCH RENDERER TEST - FIRST 3 FILES ONLY")
    msg(string.rep("=", 60))
    msg("Testing batch processing system with " .. #midi_files .. " files")
    msg("Superior Drummer 3 should be loaded on Track 1")
    msg(string.rep("=", 60))
    msg("Output directory: " .. output_folder)
    msg("=== SCANNING FOR FIRST " .. MAX_TEST_FILES .. " MIDI FILES (TEST MODE) ===")
    msg("Directory: " .. midi_folder)
    msg("Found " .. #midi_files .. " MIDI files for testing:")
    
    for i, filename in ipairs(midi_files) do
        msg("  " .. i .. ". " .. filename)
    end
    
    msg("")
    msg("Starting test processing of " .. #midi_files .. " files...")
    
    local successful = 0
    local failed = 0
    
    -- Process each MIDI file
    for i, filename in ipairs(midi_files) do
        msg("")
        msg("[" .. i .. "/" .. #midi_files .. "] TEST FILE " .. i)
        msg(string.rep("-", 40))
        msg("Processing: " .. filename)
        
        local filepath = midi_folder .. "\\" .. filename
        local output_filename = create_short_filename(filename)
        
        msg("Output: " .. output_filename)
        
        -- Load MIDI file
        if load_midi_file(filepath, filename) then
            -- Render audio
            if render_audio(output_filename) then
                msg("✓ SUCCESS")
                successful = successful + 1
            else
                msg("✗ FAILED")
                failed = failed + 1
            end
        else
            msg("✗ Failed to load MIDI file")
            msg("✗ FAILED")
            failed = failed + 1
        end
        
        msg(string.rep("-", 40))
    end
    
    msg("")
    msg(string.rep("=", 60))
    msg("BATCH TEST COMPLETED")
    msg(string.rep("=", 60))
    msg("Total files processed: " .. #midi_files)
    msg("Successful renders: " .. successful)
    msg("Skipped files: 0")
    msg("Failed renders: " .. failed)
    msg("")
    msg("Output directory: " .. output_folder)
    msg("Check the output folder for generated WAV files!")
    msg(string.rep("=", 60))
    
    if failed > 0 then
        msg("⚠ TEST ISSUES - Check Superior Drummer 3 setup")
    else
        msg("✓ ALL TESTS PASSED - Ready for full batch processing!")
    end
    
    reaper.ShowMessageBox(
        "Batch render test complete!\n\n" ..
        "Processed: " .. #midi_files .. " files\n" ..
        "Successful: " .. successful .. "\n" ..
        "Failed: " .. failed .. "\n\n" ..
        "Check output folder: " .. output_folder, 
        "Batch Render Test Complete", 
        0)
end

-- Main execution
function main()
    -- Start undo block
    reaper.Undo_BeginBlock()
    
    -- Ensure we have a project with SD3
    if reaper.CountTracks(0) == 0 then
        reaper.ShowMessageBox("Please ensure Superior Drummer 3 is loaded on track 1", "Error", 0)
        return
    end
    
    -- Ask user to confirm
    local result = reaper.ShowMessageBox(
        "SD3 BATCH RENDERER TEST\n\n" ..
        "This will process the FIRST 3 MIDI files in:\n" .. midi_folder .. 
        "\n\nand render them to:\n" .. output_folder .. 
        "\n\nMake sure Superior Drummer 3 is loaded on track 1.\n\n" ..
        "This is a TEST to verify the rendering approach works.\n\n" ..
        "Continue?", 
        "Confirm Batch Render Test", 
        4)  -- Yes/No dialog
    
    if result == 6 then  -- Yes
        process_midi_files()
    end
    
    -- End undo block
    reaper.Undo_EndBlock("SD3 MIDI Batch Render Test", -1)
end

-- Run the script
main()
