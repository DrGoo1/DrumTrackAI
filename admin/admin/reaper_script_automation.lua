-- Reaper Script Automation - Direct MIDI Import and Processing
-- ============================================================
-- 
-- This ReaScript directly controls Reaper to:
-- 1. Import MIDI file
-- 2. Position at beat 1.3
-- 3. Set render selection 1.1 to 2.1
-- 4. Render audio output
--
-- Author: DrumTracKAI v1.1.7
-- Date: July 23, 2025

-- Configuration
local midi_dir = "D:\\DrumTracKAI_v1.1.7\\admin\\sd3_midi_patterns\\"
local output_dir = "D:\\DrumTracKAI_v1.1.7\\admin\\sd3_extracted_samples\\"
local test_midi = "china_china_hard_053.mid"

function msg(text)
    reaper.ShowConsoleMsg(text .. "\n")
end

function import_midi_file(midi_path)
    msg("=== IMPORTING MIDI FILE ===")
    msg("File: " .. midi_path)
    
    -- Get the first track (should have SD3 loaded)
    local track = reaper.GetTrack(0, 0)
    if not track then
        msg("ERROR: No track found!")
        return false
    end
    
    -- Import MIDI file to track at position 0
    local item = reaper.AddMediaItemToTrack(track)
    if not item then
        msg("ERROR: Could not create media item!")
        return false
    end
    
    -- Add MIDI source to the item
    local take = reaper.AddTakeToMediaItem(item)
    if not take then
        msg("ERROR: Could not create take!")
        return false
    end
    
    -- Set the MIDI file as source
    local source = reaper.PCM_Source_CreateFromFile(midi_path)
    if not source then
        msg("ERROR: Could not load MIDI file!")
        return false
    end
    
    reaper.SetMediaItemTake_Source(take, source)
    
    -- Set item length based on MIDI content
    local length = reaper.GetMediaSourceLength(source, false)
    reaper.SetMediaItemLength(item, length, false)
    
    msg("SUCCESS: MIDI imported!")
    return item
end

function position_midi_at_beat_1_3(item)
    msg("=== POSITIONING MIDI AT BEAT 1.3 ===")
    
    if not item then
        msg("ERROR: No item to position!")
        return false
    end
    
    -- Calculate beat 1.3 position
    -- Assuming 4/4 time, beat 1.3 = 0.5 beats from start
    local bpm = 120 -- Default BPM, could be read from project
    local beat_1_3_time = (0.5 * 60) / bpm -- 0.5 beats in seconds
    
    -- Set item position
    reaper.SetMediaItemPosition(item, beat_1_3_time, false)
    
    msg("SUCCESS: MIDI positioned at beat 1.3 (" .. beat_1_3_time .. " seconds)")
    return true
end

function set_render_selection_1_1_to_2_1()
    msg("=== SETTING RENDER SELECTION: 1.1 to 2.1 ===")
    
    -- Calculate time positions
    local bpm = 120 -- Default BPM
    local beat_1_1_time = 0 -- Start of project
    local beat_2_1_time = (1.0 * 60) / bpm -- 1 full beat in seconds
    
    -- Set time selection
    reaper.GetSet_LoopTimeRange(true, false, beat_1_1_time, beat_2_1_time, false)
    
    msg("SUCCESS: Render selection set from " .. beat_1_1_time .. " to " .. beat_2_1_time .. " seconds")
    return true
end

function render_audio_output(output_filename)
    msg("=== RENDERING AUDIO OUTPUT ===")
    msg("Output: " .. output_filename)
    
    -- Set render settings
    local render_cfg = {
        -- Output format: WAV
        ["RENDER_FORMAT"] = "wav",
        -- Sample rate: 44100
        ["RENDER_SRATE"] = 44100,
        -- Bit depth: 24
        ["RENDER_CHANNELS"] = 2, -- Stereo
        -- Source: Time selection
        ["RENDER_BOUNDSFLAG"] = 1, -- Time selection
        -- Output file
        ["RENDER_FILE"] = output_dir .. output_filename .. ".wav"
    }
    
    -- Apply render settings
    for key, value in pairs(render_cfg) do
        if type(value) == "string" then
            reaper.GetSetProjectInfo_String(0, key, value, true)
        else
            reaper.GetSetProjectInfo(0, key, value, true)
        end
    end
    
    -- Start render
    reaper.Main_OnCommand(42230, 0) -- Render project to file
    
    msg("SUCCESS: Render initiated!")
    return true
end

function clear_project()
    msg("=== CLEARING PROJECT ===")
    
    -- Select all items
    reaper.Main_OnCommand(40182, 0) -- Select all items
    
    -- Delete selected items
    reaper.Main_OnCommand(40006, 0) -- Delete items
    
    -- Clear time selection
    reaper.Main_OnCommand(40020, 0) -- Clear time selection
    
    msg("SUCCESS: Project cleared!")
    return true
end

function process_single_midi_file(midi_filename)
    msg("=" .. string.rep("=", 60))
    msg("PROCESSING: " .. midi_filename)
    msg("=" .. string.rep("=", 60))
    
    local midi_path = midi_dir .. midi_filename
    local instrument_name = midi_filename:gsub("%.mid$", ""):gsub("_[0-9]+$", "")
    
    msg("MIDI Path: " .. midi_path)
    msg("Instrument: " .. instrument_name)
    
    -- Check if output already exists
    local output_file = output_dir .. instrument_name .. ".wav"
    local file = io.open(output_file, "r")
    if file then
        file:close()
        msg("SKIPPING: Output already exists - " .. output_file)
        return true
    end
    
    -- Execute workflow
    local workflow_steps = {
        {"Import MIDI", function() return import_midi_file(midi_path) end},
        {"Position at 1.3", function() return position_midi_at_beat_1_3(last_item) end},
        {"Set render selection", set_render_selection_1_1_to_2_1},
        {"Render audio", function() return render_audio_output(instrument_name) end},
        {"Clear project", clear_project}
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
        
        -- Small delay between steps
        reaper.defer(function() end)
    end
    
    msg("SUCCESS: " .. midi_filename .. " -> " .. instrument_name .. ".wav")
    return true
end

function main()
    msg("REAPER SCRIPT AUTOMATION - DIRECT CONTROL")
    msg(string.rep("=", 60))
    msg("Using ReaScript for reliable MIDI processing")
    msg(string.rep("=", 60))
    
    -- Ensure output directory exists
    reaper.RecursiveCreateDirectory(output_dir, 0)
    
    -- Test with single file first
    msg("\nTesting with: " .. test_midi)
    
    local success = process_single_midi_file(test_midi)
    
    if success then
        msg("\nSUCCESS: ReaScript automation working!")
        msg("Ready for batch processing")
        
        -- Could extend to process all MIDI files
        -- local midi_files = get_all_midi_files(midi_dir)
        -- for i, midi_file in ipairs(midi_files) do
        --     process_single_midi_file(midi_file)
        -- end
        
    else
        msg("\nFAILED: ReaScript automation needs debugging")
    end
    
    msg("\nReaScript automation complete!")
end

-- Execute main function
main()
