// MidiUtils.cpp - MIDI conversion implementations
#include "MidiUtils.h"

namespace MidiUtils
{
    juce::MemoryBlock sequenceToSMF (const juce::MidiMessageSequence& seq, double ppqPerQuarter)
    {
        juce::MidiFile mf;
        mf.setTicksPerQuarterNote ((int) ppqPerQuarter);

        juce::MidiMessageSequence copy (seq);
        copy.updateMatchedPairs();

        juce::MidiMessageSequence trackSeq;
        for (int i = 0; i < copy.getNumEvents(); ++i)
            trackSeq.addEvent (copy.getEventPointer (i)->message);

        mf.addTrack (trackSeq);

        juce::MemoryBlock block;
        juce::MemoryOutputStream mo (block, false);
        mf.writeTo (mo);
        return block;
    }

    bool smfToSequence (const void* data, size_t size, juce::MidiMessageSequence& outSeq)
    {
        juce::MemoryInputStream in (data, size, false);
        juce::MidiFile mf;

        if (! mf.readFrom (in))
            return false;

        mf.convertTimestampTicksToSeconds();

        outSeq.clear();

        if (mf.getNumTracks() > 0)
        {
            auto* track = mf.getTrack (0);
            if (track != nullptr)
            {
                for (int i = 0; i < track->getNumEvents(); ++i)
                    outSeq.addEvent (track->getEventPointer (i)->message);
                outSeq.updateMatchedPairs();
                return true;
            }
        }
        return false;
    }

    juce::String toBase64 (const juce::MemoryBlock& mb)
    {
        return mb.toBase64Encoding();
    }

    bool fromBase64 (const juce::String& b64, juce::MemoryBlock& out)
    {
        return out.fromBase64Encoding (b64);
    }
}
