#include "MainComponent.h"

MainComponent::MainComponent()
{
    setSize(800, 600);
    
    // Initialize orchestrator
    orchestrator = std::make_unique<DCSMOrchestrator>("DrumTracKAI Hybrid");
    
    // Setup UI components
    addAndMakeVisible(loadButton);
    loadButton.setButtonText("Load Audio File");
    loadButton.onClick = [this] {
        juce::FileChooser chooser("Select audio file", {}, "*.wav;*.mp3;*.flac;*.aac");
        if (chooser.browseForFileToOpen()) {
            processAudioFile(chooser.getResult());
        }
    };
    
    addAndMakeVisible(playButton);
    playButton.setButtonText("Play");
    playButton.onClick = [this] {
        if (orchestrator) {
            orchestrator->adapter.play(0.0);
            updateStatus("Playing...");
        }
    };
    playButton.setEnabled(false);
    
    addAndMakeVisible(stopButton);
    stopButton.setButtonText("Stop");
    stopButton.onClick = [this] {
        if (orchestrator) {
            orchestrator->adapter.stop();
            updateStatus("Stopped");
        }
    };
    stopButton.setEnabled(false);
    
    addAndMakeVisible(exportButton);
    exportButton.setButtonText("Export MIDI");
    exportButton.onClick = [this] {
        if (!currentAudioFile.exists()) return;
        
        juce::FileChooser chooser("Save MIDI file", {}, "*.mid");
        if (chooser.browseForFileToSave(true)) {
            // Export MIDI using orchestrator
            juce::DynamicObject::Ptr params = new juce::DynamicObject();
            params->setProperty("bpm", 120.0);
            params->setProperty("start", 0.0);
            params->setProperty("end", 32.0);
            params->setProperty("style", styleCombo.getText());
            params->setProperty("label", "verse");
            params->setProperty("density", densitySlider.getValue());
            params->setProperty("swing", swingSlider.getValue());
            params->setProperty("swing_preset", swingPresetCombo.getText());
            params->setProperty("vel_preset", velocityPresetCombo.getText());
            params->setProperty("fill_preset", fillPresetCombo.getText());
            
            auto b64 = orchestrator->core.generateMidi64(juce::var(params.get()));
            juce::MemoryBlock data;
            juce::MemoryOutputStream mos(data, false);
            juce::Base64::convertFromBase64(mos, b64);
            
            auto file = chooser.getResult();
            file.replaceWithData(data.getData(), data.getSize());
            updateStatus("MIDI exported to " + file.getFileName());
        }
    };
    exportButton.setEnabled(false);
    
    // Style combo
    addAndMakeVisible(styleCombo);
    addAndMakeVisible(styleLabel);
    styleLabel.setText("Style:", juce::dontSendNotification);
    styleLabel.attachToComponent(&styleCombo, true);
    styleCombo.addItem("Rock", 1);
    styleCombo.addItem("Funk", 2);
    styleCombo.addItem("Jazz", 3);
    styleCombo.addItem("Latin", 4);
    styleCombo.setSelectedId(1);
    
    // Density slider
    addAndMakeVisible(densitySlider);
    addAndMakeVisible(densityLabel);
    densityLabel.setText("Density:", juce::dontSendNotification);
    densityLabel.attachToComponent(&densitySlider, true);
    densitySlider.setRange(0.0, 1.0, 0.01);
    densitySlider.setValue(0.65);
    densitySlider.setSliderStyle(juce::Slider::LinearHorizontal);
    densitySlider.setTextBoxStyle(juce::Slider::TextBoxRight, false, 60, 20);
    
    // Swing slider
    addAndMakeVisible(swingSlider);
    addAndMakeVisible(swingLabel);
    swingLabel.setText("Swing:", juce::dontSendNotification);
    swingLabel.attachToComponent(&swingSlider, true);
    swingSlider.setRange(0.0, 0.5, 0.01);
    swingSlider.setValue(0.1);
    swingSlider.setSliderStyle(juce::Slider::LinearHorizontal);
    swingSlider.setTextBoxStyle(juce::Slider::TextBoxRight, false, 60, 20);
    
    // Preset combos
    addAndMakeVisible(swingPresetCombo);
    swingPresetCombo.addItem("Off", 1);
    swingPresetCombo.addItem("Light", 2);
    swingPresetCombo.addItem("Heavy", 3);
    swingPresetCombo.setSelectedId(2);
    
    addAndMakeVisible(velocityPresetCombo);
    velocityPresetCombo.addItem("Flat", 1);
    velocityPresetCombo.addItem("Accent 2/4", 2);
    velocityPresetCombo.addItem("Funk 16", 3);
    velocityPresetCombo.setSelectedId(2);
    
    addAndMakeVisible(fillPresetCombo);
    fillPresetCombo.addItem("None", 1);
    fillPresetCombo.addItem("Random", 2);
    fillPresetCombo.addItem("Tom Run", 3);
    fillPresetCombo.addItem("Snare Buzz", 4);
    fillPresetCombo.addItem("EDM Riser", 5);
    fillPresetCombo.setSelectedId(2);
    
    // Status label
    addAndMakeVisible(statusLabel);
    statusLabel.setJustificationType(juce::Justification::centred);
    
    // Load Rust library
    loadRustLibrary();
}

MainComponent::~MainComponent()
{
}

void MainComponent::paint(juce::Graphics& g)
{
    g.fillAll(juce::Colours::darkgrey);
    
    g.setColour(juce::Colours::white);
    g.setFont(24.0f);
    g.drawText("DrumTracKAI Hybrid v1.2", 10, 10, getWidth() - 20, 30, juce::Justification::centred);
    
    if (isDragOver) {
        g.setColour(juce::Colours::lightblue.withAlpha(0.3f));
        g.fillRect(getLocalBounds().reduced(10));
        g.setColour(juce::Colours::lightblue);
        g.drawRect(getLocalBounds().reduced(10), 2);
        g.setFont(18.0f);
        g.drawText("Drop audio file here", getLocalBounds(), juce::Justification::centred);
    }
}

void MainComponent::resized()
{
    auto area = getLocalBounds().reduced(10);
    area.removeFromTop(50); // Title space
    
    // Top row - transport controls
    auto transportArea = area.removeFromTop(40);
    loadButton.setBounds(transportArea.removeFromLeft(120));
    transportArea.removeFromLeft(10);
    playButton.setBounds(transportArea.removeFromLeft(80));
    transportArea.removeFromLeft(10);
    stopButton.setBounds(transportArea.removeFromLeft(80));
    transportArea.removeFromLeft(10);
    exportButton.setBounds(transportArea.removeFromLeft(100));
    
    area.removeFromTop(20);
    
    // Waveform area
    auto waveformArea = area.removeFromTop(150);
    if (waveform) {
        waveform->setBounds(waveformArea);
    }
    
    area.removeFromTop(20);
    
    // Controls area
    auto controlsArea = area.removeFromTop(200);
    
    // Style
    auto styleArea = controlsArea.removeFromTop(30);
    styleArea.removeFromLeft(80); // Label space
    styleCombo.setBounds(styleArea.removeFromLeft(150));
    
    controlsArea.removeFromTop(10);
    
    // Density
    auto densityArea = controlsArea.removeFromTop(30);
    densityArea.removeFromLeft(80); // Label space
    densitySlider.setBounds(densityArea.removeFromLeft(200));
    
    controlsArea.removeFromTop(10);
    
    // Swing
    auto swingArea = controlsArea.removeFromTop(30);
    swingArea.removeFromLeft(80); // Label space
    swingSlider.setBounds(swingArea.removeFromLeft(200));
    
    controlsArea.removeFromTop(10);
    
    // Presets row
    auto presetsArea = controlsArea.removeFromTop(30);
    swingPresetCombo.setBounds(presetsArea.removeFromLeft(100));
    presetsArea.removeFromLeft(10);
    velocityPresetCombo.setBounds(presetsArea.removeFromLeft(100));
    presetsArea.removeFromLeft(10);
    fillPresetCombo.setBounds(presetsArea.removeFromLeft(100));
    
    // Status at bottom
    statusLabel.setBounds(area.removeFromBottom(30));
}

bool MainComponent::isInterestedInFileDrag(const juce::StringArray& files)
{
    for (const auto& file : files) {
        if (file.endsWith(".wav") || file.endsWith(".mp3") || 
            file.endsWith(".flac") || file.endsWith(".aac")) {
            return true;
        }
    }
    return false;
}

void MainComponent::fileDragEnter(const juce::StringArray&, int, int)
{
    isDragOver = true;
    repaint();
}

void MainComponent::fileDragExit(const juce::StringArray&)
{
    isDragOver = false;
    repaint();
}

void MainComponent::filesDropped(const juce::StringArray& files, int, int)
{
    isDragOver = false;
    repaint();
    
    if (files.size() > 0) {
        juce::File audioFile(files[0]);
        processAudioFile(audioFile);
    }
}

void MainComponent::loadRustLibrary()
{
#if JUCE_MAC
    auto dylib = juce::File::getSpecialLocation(juce::File::currentExecutableFile)
                   .getParentDirectory().getChildFile("libaudio_core_ffi.dylib");
#elif JUCE_WINDOWS
    auto dylib = juce::File::getSpecialLocation(juce::File::currentExecutableFile)
                   .getParentDirectory().getChildFile("audio_core_ffi.dll");
#else
    auto dylib = juce::File::getSpecialLocation(juce::File::currentExecutableFile)
                   .getParentDirectory().getChildFile("libaudio_core_ffi.so");
#endif

    if (dylib.exists() && orchestrator->loadRust(dylib)) {
        rustLibraryLoaded = true;
        updateStatus("Rust FFI library loaded successfully");
    } else {
        rustLibraryLoaded = false;
        updateStatus("Failed to load Rust FFI library: " + dylib.getFullPathName());
    }
}

void MainComponent::processAudioFile(const juce::File& file)
{
    if (!rustLibraryLoaded) {
        updateStatus("Rust library not loaded");
        return;
    }
    
    if (!file.exists()) {
        updateStatus("File does not exist");
        return;
    }
    
    currentAudioFile = file;
    updateStatus("Processing: " + file.getFileName());
    
    // Create waveform component
    waveform = std::make_unique<DCSMWaveformComponent>(orchestrator->adapter.engine, file);
    addAndMakeVisible(*waveform);
    resized();
    
    // Process with orchestrator
    try {
        auto style = styleCombo.getText().toLowerCase();
        orchestrator->processFile(file, style);
        
        playButton.setEnabled(true);
        stopButton.setEnabled(true);
        exportButton.setEnabled(true);
        
        updateStatus("Ready - " + file.getFileName() + " processed successfully");
    } catch (const std::exception& e) {
        updateStatus("Error processing file: " + juce::String(e.what()));
    }
}

void MainComponent::updateStatus(const juce::String& message)
{
    statusLabel.setText(message, juce::dontSendNotification);
}
