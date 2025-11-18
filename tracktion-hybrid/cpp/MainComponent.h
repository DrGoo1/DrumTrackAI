#pragma once
#include <tracktion_engine/tracktion_engine.h>
#include "DCSMOrchestrator.h"
#include "DCSMWaveformComponent.h"

class MainComponent : public juce::Component, public juce::FileDragAndDropTarget
{
public:
    MainComponent();
    ~MainComponent() override;

    void paint(juce::Graphics&) override;
    void resized() override;

    // File drag and drop
    bool isInterestedInFileDrag(const juce::StringArray& files) override;
    void fileDragEnter(const juce::StringArray& files, int x, int y) override;
    void fileDragExit(const juce::StringArray& files) override;
    void filesDropped(const juce::StringArray& files, int x, int y) override;

private:
    void loadRustLibrary();
    void processAudioFile(const juce::File& file);
    void updateStatus(const juce::String& message);

    std::unique_ptr<DCSMOrchestrator> orchestrator;
    std::unique_ptr<DCSMWaveformComponent> waveform;
    
    juce::TextButton loadButton;
    juce::TextButton playButton;
    juce::TextButton stopButton;
    juce::TextButton exportButton;
    
    juce::ComboBox styleCombo;
    juce::Slider densitySlider;
    juce::Slider swingSlider;
    juce::ComboBox swingPresetCombo;
    juce::ComboBox velocityPresetCombo;
    juce::ComboBox fillPresetCombo;
    
    juce::Label statusLabel;
    juce::Label styleLabel;
    juce::Label densityLabel;
    juce::Label swingLabel;
    
    bool isDragOver = false;
    bool rustLibraryLoaded = false;
    juce::File currentAudioFile;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(MainComponent)
};
