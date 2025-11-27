#pragma once
#include <tracktion_engine/tracktion_engine.h>
namespace te = tracktion::engine;

struct DCSMAdapter {
  te::Engine engine;
  std::unique_ptr<te::Edit> edit;

  explicit DCSMAdapter(const juce::String& appName);
  te::AudioTrack* importAudioFile(const juce::File& f, double atSeconds=0.0);
  te::MidiClip*  ensureDrumMidiClip(int trackIndex, double lengthSeconds);
  void addMidiNote(te::MidiClip& clip, int midiNote, double startSec, double lenSec, int vel);
  void setConstantTempo(double bpm);
  void ensureArranger();
  void addSection(double startSec, double endSec, const juce::String& label);
  void play(double fromSec=0.0);
  void stop();
};
