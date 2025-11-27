#pragma once
#include <tracktion_engine/tracktion_engine.h>
#include "RustCoreBridge.h"
#include "DCSMAdapter.h"

struct DCSMOrchestrator {
  RustCoreBridge core;
  DCSMAdapter adapter;

  explicit DCSMOrchestrator(const juce::String& appName) : adapter(appName) {}

  // lane → GM note mapping
  static int laneToMidi(const juce::String& lane){
    if      (lane == "kick")  return 36;
    else if (lane == "snare") return 38;
    else if (lane == "hihat") return 42;
    else if (lane == "ohat")  return 46;
    else if (lane == "ride")  return 51;
    else if (lane == "tom")   return 45;
    else if (lane == "crash") return 49;
    return 39; // hand clap fallback
  }

  bool loadRust(const juce::File& dylib){ return core.load(dylib); }

  void processFile(const juce::File& audio, const juce::String& style="rock"){
    // 1) import & analyze
    adapter.importAudioFile(audio, 0.0);
    auto a = core.analyze(audio); double bpm = a.getProperty("tempo", 120.0);
    adapter.setConstantTempo(bpm);

    // 2) smart sectionize
    auto s = core.sectionizeSmart(audio, (float) bpm, 8, 16);
    if (auto* arr = s.getProperty("sections", juce::var()).getArray()){
      for (const auto& secVar : *arr){
        if (auto* sec = secVar.getDynamicObject()){
          const double st = (double) sec->getProperty("start");
          const double en = (double) sec->getProperty("end");
          const juce::String label = sec->getProperty("label").toString();

          adapter.addSection(st, en, label);

          // 3) generate drums (notes) per section
          juce::DynamicObject::Ptr params = new juce::DynamicObject();
          params->setProperty("bpm", bpm);
          params->setProperty("start", st);
          params->setProperty("end", en);
          params->setProperty("style", style);
          params->setProperty("label", label);
          params->setProperty("density", 0.65);
          params->setProperty("swing", 0.1);
          params->setProperty("humanize", 0.12);
          params->setProperty("seed", 42);
          params->setProperty("swing_preset", "light");
          params->setProperty("vel_preset", "accent24");
          params->setProperty("fill_preset", "random");
          juce::var gen = core.generateNotes(juce::var(params.get()));

          auto* clip = adapter.ensureDrumMidiClip(0, en);
          if (clip){
            if (auto* notes = gen.getProperty("notes", juce::var()).getArray()){
              for (const auto& nVar : *notes){
                if (auto* n = nVar.getDynamicObject()){
                  const juce::String lane = n->getProperty("lane").toString();
                  const int midi = laneToMidi(lane);
                  const double t = (double) n->getProperty("time");
                  const double len = (double) n->getProperty("len");
                  const int vel = (int) n->getProperty("vel");
                  adapter.addMidiNote(*clip, midi, t, len, vel);
                }
              }
            }
          }
        }
      }
    }

    adapter.play(0.0);
  }
};
