#pragma once
#include <tracktion_engine/tracktion_engine.h>

struct RustCoreBridge {
  using Fn0 = const char* (*)();
  using FnFree = void (*)(const char*);
  using FnPeaks = const char* (*)(const char* path, int maxPoints);
  using FnAnalyze = const char* (*)(const char* path, float minBpm, float maxBpm);
  using FnSectionize = const char* (*)(const char* path, float bpm, int minBars, int maxBars);
  using FnGenJson = const char* (*)(const char* paramsJson);

  juce::DynamicLibrary lib;
  FnFree ac_free = nullptr; Fn0 ac_last_error = nullptr; Fn0 ac_version = nullptr;
  FnPeaks ac_peaks = nullptr; FnAnalyze ac_analyze = nullptr; FnSectionize ac_sectionize_smart = nullptr; FnGenJson ac_generate_json = nullptr; FnGenJson ac_generate_midi64 = nullptr;

  bool load(const juce::File& dylib){
    if (! lib.open(dylib.getFullPathName())) return false;
    ac_free = (FnFree) lib.getFunction("ac_free");
    ac_last_error = (Fn0) lib.getFunction("ac_last_error");
    ac_version = (Fn0) lib.getFunction("ac_version");
    ac_peaks = (FnPeaks) lib.getFunction("ac_peaks");
    ac_analyze = (FnAnalyze) lib.getFunction("ac_analyze");
    ac_sectionize_smart = (FnSectionize) lib.getFunction("ac_sectionize_smart");
    ac_generate_json = (FnGenJson) lib.getFunction("ac_generate_json");
    ac_generate_midi64 = (FnGenJson) lib.getFunction("ac_generate_midi64");
    return ac_free && ac_last_error && ac_version && ac_peaks && ac_analyze && ac_sectionize_smart && ac_generate_json && ac_generate_midi64;
  }

  juce::var callJson(const char* s){
    // Use JUCE JSON helper that returns a juce::var directly
    juce::var v = juce::JSON::fromString(juce::String(s));
    if (ac_free) ac_free(s);
    return v;
  }

  juce::var peaks(const juce::File& f, int maxPoints){ return callJson(ac_peaks(f.getFullPathName().toRawUTF8(), maxPoints)); }
  juce::var analyze(const juce::File& f, float minBpm=50.f, float maxBpm=200.f){ return callJson(ac_analyze(f.getFullPathName().toRawUTF8(), minBpm, maxBpm)); }
  juce::var sectionizeSmart(const juce::File& f, float bpm, int minBars=8, int maxBars=16){ return callJson(ac_sectionize_smart(f.getFullPathName().toRawUTF8(), bpm, minBars, maxBars)); }
  juce::String generateMidi64(const juce::var& params){ auto s = juce::JSON::toString(params); auto out = ac_generate_midi64(s.toRawUTF8()); juce::String b64(out); if (ac_free) ac_free(out); return b64; }
  juce::var generateNotes(const juce::var& params){ auto s = juce::JSON::toString(params); return callJson(ac_generate_json(s.toRawUTF8())); }
};
