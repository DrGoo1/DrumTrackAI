// PluginEditor.cpp - GUI implementation
#include "PluginEditor.h"

using namespace juce;

DrumTracKAIConnectorAudioProcessorEditor::DrumTracKAIConnectorAudioProcessorEditor (DrumTracKAIConnectorAudioProcessor& p)
    : AudioProcessorEditor (&p), processor (p)
{
    setSize (500, 380); // Increased height for guide controls

    serverLabel.setText ("Server URL:", dontSendNotification);
    serverLabel.setJustificationType (Justification::centredLeft);
    addAndMakeVisible (serverLabel);

    serverEditor.setText (processor.getServerUrl());
    serverEditor.setTextToShowWhenEmpty ("http://localhost:8000/api/generate", Colours::grey);
    addAndMakeVisible (serverEditor);

    apiKeyLabel.setText ("API Key:", dontSendNotification);
    apiKeyLabel.setJustificationType (Justification::centredLeft);
    addAndMakeVisible (apiKeyLabel);

    apiKeyEditor.setText (processor.getApiKey());
    apiKeyEditor.setTextToShowWhenEmpty ("optional", Colours::grey);
    addAndMakeVisible (apiKeyEditor);

    analyzeAudioButton.addListener (this);
    addAndMakeVisible (analyzeAudioButton);

    analyzeMidiButton.addListener (this);
    addAndMakeVisible (analyzeMidiButton);

    clearButton.addListener (this);
    addAndMakeVisible (clearButton);
    
    // Guide track controls
    addAndMakeVisible (guideLabel);
    guideLabel.setText ("Guide Track", dontSendNotification);
    guideLabel.setJustificationType (Justification::centredLeft);
    
    addAndMakeVisible (guideEnableButton);
    guideEnableButton.setClickingTogglesState (true);
    guideEnableButton.setToggleState (processor.getGuideEnabled(), dontSendNotification);
    guideEnableButton.setTooltip ("If enabled, this track's audio/MIDI will be treated as the primary guide for drum generation.");
    
    addAndMakeVisible (guideInstrumentCombo);
    guideInstrumentCombo.addItem ("Song Mix", 1);
    guideInstrumentCombo.addItem ("Bass", 2);
    guideInstrumentCombo.addItem ("Guitar", 3);
    guideInstrumentCombo.addItem ("Keys", 4);
    guideInstrumentCombo.addItem ("Vocal", 5);
    guideInstrumentCombo.addItem ("Other", 6);
    guideInstrumentCombo.setTooltip ("Tell DrumTracKAI what instrument this guide track primarily is.");
    guideInstrumentCombo.setSelectedId (1);

    statusLabel.setText ("Ready - waiting for audio/MIDI", dontSendNotification);
    statusLabel.setJustificationType (Justification::centredLeft);
    statusLabel.setColour (Label::textColourId, Colours::lightblue);
    addAndMakeVisible (statusLabel);

    addAndMakeVisible (midiDrag);

    startTimer (500); // Update status every 500ms
}

DrumTracKAIConnectorAudioProcessorEditor::~DrumTracKAIConnectorAudioProcessorEditor() = default;

void DrumTracKAIConnectorAudioProcessorEditor::paint (Graphics& g)
{
    g.fillAll (Colour (0xff2b2b2b));
    
    // Title
    g.setColour (Colours::white);
    g.setFont (Font (20.0f, Font::bold));
    g.drawText ("DrumTracKAI Connector", 10, 5, getWidth() - 20, 30, Justification::centred);
    
    // Info text
    g.setFont (Font (11.0f));
    g.setColour (Colours::grey);
    g.drawText ("Captures audio/MIDI and generates drum tracks via AI", 
                10, 235, getWidth() - 20, 20, Justification::centred);
}

void DrumTracKAIConnectorAudioProcessorEditor::resized()
{
    auto r = getLocalBounds().reduced (10);
    r.removeFromTop (35); // Title space

    auto topRow = r.removeFromTop (24);
    serverLabel.setBounds (topRow.removeFromLeft (85));
    serverEditor.setBounds (topRow);

    auto row2 = r.removeFromTop (24).withTrimmedTop (6);
    apiKeyLabel.setBounds (row2.removeFromLeft (85));
    apiKeyEditor.setBounds (row2);

    auto row3 = r.removeFromTop (34).withTrimmedTop (10);
    analyzeAudioButton.setBounds (row3.removeFromLeft (145));
    analyzeMidiButton.setBounds (row3.removeFromLeft (145).withTrimmedLeft (5));
    clearButton.setBounds (row3.withTrimmedLeft (5));
    
    // Guide track controls
    r.removeFromTop (12);
    guideLabel.setBounds (r.removeFromTop (18));
    r.removeFromTop (4);
    guideEnableButton.setBounds (r.removeFromTop (22));
    r.removeFromTop (4);
    guideInstrumentCombo.setBounds (r.removeFromTop (24));

    auto row4 = r.removeFromTop (22).withTrimmedTop (10);
    statusLabel.setBounds (row4);

    r.removeFromTop (10);
    midiDrag.setBounds (r.removeFromTop (70));
}

void DrumTracKAIConnectorAudioProcessorEditor::buttonClicked (Button* b)
{
    processor.setServerUrl (serverEditor.getText());
    processor.setApiKey (apiKeyEditor.getText());
    
    // Save guide track settings
    processor.setGuideEnabled (guideEnableButton.getToggleState());
    
    auto guideId = guideInstrumentCombo.getSelectedId();
    juce::String guideInstrument = "mix";
    switch (guideId)
    {
        case 2: guideInstrument = "bass";   break;
        case 3: guideInstrument = "guitar"; break;
        case 4: guideInstrument = "keys";   break;
        case 5: guideInstrument = "vocal";  break;
        case 6: guideInstrument = "other";  break;
        case 1:
        default: guideInstrument = "mix";   break;
    }
    processor.setGuideInstrument (guideInstrument);

    if (b == &analyzeAudioButton)
    {
        statusLabel.setText ("Sending audio to DrumTracKAI...", dontSendNotification);
        statusLabel.setColour (Label::textColourId, Colours::yellow);
        processor.startAudioAnalysisRequest();
    }
    else if (b == &analyzeMidiButton)
    {
        statusLabel.setText ("Sending MIDI to DrumTracKAI...", dontSendNotification);
        statusLabel.setColour (Label::textColourId, Colours::yellow);
        processor.startMidiAnalysisRequest();
    }
    else if (b == &clearButton)
    {
        processor.clearGeneratedSequence();
        statusLabel.setText ("Cleared - ready for new analysis", dontSendNotification);
        statusLabel.setColour (Label::textColourId, Colours::lightblue);
    }
}

void DrumTracKAIConnectorAudioProcessorEditor::timerCallback()
{
    if (processor.isAnalyzing())
    {
        statusLabel.setText ("Analyzing... please wait", dontSendNotification);
        statusLabel.setColour (Label::textColourId, Colours::orange);
    }
    else if (processor.hasGeneratedDrums())
    {
        statusLabel.setText ("✓ Drum track ready! Drag MIDI below or it will play automatically", dontSendNotification);
        statusLabel.setColour (Label::textColourId, Colours::lightgreen);
    }
}

// --- MidiDragComponent ---

DrumTracKAIConnectorAudioProcessorEditor::MidiDragComponent::MidiDragComponent (DrumTracKAIConnectorAudioProcessor& p,
                                                                                String name)
    : processor (p), labelText (std::move (name))
{
}

void DrumTracKAIConnectorAudioProcessorEditor::MidiDragComponent::paint (Graphics& g)
{
    auto bounds = getLocalBounds().toFloat();
    
    bool hasDrums = processor.hasGeneratedDrums();
    
    if (hasDrums)
    {
        g.setColour (Colour (0xff3a5f3a)); // Dark green background
        g.fillRoundedRectangle (bounds, 10.0f);
        g.setColour (Colours::lightgreen);
    }
    else
    {
        g.setColour (Colour (0xff1a1a1a)); // Dark grey
        g.fillRoundedRectangle (bounds, 10.0f);
        g.setColour (Colours::grey);
    }
    
    g.drawRoundedRectangle (bounds, 10.0f, 2.0f);

    g.setFont (Font (16.0f, Font::bold));
    g.drawFittedText (hasDrums ? "🎵 " + labelText : "Waiting for drum track...", 
                      getLocalBounds(), Justification::centred, 2);
}

void DrumTracKAIConnectorAudioProcessorEditor::MidiDragComponent::mouseDown (const MouseEvent& e)
{
    if (! processor.isAnalyzing())
    {
        auto smf = processor.getGeneratedMidiSMF();
        if (smf.getSize() > 0)
        {
            // Write to temp file for drag-and-drop
            auto tempFile = File::getSpecialLocation (File::tempDirectory)
                                .getNonexistentChildFile ("DrumTracKAI_Drums", ".mid");

            {
                FileOutputStream fo (tempFile);
                fo.write (smf.getData(), smf.getSize());
            }

            auto description = tempFile.getFullPathName();
            var dragDesc (description);

            startDragging (dragDesc, this);
        }
    }

    Component::mouseDown (e);
}
