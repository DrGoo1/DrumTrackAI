/**
 * Integration Examples for DrumTracKAI Tracktion Hybrid v1.2
 * 
 * These examples show how to integrate the Rust FFI library
 * with existing JUCE/Tracktion Engine applications.
 */

#include <juce_gui_basics/juce_gui_basics.h>
#include <tracktion_engine/tracktion_engine.h>
#include "DCSMOrchestrator.h"

namespace te = tracktion::engine;

//==============================================================================
// Example 1: Basic Integration
//==============================================================================
class BasicDrumTrackExample
{
public:
    BasicDrumTrackExample()
    {
        // Initialize orchestrator
        orchestrator = std::make_unique<DCSMOrchestrator>("DrumTracKAI Basic");
        
        // Load Rust FFI library
        loadRustLibrary();
    }
    
    void processAudioFile(const juce::File& audioFile, const juce::String& style = "rock")
    {
        if (!rustLoaded) {
            juce::AlertWindow::showMessageBox(juce::AlertWindow::WarningIcon,
                                            "Error", "Rust FFI library not loaded");
            return;
        }
        
        // Process with orchestrator - this will:
        // 1. Import audio file
        // 2. Analyze tempo and structure
        // 3. Generate drum patterns per section
        // 4. Create MIDI clips
        // 5. Start playback
        orchestrator->processFile(audioFile, style);
    }
    
private:
    void loadRustLibrary()
    {
        auto appDir = juce::File::getSpecialLocation(juce::File::currentExecutableFile).getParentDirectory();
        
#if JUCE_WINDOWS
        auto ffiLib = appDir.getChildFile("audio_core_ffi.dll");
#elif JUCE_MAC
        auto ffiLib = appDir.getChildFile("libaudio_core_ffi.dylib");
#else
        auto ffiLib = appDir.getChildFile("libaudio_core_ffi.so");
#endif
        
        rustLoaded = orchestrator->loadRust(ffiLib);
        if (!rustLoaded) {
            DBG("Failed to load Rust FFI library: " + ffiLib.getFullPathName());
        }
    }
    
    std::unique_ptr<DCSMOrchestrator> orchestrator;
    bool rustLoaded = false;
};

//==============================================================================
// Example 2: Custom UI Integration
//==============================================================================
class DrumGeneratorComponent : public juce::Component
{
public:
    DrumGeneratorComponent() : orchestrator("DrumTracKAI Custom")
    {
        // Setup UI
        addAndMakeVisible(styleCombo);
        styleCombo.addItem("Rock", 1);
        styleCombo.addItem("Funk", 2);
        styleCombo.addItem("Jazz", 3);
        styleCombo.addItem("Latin", 4);
        styleCombo.setSelectedId(1);
        
        addAndMakeVisible(generateButton);
        generateButton.setButtonText("Generate Drums");
        generateButton.onClick = [this] { generateDrums(); };
        
        addAndMakeVisible(exportButton);
        exportButton.setButtonText("Export MIDI");
        exportButton.onClick = [this] { exportMIDI(); };
        
        // Load Rust library
        loadRustLibrary();
    }
    
    void resized() override
    {
        auto area = getLocalBounds().reduced(10);
        styleCombo.setBounds(area.removeFromTop(30));
        area.removeFromTop(10);
        generateButton.setBounds(area.removeFromTop(30));
        area.removeFromTop(10);
        exportButton.setBounds(area.removeFromTop(30));
    }
    
private:
    void generateDrums()
    {
        if (!rustLoaded) return;
        
        // Create generation parameters
        juce::DynamicObject::Ptr params = new juce::DynamicObject();
        params->setProperty("bpm", 120.0);
        params->setProperty("start", 0.0);
        params->setProperty("end", 16.0);
        params->setProperty("style", styleCombo.getText().toLowerCase());
        params->setProperty("label", "verse");
        params->setProperty("density", 0.7);
        params->setProperty("swing_preset", "light");
        params->setProperty("vel_preset", "accent24");
        params->setProperty("fill_preset", "random");
        
        // Generate notes
        auto result = orchestrator.core.generateNotes(juce::var(params.get()));
        
        // Create MIDI clip and add notes
        auto* clip = orchestrator.adapter.ensureDrumMidiClip(0, 16.0);
        if (clip && result.hasProperty("notes")) {
            if (auto* notesArray = result.getProperty("notes").getArray()) {
                for (auto* noteVar : *notesArray) {
                    auto lane = noteVar->getProperty("lane").toString();
                    auto time = (double) noteVar->getProperty("time");
                    auto length = (double) noteVar->getProperty("len");
                    auto velocity = (int) noteVar->getProperty("vel");
                    
                    int midiNote = orchestrator.laneToMidi(lane);
                    orchestrator.adapter.addMidiNote(*clip, midiNote, time, length, velocity);
                }
            }
        }
    }
    
    void exportMIDI()
    {
        if (!rustLoaded) return;
        
        juce::FileChooser chooser("Export MIDI", {}, "*.mid");
        if (chooser.browseForFileToSave(true)) {
            // Generate MIDI data
            juce::DynamicObject::Ptr params = new juce::DynamicObject();
            params->setProperty("bpm", 120.0);
            params->setProperty("start", 0.0);
            params->setProperty("end", 16.0);
            params->setProperty("style", styleCombo.getText().toLowerCase());
            params->setProperty("label", "verse");
            
            auto midiB64 = orchestrator.core.generateMidi64(juce::var(params.get()));
            
            // Decode and save
            juce::MemoryBlock midiData;
            juce::Base64::convertFromBase64(midiData, midiB64);
            
            auto file = chooser.getResult();
            file.replaceWithData(midiData.getData(), midiData.getSize());
            
            juce::AlertWindow::showMessageBox(juce::AlertWindow::InfoIcon,
                                            "Export Complete", 
                                            "MIDI exported to: " + file.getFileName());
        }
    }
    
    void loadRustLibrary()
    {
        auto appDir = juce::File::getSpecialLocation(juce::File::currentExecutableFile).getParentDirectory();
        
#if JUCE_WINDOWS
        auto ffiLib = appDir.getChildFile("audio_core_ffi.dll");
#elif JUCE_MAC
        auto ffiLib = appDir.getChildFile("libaudio_core_ffi.dylib");
#else
        auto ffiLib = appDir.getChildFile("libaudio_core_ffi.so");
#endif
        
        rustLoaded = orchestrator.loadRust(ffiLib);
    }
    
    DCSMOrchestrator orchestrator;
    juce::ComboBox styleCombo;
    juce::TextButton generateButton;
    juce::TextButton exportButton;
    bool rustLoaded = false;
};

//==============================================================================
// Example 3: Batch Processing
//==============================================================================
class BatchDrumProcessor
{
public:
    BatchDrumProcessor() : orchestrator("DrumTracKAI Batch")
    {
        loadRustLibrary();
    }
    
    void processDirectory(const juce::File& inputDir, const juce::File& outputDir)
    {
        if (!rustLoaded) return;
        
        auto audioFiles = inputDir.findChildFiles(juce::File::findFiles, false, "*.wav;*.mp3;*.flac");
        
        for (const auto& audioFile : audioFiles) {
            processFileToMIDI(audioFile, outputDir);
        }
    }
    
private:
    void processFileToMIDI(const juce::File& audioFile, const juce::File& outputDir)
    {
        // Analyze the audio file
        auto analysis = orchestrator.core.analyze(audioFile);
        auto bpm = (double) analysis.getProperty("tempo", 120.0);
        
        // Smart sectionization
        auto sections = orchestrator.core.sectionizeSmart(audioFile, (float) bpm);
        
        if (auto* sectionsArray = sections.getProperty("sections").getArray()) {
            for (auto* section : *sectionsArray) {
                auto start = (double) section->getProperty("start");
                auto end = (double) section->getProperty("end");
                auto label = section->getProperty("label").toString();
                
                // Generate drums for this section
                juce::DynamicObject::Ptr params = new juce::DynamicObject();
                params->setProperty("bpm", bpm);
                params->setProperty("start", start);
                params->setProperty("end", end);
                params->setProperty("style", "rock");
                params->setProperty("label", label);
                params->setProperty("density", 0.65);
                
                auto midiB64 = orchestrator.core.generateMidi64(juce::var(params.get()));
                
                // Save MIDI file
                juce::MemoryBlock midiData;
                juce::Base64::convertFromBase64(midiData, midiB64);
                
                auto outputFile = outputDir.getChildFile(audioFile.getFileNameWithoutExtension() + 
                                                       "_" + label + ".mid");
                outputFile.replaceWithData(midiData.getData(), midiData.getSize());
            }
        }
    }
    
    void loadRustLibrary()
    {
        auto appDir = juce::File::getSpecialLocation(juce::File::currentExecutableFile).getParentDirectory();
        
#if JUCE_WINDOWS
        auto ffiLib = appDir.getChildFile("audio_core_ffi.dll");
#elif JUCE_MAC
        auto ffiLib = appDir.getChildFile("libaudio_core_ffi.dylib");
#else
        auto ffiLib = appDir.getChildFile("libaudio_core_ffi.so");
#endif
        
        rustLoaded = orchestrator.loadRust(ffiLib);
    }
    
    DCSMOrchestrator orchestrator;
    bool rustLoaded = false;
};

//==============================================================================
// Example 4: Real-time Parameter Control
//==============================================================================
class RealtimeDrumController : public juce::Component, public juce::Slider::Listener
{
public:
    RealtimeDrumController() : orchestrator("DrumTracKAI Realtime")
    {
        // Setup parameter controls
        addAndMakeVisible(densitySlider);
        densitySlider.setRange(0.0, 1.0, 0.01);
        densitySlider.setValue(0.65);
        densitySlider.addListener(this);
        
        addAndMakeVisible(swingSlider);
        swingSlider.setRange(0.0, 0.5, 0.01);
        swingSlider.setValue(0.1);
        swingSlider.addListener(this);
        
        loadRustLibrary();
    }
    
    void sliderValueChanged(juce::Slider* slider) override
    {
        // Regenerate drums with new parameters
        regenerateDrums();
    }
    
    void resized() override
    {
        auto area = getLocalBounds().reduced(10);
        densitySlider.setBounds(area.removeFromTop(30));
        area.removeFromTop(10);
        swingSlider.setBounds(area.removeFromTop(30));
    }
    
private:
    void regenerateDrums()
    {
        if (!rustLoaded) return;
        
        // Create new parameters with current slider values
        juce::DynamicObject::Ptr params = new juce::DynamicObject();
        params->setProperty("bpm", 120.0);
        params->setProperty("start", 0.0);
        params->setProperty("end", 8.0);
        params->setProperty("style", "rock");
        params->setProperty("label", "verse");
        params->setProperty("density", densitySlider.getValue());
        params->setProperty("swing", swingSlider.getValue());
        params->setProperty("seed", juce::Random::getSystemRandom().nextInt64());
        
        // Generate and update MIDI clip
        auto result = orchestrator.core.generateNotes(juce::var(params.get()));
        
        // Clear existing notes and add new ones
        auto* clip = orchestrator.adapter.ensureDrumMidiClip(0, 8.0);
        if (clip) {
            clip->getSequence().clear(nullptr);
            
            if (auto* notesArray = result.getProperty("notes").getArray()) {
                for (auto* noteVar : *notesArray) {
                    auto lane = noteVar->getProperty("lane").toString();
                    auto time = (double) noteVar->getProperty("time");
                    auto length = (double) noteVar->getProperty("len");
                    auto velocity = (int) noteVar->getProperty("vel");
                    
                    int midiNote = orchestrator.laneToMidi(lane);
                    orchestrator.adapter.addMidiNote(*clip, midiNote, time, length, velocity);
                }
            }
        }
    }
    
    void loadRustLibrary()
    {
        auto appDir = juce::File::getSpecialLocation(juce::File::currentExecutableFile).getParentDirectory();
        
#if JUCE_WINDOWS
        auto ffiLib = appDir.getChildFile("audio_core_ffi.dll");
#elif JUCE_MAC
        auto ffiLib = appDir.getChildFile("libaudio_core_ffi.dylib");
#else
        auto ffiLib = appDir.getChildFile("libaudio_core_ffi.so");
#endif
        
        rustLoaded = orchestrator.loadRust(ffiLib);
    }
    
    DCSMOrchestrator orchestrator;
    juce::Slider densitySlider;
    juce::Slider swingSlider;
    bool rustLoaded = false;
};
