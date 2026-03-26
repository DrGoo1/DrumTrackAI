// MidiUtils.h - MIDI conversion utilities
#pragma once
#include <juce_audio_basics/juce_audio_basics.h>

namespace MidiUtils
{
    juce::MemoryBlock sequenceToSMF (const juce::MidiMessageSequence& seq, double ppqPerQuarter = 960.0);
    bool smfToSequence (const void* data, size_t size, juce::MidiMessageSequence& outSeq);
    juce::String toBase64 (const juce::MemoryBlock& mb);
    bool fromBase64 (const juce::String& b64, juce::MemoryBlock& out);
}
