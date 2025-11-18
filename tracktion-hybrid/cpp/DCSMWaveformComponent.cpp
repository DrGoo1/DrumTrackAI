#include "DCSMWaveformComponent.h"

DCSMWaveformComponent::DCSMWaveformComponent(tracktion::engine::Engine& eng, const juce::File& af)
: engine(eng), file(eng, af)
{ 
    thumb = std::make_unique<tracktion::engine::SmartThumbnail>(engine, file, *this, nullptr); 
}

void DCSMWaveformComponent::paint(juce::Graphics& g)
{
    g.fillAll(juce::Colours::black);
    g.setColour(juce::Colours::lightblue);
    
    if (thumb && thumb->isFullyLoaded()) {
        auto start = tracktion::core::TimePosition::fromSeconds(0.0);
        auto end   = tracktion::core::TimePosition::fromSeconds(thumb->getTotalLength());
        auto range = tracktion::core::TimeRange(start, end);
        thumb->drawChannels(g, getLocalBounds(), range, 1.0f);
    } else {
        g.setColour(juce::Colours::grey);
        g.drawText("Loading waveform...", getLocalBounds(), juce::Justification::centred);
    }
}

void DCSMWaveformComponent::resized()
{
    // No-op; SmartThumbnail manages its own cache and repainting
}
