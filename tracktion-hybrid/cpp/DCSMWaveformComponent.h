#pragma once
#include <tracktion_engine/tracktion_engine.h>

struct DCSMWaveformComponent : public juce::Component {
  tracktion::engine::Engine& engine; 
  tracktion::engine::AudioFile file;
  std::unique_ptr<tracktion::engine::SmartThumbnail> thumb;
  
  DCSMWaveformComponent(tracktion::engine::Engine& eng, const juce::File& audioFile);
  void paint(juce::Graphics& g) override;
  void resized() override;
};
