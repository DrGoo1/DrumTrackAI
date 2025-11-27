-- JamstixBatchGenerator_SINGLE.lua
-- Test version - generates just ONE example
-- ================================================================

local reaper = reaper

------------------------------------------------------------
-- CONFIG - UPDATED PATHS
------------------------------------------------------------

local OUTPUT_BASE = "F:/DrumTrackAI_Jamstix_Dataset"
local BARS_PER_TAKE = 16
local TEMPO_BPM = 100

------------------------------------------------------------
-- UTILS
------------------------------------------------------------

local function ensure_directory(path)
  reaper.RecursiveCreateDirectory(path, 0)
end

local function msg(s)
  reaper.ShowConsoleMsg(tostring(s) .. "\n")
end

local function clear_midi_items_on_track(track)
  local itemCount = reaper.CountTrackMediaItems(track)
  for i = itemCount - 1, 0, -1 do
    local item = reaper.GetTrackMediaItem(track, i)
    reaper.DeleteTrackMediaItem(track, item)
  end
end

------------------------------------------------------------
-- MAIN - SINGLE TEST
------------------------------------------------------------

local function main()
  msg("=" .. string.rep("=", 69))
  msg("Jamstix Test - SINGLE RECORDING")
  msg("=" .. string.rep("=", 69))
  msg("")
  
  ensure_directory(OUTPUT_BASE)
  
  local proj = 0
  local captureTrack = reaper.GetTrack(proj, 1) -- Track 2 (0-indexed)
  
  if not captureTrack then
    reaper.MB("Error: Track 2 (MIDI Capture) not found!", "Error", 0)
    return
  end
  
  msg("Found capture track")
  
  -- Clear any existing items
  clear_midi_items_on_track(captureTrack)
  
  -- Check record mode
  local recmode = reaper.GetMediaTrackInfo_Value(captureTrack, "I_RECMODE")
  msg("Current record mode: " .. recmode .. " (should be 3 for MIDI output)")
  
  -- Set capture track to record output (MIDI)
  reaper.SetMediaTrackInfo_Value(captureTrack, "I_RECARM", 1)
  reaper.SetMediaTrackInfo_Value(captureTrack, "I_RECMON", 1)
  reaper.SetMediaTrackInfo_Value(captureTrack, "I_RECMODE", 3) -- Record: output (MIDI)
  
  msg("Track armed for MIDI recording")
  msg("")
  
  -- Prompt user
  local result = reaper.MB(
    "SINGLE TEST RECORDING\n\n" ..
    "1. Set Jamstix to any preset you want\n" ..
    "2. Click OK to start recording\n" ..
    "3. Recording will run for " .. BARS_PER_TAKE .. " bars\n\n" ..
    "Ready?",
    "Test Recording",
    1
  )
  
  if result == 2 then
    msg("Cancelled by user")
    return
  end
  
  -- Start recording
  msg("Starting recording...")
  reaper.OnPlayButton()
  reaper.CSurf_OnRecord()
  reaper.UpdateArrange()
  
  -- Calculate duration
  local beats_per_bar = 4
  local seconds_per_beat = 60.0 / TEMPO_BPM
  local bar_length_sec = beats_per_bar * seconds_per_beat
  local total_sec = BARS_PER_TAKE * bar_length_sec
  
  msg("Recording for " .. string.format("%.1f", total_sec) .. " seconds...")
  
  -- Show recording dialog
  reaper.MB(
    "Recording in progress...\n\n" ..
    "Duration: " .. string.format("%.1f", total_sec) .. " seconds\n" ..
    "(" .. BARS_PER_TAKE .. " bars @ " .. TEMPO_BPM .. " BPM)\n\n" ..
    "Click OK when playback finishes.",
    "Recording...",
    0
  )
  
  -- Stop
  reaper.CSurf_OnStop()
  reaper.OnStopButton()
  reaper.UpdateTimeline()
  
  msg("Recording stopped")
  msg("")
  
  -- Check what we recorded
  local itemCount = reaper.CountTrackMediaItems(captureTrack)
  msg("Items on capture track: " .. itemCount)
  
  if itemCount < 1 then
    reaper.MB("No items recorded! Check:\n\n" ..
      "1. Track 2 record mode = 'output (MIDI)'\n" ..
      "2. Track 1 sends MIDI to Track 2\n" ..
      "3. Jamstix is playing",
      "No Recording!", 0)
    return
  end
  
  local item = reaper.GetTrackMediaItem(captureTrack, 0)
  local take = reaper.GetActiveTake(item)
  
  if not take then
    reaper.MB("No take found in recorded item!", "Error", 0)
    return
  end
  
  local isMIDI = reaper.TakeIsMIDI(take)
  msg("Is MIDI: " .. tostring(isMIDI))
  
  if not isMIDI then
    reaper.MB(
      "❌ PROBLEM: Recorded AUDIO, not MIDI!\n\n" ..
      "Fix:\n" ..
      "1. Right-click Track 2 record button\n" ..
      "2. Select 'Record: output (MIDI)'\n" ..
      "3. Save template\n" ..
      "4. Run script again",
      "Wrong Recording Type!",
      0
    )
    return
  end
  
  -- Count notes
  local _, notecnt, _, _ = reaper.MIDI_CountEvts(take)
  msg("MIDI notes recorded: " .. notecnt)
  
  if notecnt == 0 then
    reaper.MB("MIDI recorded but NO NOTES!\n\nCheck Jamstix is playing.", "No Notes!", 0)
    return
  end
  
  -- Success!
  msg("")
  msg("=" .. string.rep("=", 69))
  msg("✓ SUCCESS!")
  msg("=" .. string.rep("=", 69))
  msg("Recorded: " .. notecnt .. " MIDI notes")
  msg("")
  
  reaper.MB(
    "✅ SUCCESS!\n\n" ..
    "Recorded " .. notecnt .. " MIDI notes\n\n" ..
    "Your setup is working!\n" ..
    "You can now:\n" ..
    "1. Save this template\n" ..
    "2. Run the full batch script\n" ..
    "   (JamstixBatchGenerator_COMPLETE.lua)\n\n" ..
    "Check ReaScript console for details.",
    "Test Successful!",
    0
  )
end

reaper.Undo_BeginBlock()
main()
reaper.Undo_EndBlock("Jamstix test recording", -1)
