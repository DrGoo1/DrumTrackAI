// PluginEditor.h - GUI for the plugin
#pragma once

#include <juce_gui_extra/juce_gui_extra.h>
#include "PluginProcessor.h"

class DrumTracKAIConnectorAudioProcessorEditor  : public juce::AudioProcessorEditor,
                                                  private juce::Button::Listener,
                                                  private juce::Timer
{
public:
    explicit DrumTracKAIConnectorAudioProcessorEditor (DrumTracKAIConnectorAudioProcessor&);
    ~DrumTracKAIConnectorAudioProcessorEditor() override;

    void paint (juce::Graphics&) override;
    void resized() override;

private:
    void buttonClicked (juce::Button* b) override;
    void timerCallback() override;

    class MidiDragComponent : public juce::Component,
                              public juce::DragAndDropContainer
    {
    public:
        MidiDragComponent (DrumTracKAIConnectorAudioProcessor& p, juce::String name);

        void paint (juce::Graphics& g) override;
        void mouseDown (const juce::MouseEvent& e) override;

    private:
        DrumTracKAIConnectorAudioProcessor& processor;
        juce::String labelText;
    };

    DrumTracKAIConnectorAudioProcessor& processor;

    juce::Label serverLabel, apiKeyLabel, statusLabel;
    juce::TextEditor serverEditor, apiKeyEditor;
    juce::TextButton analyzeAudioButton { "Analyze Last Audio" };
    juce::TextButton analyzeMidiButton  { "Analyze MIDI" };
    juce::TextButton clearButton { "Clear" };
    
    // Guide track controls
    juce::Label guideLabel;
    juce::ToggleButton guideEnableButton { "Use this track as guide" };
    juce::ComboBox guideInstrumentCombo;
    
    MidiDragComponent midiDrag { processor, "Drag MIDI to DAW" };

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (DrumTracKAIConnectorAudioProcessorEditor)
};
