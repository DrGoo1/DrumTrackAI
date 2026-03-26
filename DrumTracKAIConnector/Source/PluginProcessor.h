// PluginProcessor.h - Main audio processor
#pragma once

#include <juce_audio_processors/juce_audio_processors.h>
#include "NetworkClient.h"

class DrumTracKAIConnectorAudioProcessor  : public juce::AudioProcessor,
                                            private DrumTracKAINetworkClient::Listener
{
public:
    DrumTracKAIConnectorAudioProcessor();
    ~DrumTracKAIConnectorAudioProcessor() override;

    // AudioProcessor overrides
    const juce::String getName() const override                            { return "DrumTracKAI Connector"; }
    bool acceptsMidi() const override                                      { return true; }
    bool producesMidi() const override                                     { return true; }
    double getTailLengthSeconds() const override                           { return 0.0; }

    bool isBusesLayoutSupported (const BusesLayout& layouts) const override;
    void prepareToPlay (double sampleRate, int samplesPerBlock) override;
    void releaseResources() override;
    void processBlock (juce::AudioBuffer<float>&, juce::MidiBuffer&) override;

    // Program state
    juce::AudioProcessorEditor* createEditor() override;
    bool hasEditor() const override                                        { return true; }

    void getStateInformation (juce::MemoryBlock& destData) override;
    void setStateInformation (const void* data, int sizeInBytes) override;

    // GUI accessors
    void setServerUrl (const juce::String& url)    { serverUrl = url; }
    void setApiKey    (const juce::String& key)    { apiKey = key; }

    juce::String getServerUrl() const              { return serverUrl; }
    juce::String getApiKey() const                 { return apiKey; }

    bool isAnalyzing() const                       { return networkClient.isBusy(); }
    
    void setSelectedStyleId (const juce::String& style) { selectedStyleId = style; }
    juce::String getSelectedStyleId() const             { return selectedStyleId; }
    
    // Guide track support
    void setGuideEnabled (bool enabled)                 { guideEnabled = enabled; }
    bool getGuideEnabled() const                        { return guideEnabled; }
    void setGuideInstrument (const juce::String& id)    { guideInstrument = id; }
    juce::String getGuideInstrument() const             { return guideInstrument; }

    void startAudioAnalysisRequest();
    void startMidiAnalysisRequest();

    // Drag-and-drop helper: export generated MIDI as SMF
    juce::MemoryBlock getGeneratedMidiSMF() const;

    // Called from editor when user clears result
    void clearGeneratedSequence();
    
    bool hasGeneratedDrums() const { return generatedDrumsValid; }

private:
    // Network listener
    void drumTracKAIRequestFinished (const DrumTracKAINetworkClient::Response& resp) override;

    // Ring buffer for last few seconds of audio
    juce::AudioBuffer<float> audioRingBuffer;
    int ringWritePos = 0;
    int ringSizeSamples = 0;
    double currentSampleRate = 44100.0;

    // Captured MIDI buffer (if user wants to send MIDI instead of audio)
    juce::MidiMessageSequence capturedMidi;

    // Generated drum sequence
    juce::MidiMessageSequence generatedDrums;
    bool generatedDrumsValid = false;

    // Timing for playback
    double lastPositionPPQ = 0.0;

    DrumTracKAINetworkClient networkClient;
    juce::String serverUrl { "http://localhost:8000/api/generate" };
    juce::String apiKey    { "" };
    juce::String selectedStyleId { "default" };
    
    // Guide track support
    bool guideEnabled = true;                  // default: use current track as guide
    juce::String guideInstrument { "mix" };    // "mix", "bass", "guitar", "keys", "vocal", "other"

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (DrumTracKAIConnectorAudioProcessor)
};
