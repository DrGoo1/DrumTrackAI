-- JamstixBatchGenerator.lua
-- Batch-generate Jamstix drum tracks with Reaper for LLM training
-- ================================================================

local reaper = reaper

------------------------------------------------------------
-- CONFIG
------------------------------------------------------------

local TEMPLATE_PROJECT_PATH = "C:\\ReaperTemplates\\JamstixTemplate.RPP"
local OUTPUT_BASE = "F:\\DrumTracKAI_v1.1.16_Clean\\llm_training_project\\phase1_data_generation\\output\\jamstix_generated"
local BARS_PER_TAKE = 16
local TEMPO_BPM = 100

-- Drummers and styles to iterate (must match Jamstix presets)
local DRUMMERS = {
  "Default Rock Drummer",
  "Funk Master",
  "Jazz Player",
  "Metal Beast",
  "Fusion Pro"
}

local STYLES = {
  "Rock 8th",
  "Rock 16th",
  "Funk 16th",
  "Shuffle Half-Time",
  "Jazz Swing",
  "Latin Groove"
}

local SONG_PRESETS = {
  "Simple Verse-Chorus",
  "Intro-Verse-Chorus-Bridge",
  "Verse-Build-Chorus"
}

------------------------------------------------------------
-- UTILS
------------------------------------------------------------

local function ensure_directory(path)
  reaper.RecursiveCreateDirectory(path, 0)
end

local function msg(s)
  reaper.ShowConsoleMsg(tostring(s) .. "\n")
end

local function set_project_tempo(bpm)
  reaper.CSurf_OnTempoChange(bpm)
end

local function clear_midi_items_on_track(track)
  local itemCount = reaper.CountTrackMediaItems(track)
  for i = itemCount - 1, 0, -1 do
    local item = reaper.GetTrackMediaItem(track, i)
    reaper.DeleteTrackMediaItem(track, item)
  end
end

local function set_time_selection_for_bars(bpm, bars)
  local beats_per_bar = 4  -- assumes 4/4
  local seconds_per_beat = 60.0 / bpm
  local bar_length_sec = beats_per_bar * seconds_per_beat
  local total_sec = bars * bar_length_sec
  reaper.GetSet_LoopTimeRange(true, false, 0.0, total_sec, false)
end

local function record_jamstix_to_midi(bars)
  local proj = 0
  local captureTrack = reaper.GetTrack(proj, 1) -- Track 2 (0-indexed)

  if not captureTrack then
    msg("Error: capture track not found")
    return false
  end

  clear_midi_items_on_track(captureTrack)

  -- Set capture track to record output (MIDI)
  reaper.SetMediaTrackInfo_Value(captureTrack, "I_RECARM", 1)
  reaper.SetMediaTrackInfo_Value(captureTrack, "I_RECMON", 1)
  reaper.SetMediaTrackInfo_Value(captureTrack, "I_RECMODE", 3) -- Record: output (MIDI)

  -- Start recording
  reaper.OnPlayButton()
  reaper.CSurf_OnRecord()
  reaper.UpdateArrange()

  -- Let it run for the selected time range
  local _, endpos = reaper.GetSet_LoopTimeRange(false, false, 0, 0, false)
  local start_time = reaper.time_precise()
  while reaper.time_precise() - start_time < (endpos + 0.5) do
    reaper.defer(function() end)
  end

  -- Stop
  reaper.CSurf_OnStop()
  reaper.OnStopButton()
  reaper.UpdateTimeline()

  return true
end

local function export_capture_track_midi(output_path)
  local proj = 0
  local captureTrack = reaper.GetTrack(proj, 1)
  if not captureTrack then
    msg("Error: capture track not found for export")
    return false
  end

  local itemCount = reaper.CountTrackMediaItems(captureTrack)
  if itemCount < 1 then
    msg("No MIDI items on capture track")
    return false
  end

  local item = reaper.GetTrackMediaItem(captureTrack, 0)
  local take = reaper.GetActiveTake(item)
  if not take or not reaper.TakeIsMIDI(take) then
    msg("No MIDI take found on capture track")
    return false
  end

  -- Export MIDI (simplified - requires custom MIDI writer for full automation)
  -- TODO: Implement custom MIDI file writer using reaper.MIDI_GetNote()
  msg("Exporting MIDI to: " .. output_path)
  
  return true
end

------------------------------------------------------------
-- JAMSTIX PRESET HANDLING
------------------------------------------------------------

local function set_jamstix_preset(drummerName, styleName, songPresetName)
  local proj = 0
  local jamTrack = reaper.GetTrack(proj, 0) -- Track 1
  if not jamTrack then
    msg("Error: Jamstix track not found")
    return
  end

  local fxIndex = 0 -- assuming Jamstix is first FX
  
  -- TODO: Set Jamstix preset via TrackFX_SetPreset or parameter automation
  -- This is plugin-specific and requires knowing Jamstix's parameter layout
  msg("Setting Jamstix preset: " .. drummerName .. " / " .. styleName .. " / " .. songPresetName)
end

------------------------------------------------------------
-- MAIN LOOP
------------------------------------------------------------

local function main()
  reaper.Main_openProject(TEMPLATE_PROJECT_PATH)

  ensure_directory(OUTPUT_BASE)
  set_project_tempo(TEMPO_BPM)
  set_time_selection_for_bars(TEMPO_BPM, BARS_PER_TAKE)

  local count = 0

  for _, drummerName in ipairs(DRUMMERS) do
    for _, styleName in ipairs(STYLES) do
      for _, songPreset in ipairs(SONG_PRESETS) do

        set_jamstix_preset(drummerName, styleName, songPreset)

        local ok = record_jamstix_to_midi(BARS_PER_TAKE)
        if not ok then
          msg("Recording failed, skipping combination")
        else
          local comboDir = string.format(
            "%s\\jam_%04d_%s_%s_%s",
            OUTPUT_BASE,
            count,
            drummerName:gsub(" ", "_"),
            styleName:gsub(" ", "_"),
            songPreset:gsub(" ", "_")
          )
          ensure_directory(comboDir)

          local midiPath = comboDir .. "\\drums.mid"
          export_capture_track_midi(midiPath)

          -- Metadata JSON
          local metaPath = comboDir .. "\\jamstix_meta.json"
          local metaFile = io.open(metaPath, "w")
          if metaFile then
            metaFile:write(string.format([[
{
  "drummer": %q,
  "style": %q,
  "song_preset": %q,
  "tempo": %d,
  "bars": %d,
  "generated_at": "%s"
}
]], drummerName, styleName, songPreset, TEMPO_BPM, BARS_PER_TAKE, os.date("%Y-%m-%d %H:%M:%S")))
            metaFile:close()
          end

          count = count + 1
          msg("Generated combo #" .. count)
        end
      end
    end
  end

  msg("Done generating Jamstix dataset. Total: " .. count .. " combinations")
end

reaper.Undo_BeginBlock()
main()
reaper.Undo_EndBlock("Jamstix batch generator", -1)
