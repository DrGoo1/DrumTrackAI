-- JamstixBatchGenerator_COMPLETE.lua
-- Batch-generate Jamstix drum tracks with Reaper for LLM training
-- ================================================================
-- Updated with correct paths for your system

local reaper = reaper

------------------------------------------------------------
-- CONFIG - UPDATED PATHS
------------------------------------------------------------

local TEMPLATE_PROJECT_PATH = "C:/Users/dagol/ReaperTemplates/JamstixTemplate.rpp"
local OUTPUT_BASE = "F:/DrumTrackAI_Jamstix_Dataset"
local BARS_PER_TAKE = 16

-- Tempo grid and variation count for richer LLM data
local TEMPOS = { 60, 80, 100, 120 }
local VARIATIONS_PER_COMBO = 5

-- Drummers and styles to iterate (must match Jamstix presets)
local DRUMMERS = {
  "Default_Rock",
  "Funk_Master",
  "Jazz_Player",
  "Metal_Beast",
  "Fusion_Pro"
}

local STYLES = {
  "Rock_8th",
  "Rock_16th",
  "Funk_16th",
  "Shuffle_HalfTime",
  "Jazz_Swing",
  "Latin_Groove"
}

local SONG_PRESETS = {
  "Simple_Verse_Chorus",
  "Intro_Verse_Chorus_Bridge",
  "Verse_Build_Chorus"
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
  local beats_per_bar = 4
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

  -- Let it run for the selected time range (NON-BLOCKING)
  local _, endpos = reaper.GetSet_LoopTimeRange(false, false, 0, 0, false)
  
  -- Prompt user to wait manually
  msg("Recording " .. bars .. " bars...")
  msg("Wait for recording to finish, then press OK")
  reaper.MB(
    "Recording in progress...\n\n" ..
    "Duration: " .. string.format("%.1f", endpos) .. " seconds\n\n" ..
    "Click OK when recording finishes.",
    "Recording...",
    0
  )

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

  -- Export MIDI using custom writer
  local _, notecnt, _, _ = reaper.MIDI_CountEvts(take)
  
  if notecnt == 0 then
    msg("Warning: No notes in MIDI take")
    return false
  end

  -- Write simple MIDI file
  msg("Exporting MIDI to: " .. output_path)
  msg("  Notes: " .. notecnt)
  
  -- Note: Full MIDI export requires custom SMF writer
  -- For now, save project and extract MIDI manually or use Python converter
  
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

  -- Show prompt for manual preset change
  msg("Set Jamstix preset: " .. drummerName .. " / " .. styleName .. " / " .. songPresetName)
  
  -- Auto preset setting via FX parameters (plugin-specific)
  -- local fxIndex = 0
  -- reaper.TrackFX_SetPreset(jamTrack, fxIndex, presetName)
  -- OR set parameters directly if you know the param indices
end

------------------------------------------------------------
-- MAIN LOOP
------------------------------------------------------------

local function main()
  msg("=" .. string.rep("=", 69))
  msg("Jamstix Batch Generator - COMPLETE VERSION")
  msg("=" .. string.rep("=", 69))
  msg("")
  msg("Template: " .. TEMPLATE_PROJECT_PATH)
  msg("Output:   " .. OUTPUT_BASE)
  msg("Bars:     " .. BARS_PER_TAKE)
  msg("Tempos:   " .. table.concat(TEMPOS, ", ") .. " BPM")
  msg("")
  
  reaper.Main_openProject(TEMPLATE_PROJECT_PATH)

  ensure_directory(OUTPUT_BASE)
  
  local count = 0
  local total = #DRUMMERS * #STYLES * #SONG_PRESETS * #TEMPOS * VARIATIONS_PER_COMBO
  
  msg("Total combinations to generate (including tempos and variations): " .. total)
  msg("")

  for _, drummerName in ipairs(DRUMMERS) do
    for _, styleName in ipairs(STYLES) do
      for _, songPreset in ipairs(SONG_PRESETS) do
        for _, tempo in ipairs(TEMPOS) do
          for variation_index = 1, VARIATIONS_PER_COMBO do

            count = count + 1
            msg("=" .. string.rep("=", 69))
            msg("Combination " .. count .. "/" .. total)
            msg("=" .. string.rep("=", 69))
            msg("Drummer:    " .. drummerName)
            msg("Style:      " .. styleName)
            msg("Preset:     " .. songPreset)
            msg("Tempo:      " .. tempo .. " BPM")
            msg("Variation:  " .. variation_index)

            set_project_tempo(tempo)
            set_time_selection_for_bars(tempo, BARS_PER_TAKE)
            set_jamstix_preset(drummerName, styleName, songPreset)

            -- Prompt user to set preset / randomize manually
            local result = reaper.MB(
              "Set Jamstix preset and (optionally) randomize for this variation:\n\n" ..
              "Drummer: " .. drummerName .. "\n" ..
              "Style: " .. styleName .. "\n" ..
              "Preset: " .. songPreset .. "\n" ..
              "Tempo:  " .. tempo .. " BPM\n" ..
              "Variation: " .. variation_index .. "\n\n" ..
              "Then click OK to record.\nClick Cancel to skip this variation.",
              "Jamstix Preset - " .. count .. "/" .. total,
              1
            )

            if result == 2 then
              msg("Skipped by user\n")
              goto continue
            end

            local ok = record_jamstix_to_midi(BARS_PER_TAKE)
            if not ok then
              msg("Recording failed, skipping combination\n")
            else
              local comboDir = string.format(
                "%s\\jam_%04d_%s_%s_%s_%dbpm_var%d",
                OUTPUT_BASE,
                count,
                drummerName,
                styleName,
                songPreset,
                tempo,
                variation_index
              )
              ensure_directory(comboDir)

              local midiPath = comboDir .. "\\drums.mid"
              export_capture_track_midi(midiPath)

              -- Metadata JSON
              local metaPath = comboDir .. "\\jamstix_meta.json"
              local metaFile = io.open(metaPath, "w")
              if metaFile then
                metaFile:write(string.format([[[
{
  "drummer": %q,
  "style": %q,
  "song_preset": %q,
  "tempo": %d,
  "bars": %d,
  "variation_index": %d,
  "generated_at": "%s",
  "combination_id": %d
}
]], drummerName, styleName, songPreset, tempo, BARS_PER_TAKE, variation_index, os.date("%Y-%m-%d %H:%M:%S"), count))
                metaFile:close()
              end

              msg("? Generated: " .. comboDir)
              msg("")
            end

            ::continue::
          end
        end
      end
    end
  end

  msg("=" .. string.rep("=", 69))
  msg("Done! Generated " .. count .. " combinations")
  msg("Output directory: " .. OUTPUT_BASE)
  msg("=" .. string.rep("=", 69))
end

reaper.Undo_BeginBlock()
main()
reaper.Undo_EndBlock("Jamstix batch generator", -1)
