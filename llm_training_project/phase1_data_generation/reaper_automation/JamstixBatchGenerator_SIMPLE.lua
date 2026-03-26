-- JamstixBatchGenerator_SIMPLE.lua
-- Single-track approach - record MIDI from Jamstix plugin directly
-- ================================================================

local reaper = reaper

------------------------------------------------------------
-- CONFIG
------------------------------------------------------------

local OUTPUT_BASE = "F:/DrumTrackAI_Jamstix_Dataset"
local BARS_PER_TAKE = 16
local TEMPO_BPM = 100

------------------------------------------------------------
-- UTILS
------------------------------------------------------------

local function msg(s)
  reaper.ShowConsoleMsg(tostring(s) .. "\n")
end

local function ensure_directory(path)
  reaper.RecursiveCreateDirectory(path, 0)
end

------------------------------------------------------------
-- SIMPLE SINGLE-TRACK TEST
------------------------------------------------------------

local function main()
  msg("=" .. string.rep("=", 69))
  msg("Jamstix Single-Track Test")
  msg("=" .. string.rep("=", 69))
  msg("")
  msg("SETUP REQUIRED:")
  msg("1. Track 1 has Jamstix plugin")
  msg("2. In Jamstix plugin: Enable 'Send MIDI to Host'")
  msg("3. Track 1 record mode: 'Record: output (MIDI)'")
  msg("4. Track 1 armed (red button on)")
  msg("")
  
  ensure_directory(OUTPUT_BASE)
  
  local proj = 0
  local jamTrack = reaper.GetTrack(proj, 0) -- Track 1 (0-indexed)
  
  if not jamTrack then
    reaper.MB("Error: Track 1 (Jamstix) not found!", "Error", 0)
    return
  end
  
  msg("Found Jamstix track")
  
  -- Check current record mode
  local recmode = reaper.GetMediaTrackInfo_Value(jamTrack, "I_RECMODE")
  msg("Current record mode: " .. recmode)
  msg("  (3 = MIDI output, correct!)")
  msg("")
  
  -- Make sure track is armed and set to record MIDI output
  reaper.SetMediaTrackInfo_Value(jamTrack, "I_RECARM", 1)
  reaper.SetMediaTrackInfo_Value(jamTrack, "I_RECMON", 1)
  reaper.SetMediaTrackInfo_Value(jamTrack, "I_RECMODE", 3) -- Record: output (MIDI)
  
  msg("Track armed for MIDI output recording")
  msg("")
  
  -- Calculate duration
  local beats_per_bar = 4
  local seconds_per_beat = 60.0 / TEMPO_BPM
  local bar_length_sec = beats_per_bar * seconds_per_beat
  local total_sec = BARS_PER_TAKE * bar_length_sec
  
  -- Prompt
  local result = reaper.MB(
    "SINGLE-TRACK RECORDING TEST\n\n" ..
    "Requirements:\n" ..
    "1. Jamstix plugin has 'Send MIDI to Host' enabled\n" ..
    "2. Track 1 armed and ready\n\n" ..
    "Recording duration: " .. string.format("%.1f", total_sec) .. " seconds\n" ..
    "(" .. BARS_PER_TAKE .. " bars @ " .. TEMPO_BPM .. " BPM)\n\n" ..
    "Click OK to start recording.",
    "Ready?",
    1
  )
  
  if result == 2 then
    msg("Cancelled by user")
    return
  end
  
  -- Clear any existing items first
  local itemCount = reaper.CountTrackMediaItems(jamTrack)
  for i = itemCount - 1, 0, -1 do
    local item = reaper.GetTrackMediaItem(jamTrack, i)
    reaper.DeleteTrackMediaItem(jamTrack, item)
  end
  
  msg("Starting recording...")
  msg("Duration: " .. string.format("%.1f", total_sec) .. " seconds")
  msg("")
  
  -- Start recording
  reaper.CSurf_OnRecord()
  reaper.UpdateArrange()
  
  -- Show non-blocking message
  msg("RECORDING IN PROGRESS - manually stop when done!")
  msg("Press SPACEBAR to stop after " .. string.format("%.0f", total_sec) .. " seconds")
  msg("")
  
  -- Wait for user to manually stop
  reaper.MB(
    "Recording started!\n\n" ..
    "Jamstix is playing for " .. string.format("%.1f", total_sec) .. " seconds.\n\n" ..
    "Watch the playback position.\n" ..
    "Click OK when recording reaches " .. BARS_PER_TAKE .. " bars,\n" ..
    "then press SPACEBAR to stop.",
    "Recording...",
    0
  )
  
  -- Stop
  reaper.CSurf_OnStop()
  reaper.UpdateTimeline()
  
  msg("Recording stopped")
  msg("")
  
  -- Check what we got
  itemCount = reaper.CountTrackMediaItems(jamTrack)
  msg("Items on track: " .. itemCount)
  
  if itemCount < 1 then
    reaper.MB(
      "No items recorded!\n\n" ..
      "Check:\n" ..
      "1. Jamstix plugin has 'Send MIDI to Host' enabled\n" ..
      "2. Jamstix is actually playing\n" ..
      "3. Track record mode = 'output (MIDI)'",
      "No Recording!",
      0
    )
    return
  end
  
  local item = reaper.GetTrackMediaItem(jamTrack, 0)
  local take = reaper.GetActiveTake(item)
  
  if not take then
    msg("No take found")
    return
  end
  
  local isMIDI = reaper.TakeIsMIDI(take)
  msg("Is MIDI: " .. tostring(isMIDI))
  
  if not isMIDI then
    reaper.MB(
      "❌ STILL RECORDING AUDIO!\n\n" ..
      "The problem:\n" ..
      "Jamstix is not sending MIDI to host.\n\n" ..
      "Solution:\n" ..
      "1. Open Jamstix plugin window\n" ..
      "2. Find MIDI output settings\n" ..
      "3. Enable 'Send MIDI to Host' or 'MIDI Output'\n" ..
      "4. Try recording again\n\n" ..
      "OR use Jamstix's built-in MIDI export instead.",
      "Not MIDI!",
      0
    )
    return
  end
  
  -- Count notes
  local _, notecnt, _, _ = reaper.MIDI_CountEvts(take)
  msg("MIDI notes: " .. notecnt)
  msg("")
  
  if notecnt == 0 then
    reaper.MB("MIDI recorded but NO NOTES!\n\nJamstix may not be playing.", "No Notes!", 0)
    return
  end
  
  -- Success!
  msg("=" .. string.rep("=", 69))
  msg("✓ SUCCESS!")
  msg("=" .. string.rep("=", 69))
  msg("Recorded " .. notecnt .. " MIDI notes on Track 1")
  msg("")
  msg("This confirms single-track recording works!")
  msg("Now you can:")
  msg("1. Save this project as your template")
  msg("2. Use this approach for batch generation")
  msg("")
  
  reaper.MB(
    "✅ SUCCESS!\n\n" ..
    "Recorded " .. notecnt .. " MIDI notes directly from Jamstix!\n\n" ..
    "Single-track approach works!\n\n" ..
    "Save this project as your template.",
    "Success!",
    0
  )
end

reaper.Undo_BeginBlock()
main()
reaper.Undo_EndBlock("Jamstix single-track test", -1)
