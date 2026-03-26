-- SD3 MIDI Batch Renderer for DrumTracKAI Training Data
-- Converted to working ReaScript with recording approach
-- This script loads MIDI files sequentially and records them as audio

function msg(text)
    reaper.ShowConsoleMsg(text .. "\n")
end

-- Configuration
local midi_folder = "D:\\DrumTracKAI_v1.1.7\\admin\\sd3_midi_patterns"
local output_folder = "E:\\DrumTracKAI_Database\\sd3_extracted_samples"  -- Database location on E: drive

-- Audio render settings
local sample_rate = 44100
local bit_depth = 24
local channels = 2  -- stereo
local render_length = 5.0  -- seconds to render

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

-- Function to get all MIDI files in the folder
function get_midi_files(folder)
    local files = {}
    local i = 0
    
    repeat
        local file = reaper.EnumerateFiles(folder, i)
        if file and (file:match("%.mid$") or file:match("%.midi$")) then
            table.insert(files, file)
        end
        i = i + 1
    until not file
    
    return files
end

-- Function to create output directory if it doesn't exist
function ensure_output_dir(path)
    local result = reaper.RecursiveCreateDirectory(path, 0)
    if result == 0 then
        msg("ERROR: Could not create output directory: " .. path)
        return false
    end
    return true
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
    
    -- Clear any existing output file
    os.remove(output_path)
    
    -- Open render dialog (most reliable method)
    reaper.Main_OnCommand(42230, 0)  -- File: Render project
    
    -- Wait a moment for render dialog to process
    local wait_count = 0
    local function check_render_complete()
        wait_count = wait_count + 1
        
        -- Check if file was created
        local check = io.open(output_path, "r")
        if check then
            check:close()
            local file_size = reaper.file_exists(output_path)
            if file_size and file_size > 0 then
                msg("  ✓ SUCCESS: Rendered " .. output_file .. " (" .. file_size .. " bytes)")
                return true
            end
        end
        
        if wait_count < 30 then  -- Wait up to 30 seconds
            if wait_count % 5 == 0 then
                msg("  Waiting for render... " .. wait_count .. "s")
            end
            reaper.defer(check_render_complete)
        else
            msg("  ✗ Render timeout - file not created after 30 seconds")
            return false
        end
    end
    
    -- Start checking for render completion
    reaper.defer(check_render_complete)
    
    return true  -- Return true to continue, actual success checked in defer
end

-- Main processing function
function process_midi_files()
    -- Ensure output directory exists
    if not ensure_output_dir(output_folder) then
        return
    end
    
    -- Get all MIDI files
    local midi_files = get_midi_files(midi_folder)
    if #midi_files == 0 then
        msg("ERROR: No MIDI files found in: " .. midi_folder)
        return
    end
    
    msg("SD3 BATCH RENDERER - RENDER MODE")
    msg(string.rep("=", 50))
    msg("Found " .. #midi_files .. " MIDI files to process")
    msg("Output directory: " .. output_folder)
    msg(string.rep("=", 50))
    
    local successful = 0
    local failed = 0
    
    -- Process each MIDI file
    for i, filename in ipairs(midi_files) do
        msg("")
        msg("[" .. i .. "/" .. #midi_files .. "] Processing: " .. filename)
        
        local filepath = midi_folder .. "\\" .. filename
        local output_filename = create_short_filename(filename)
        
        msg("Output: " .. output_filename)
        
        -- Load MIDI file
        if load_midi_file(filepath, filename) then
            -- Render audio
            if render_audio(output_filename) then
                successful = successful + 1
            else
                failed = failed + 1
            end
        else
            msg("  ✗ Failed to load MIDI file")
            failed = failed + 1
        end
        
        -- Brief pause between files
        reaper.defer(function() end)
    end
    
    msg("")
    msg(string.rep("=", 50))
    msg("BATCH RENDERING COMPLETED")
    msg(string.rep("=", 50))
    msg("Total files processed: " .. #midi_files)
    msg("Successful renders: " .. successful)
    msg("Failed renders: " .. failed)
    msg("Output directory: " .. output_folder)
    msg(string.rep("=", 50))
    
    reaper.ShowMessageBox(
        "Batch rendering complete!\n\n" ..
        "Processed: " .. #midi_files .. " files\n" ..
        "Successful: " .. successful .. "\n" ..
        "Failed: " .. failed .. "\n\n" ..
        "Check output folder: " .. output_folder, 
        "Batch Rendering Complete", 
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
        "SD3 BATCH RECORDER\n\n" ..
        "This will process all MIDI files in:\n" .. midi_folder .. 
        "\n\nand record them to:\n" .. output_folder .. 
        "\n\nMake sure Superior Drummer 3 is loaded on track 1.\n\n" ..
        "This will use the RECORDING method (not rendering).\n\n" ..
        "Continue?", 
        "Confirm Batch Recording", 
        4)  -- Yes/No dialog
    
    if result == 6 then  -- Yes
        process_midi_files()
    end
    
    -- End undo block
    reaper.Undo_EndBlock("SD3 MIDI Batch Recording", -1)
end

-- Run the script
main()
