// PluginProcessor.cpp - Main audio processor implementation
#include "PluginProcessor.h"
#include "PluginEditor.h"
#include "MidiUtils.h"

using namespace juce;

DrumTracKAIConnectorAudioProcessor::DrumTracKAIConnectorAudioProcessor()
    : AudioProcessor (BusesProperties()
                      .withInput  ("Input",  AudioChannelSet::stereo(), true)
                      .withOutput ("Output", AudioChannelSet::stereo(), true))
{
    networkClient.setListener (this);
}

DrumTracKAIConnectorAudioProcessor::~DrumTracKAIConnectorAudioProcessor() = default;

bool DrumTracKAIConnectorAudioProcessor::isBusesLayoutSupported (const BusesLayout& layouts) const
{
    if (layouts.getMainInputChannelSet() != AudioChannelSet::stereo()
        || layouts.getMainOutputChannelSet() != AudioChannelSet::stereo())
        return false;
    return true;
}

void DrumTracKAIConnectorAudioProcessor::prepareToPlay (double sampleRate, int samplesPerBlock)
{
    currentSampleRate = sampleRate;
    const double secondsToStore = 30.0;
    ringSizeSamples = (int) (secondsToStore * sampleRate);
    audioRingBuffer.setSize (2, ringSizeSamples);
    audioRingBuffer.clear();
    ringWritePos = 0;
    capturedMidi.clear();
    generatedDrums.clear();
    generatedDrumsValid = false;
    lastPositionPPQ = 0.0;
}

void DrumTracKAIConnectorAudioProcessor::releaseResources()
{
}

void DrumTracKAIConnectorAudioProcessor::processBlock (AudioBuffer<float>& buffer, MidiBuffer& midi)
{
    ScopedNoDenormals noDenormals;
    const int numSamples = buffer.getNumSamples();
    const int numChans   = jmin (2, buffer.getNumChannels());

    // Write incoming audio into ring buffer
    for (int ch = 0; ch < numChans; ++ch)
    {
        auto* src = buffer.getReadPointer (ch);
        auto* dst = audioRingBuffer.getWritePointer (ch);
        int writePos = ringWritePos;
        for (int i = 0; i < numSamples; ++i)
        {
            dst[writePos] = src[i];
            if (++writePos >= ringSizeSamples)
                writePos = 0;
        }
    }
    ringWritePos += numSamples;
    while (ringWritePos >= ringSizeSamples)
        ringWritePos -= ringSizeSamples;

    // Capture incoming MIDI
    for (const auto metadata : midi)
    {
        auto msg = metadata.getMessage();
        double t = metadata.samplePosition / currentSampleRate;
        msg.setTimeStamp (t);
        capturedMidi.addEvent (msg);
    }

    // Output generated drums as MIDI
    if (generatedDrumsValid)
    {
        if (auto* playHead = getPlayHead())
        {
            juce::Optional<AudioPlayHead::PositionInfo> pos = playHead->getPosition();
            if (pos.hasValue() && pos->getIsPlaying())
            {
                MidiBuffer outMidi;
                auto numEvents = generatedDrums.getNumEvents();
                for (int i = 0; i < numEvents; ++i)
                {
                    const auto* ev = generatedDrums.getEventPointer (i);
                    auto m = ev->message;
                    double timeSec = m.getTimeStamp();
                    int outSample = (int) (timeSec * currentSampleRate);
                    if (outSample >= 0 && outSample < numSamples)
                        outMidi.addEvent (m, outSample);
                }
                midi.swapWith (outMidi);
            }
        }
    }
}

AudioProcessorEditor* DrumTracKAIConnectorAudioProcessor::createEditor()
{
    return new DrumTracKAIConnectorAudioProcessorEditor (*this);
}

void DrumTracKAIConnectorAudioProcessor::getStateInformation (MemoryBlock& destData)
{
    MemoryOutputStream mo (destData, false);
    mo.writeString (serverUrl);
    mo.writeString (apiKey);
    mo.writeString (selectedStyleId);
    
    // Guide track support
    mo.writeBool (guideEnabled);
    mo.writeString (guideInstrument);
}

void DrumTracKAIConnectorAudioProcessor::setStateInformation (const void* data, int sizeInBytes)
{
    MemoryInputStream mi (data, static_cast<size_t> (sizeInBytes), false);
    serverUrl       = mi.readString();
    apiKey          = mi.readString();
    selectedStyleId = mi.readString();
    
    // Guide track support (guard against older states with less data)
    if (! mi.isExhausted())
        guideEnabled = mi.readBool();
    if (! mi.isExhausted())
        guideInstrument = mi.readString();
}

void DrumTracKAIConnectorAudioProcessor::startAudioAnalysisRequest()
{
    if (networkClient.isBusy())
        return;

    // Export audio to WAV
    AudioBuffer<float> temp (audioRingBuffer.getNumChannels(), ringSizeSamples);
    for (int ch = 0; ch < temp.getNumChannels(); ++ch)
    {
        auto* dst = temp.getWritePointer (ch);
        auto* src = audioRingBuffer.getReadPointer (ch);
        int readPos = ringWritePos;
        for (int i = 0; i < ringSizeSamples; ++i)
        {
            dst[i] = src[readPos];
            if (++readPos >= ringSizeSamples)
                readPos = 0;
        }
    }

    MemoryBlock wavData;
    {
        MemoryOutputStream mo (wavData, false);
        WavAudioFormat fmt;
        std::unique_ptr<AudioFormatWriter> writer (fmt.createWriterFor (&mo,
                                                                        currentSampleRate,
                                                                        (unsigned int) temp.getNumChannels(),
                                                                        24,
                                                                        {},
                                                                        0));
        if (writer != nullptr)
            writer->writeFromAudioSampleBuffer (temp, 0, temp.getNumSamples());
    }

    DrumTracKAINetworkClient::Request req;
    req.apiUrl        = serverUrl;
    req.apiKey        = apiKey;
    req.bpm           = 120.0;
    req.timeSig       = "4/4";
    req.styleId       = selectedStyleId;
    
    // Guide track support
    req.guideEnabled    = guideEnabled;
    req.guideInstrument = guideInstrument;
    
    req.audioDataWav  = wavData;
    networkClient.startRequest (req);
}

void DrumTracKAIConnectorAudioProcessor::startMidiAnalysisRequest()
{
    if (networkClient.isBusy())
        return;

    MemoryBlock smf = MidiUtils::sequenceToSMF (capturedMidi);
    DrumTracKAINetworkClient::Request req;
    req.apiUrl       = serverUrl;
    req.apiKey       = apiKey;
    req.bpm          = 120.0;
    req.timeSig      = "4/4";
    req.styleId      = selectedStyleId;
    
    // Guide track support
    req.guideEnabled    = guideEnabled;
    req.guideInstrument = guideInstrument;
    
    req.midiDataSMF  = smf;
    networkClient.startRequest (req);
}

MemoryBlock DrumTracKAIConnectorAudioProcessor::getGeneratedMidiSMF() const
{
    if (! generatedDrumsValid)
        return {};
    return MidiUtils::sequenceToSMF (generatedDrums);
}

void DrumTracKAIConnectorAudioProcessor::clearGeneratedSequence()
{
    generatedDrums.clear();
    generatedDrumsValid = false;
}

void DrumTracKAIConnectorAudioProcessor::drumTracKAIRequestFinished (const DrumTracKAINetworkClient::Response& resp)
{
    if (! resp.ok || resp.midiDataSMF.getSize() == 0)
    {
        generatedDrums.clear();
        generatedDrumsValid = false;
        return;
    }

    MidiMessageSequence seq;
    if (MidiUtils::smfToSequence (resp.midiDataSMF.getData(), resp.midiDataSMF.getSize(), seq))
    {
        generatedDrums = seq;
        generatedDrumsValid = true;
    }
    else
    {
        generatedDrums.clear();
        generatedDrumsValid = false;
    }
}

AudioProcessor* JUCE_CALLTYPE createPluginFilter()
{
    return new DrumTracKAIConnectorAudioProcessor();
}
