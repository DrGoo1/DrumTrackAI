
-- Simple MIDI Import and Render Script
-- ====================================

function msg(text)
    reaper.ShowConsoleMsg(text .. "\n")
end

function main()
    msg("=== REAPER SCRIPT STARTED ===")
    
    -- Configuration
    local midi_file = "D:\\DrumTracKAI_v1.1.7\\admin\\sd3_midi_patterns\\china_china_hard_053.mid"
    local output_file = "D:\\DrumTracKAI_v1.1.7\\admin\\sd3_extracted_samples\\china_china_hard.wav"
    
    msg("MIDI file: " .. midi_file)
    msg("Output file: " .. output_file)
    
    -- Check if MIDI file exists
    local file = io.open(midi_file, "r")
    if not file then
        msg("ERROR: MIDI file not found!")
        return
    end
    file:close()
    
    -- Get first track (should have SD3 loaded)
    local track_count = reaper.CountTracks(0)
    msg("Found " .. track_count .. " tracks")
    
    if track_count == 0 then
        msg("ERROR: No tracks found! Make sure SD3 is loaded on a track.")
        return
    end
    
    local track = reaper.GetTrack(0, 0)
    msg("Using track 1")
    
    -- Insert MIDI file
    msg("Inserting MIDI file...")
    reaper.InsertMedia(midi_file, 0)
    
    -- Get the inserted item
    local item_count = reaper.CountMediaItems(0)
    msg("Found " .. item_count .. " items")
    
    if item_count == 0 then
        msg("ERROR: No items found after MIDI insert!")
        return
    end
    
    local item = reaper.GetMediaItem(0, item_count - 1) -- Get last item (just inserted)
    
    -- Position at beat 1.3 (0.5 seconds at 120 BPM)
    local beat_1_3_pos = 0.5
    reaper.SetMediaItemPosition(item, beat_1_3_pos, false)
    msg("Positioned MIDI at " .. beat_1_3_pos .. " seconds")
    
    -- Set time selection from 1.1 to 2.1 (0 to 1 second)
    reaper.GetSet_LoopTimeRange(true, false, 0.0, 1.0, false)
    msg("Set time selection: 0.0 to 1.0 seconds")
    
    -- Set render settings
    msg("Setting render configuration...")
    
    -- Set output file
    reaper.GetSetProjectInfo_String(0, "RENDER_FILE", output_file, true)
    
    -- Set format to WAV
    reaper.GetSetProjectInfo_String(0, "RENDER_FORMAT", "wav", true)
    
    -- Set to render time selection
    reaper.GetSetProjectInfo(0, "RENDER_BOUNDSFLAG", 1, true)
    
    -- Start render
    msg("Starting render...")
    reaper.Main_OnCommand(42230, 0) -- Render project to file
    
    -- Wait a bit for render to complete
    local start_time = reaper.time_precise()
    while reaper.time_precise() - start_time < 10 do
        -- Wait for render
    end
    
    msg("Render completed!")
    msg("=== REAPER SCRIPT FINISHED ===")
end

-- Execute main function
main()
