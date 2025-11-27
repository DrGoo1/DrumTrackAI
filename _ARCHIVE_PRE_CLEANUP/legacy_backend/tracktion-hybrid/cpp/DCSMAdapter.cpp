#include "DCSMAdapter.h"
using namespace juce;
namespace tc = tracktion::core;

DCSMAdapter::DCSMAdapter(const String& appName)
: engine(appName), edit(te::Edit::createSingleTrackEdit(engine, te::Edit::forEditing))
{
  edit->ensureNumberOfAudioTracks(1);
  edit->ensureTempoTrack();
  edit->ensureArrangerTrack();
  edit->ensureMarkerTrack();
}

te::AudioTrack* DCSMAdapter::importAudioFile(const File& f, double atSeconds)
{
  edit->ensureNumberOfAudioTracks( (int) te::getAudioTracks(*edit).size() + 1 );
  auto tracks = te::getAudioTracks(*edit);
  auto* track = tracks.isEmpty() ? nullptr : tracks.getLast();
  jassert(track != nullptr);
  auto start = tc::TimePosition::fromSeconds(atSeconds);
  auto end   = tc::TimePosition::fromSeconds(atSeconds); // zero-length placeholder
  auto range = tc::TimeRange(start, end);
  auto clipPos = te::createClipPosition(edit->tempoSequence, range);
  auto clipPtr = track->insertWaveClip(f.getFileNameWithoutExtension(), f, clipPos, false);
  jassert(clipPtr != nullptr); return track;
}

te::MidiClip* DCSMAdapter::ensureDrumMidiClip(int trackIndex, double lenSec)
{
  edit->ensureNumberOfAudioTracks(trackIndex + 1);
  auto* track = te::getAudioTracks(*edit)[trackIndex];
  if (track->getClips().isEmpty())
  {
    auto start = tc::TimePosition::fromSeconds(0.0);
    auto end   = tc::TimePosition::fromSeconds(lenSec);
    track->insertNewClip(te::TrackItem::Type::midi, tc::TimeRange(start, end), nullptr);
  }
  return dynamic_cast<te::MidiClip*>(track->getClips()[0]);
}

void DCSMAdapter::addMidiNote(te::MidiClip& clip, int note, double start, double len, int vel)
{
  // Convert seconds to beat domain approximately; for now treat seconds as beats to satisfy API
  auto bp = tc::BeatPosition::fromBeats(start);
  auto bd = tc::BeatDuration::fromBeats(len);
  clip.getSequence().addNote(note, bp, bd, juce::jlimit(1,127,vel), 0, nullptr);
}

void DCSMAdapter::setConstantTempo(double bpm)
{
  auto& ts = edit->tempoSequence; if (ts.getNumTempos() == 0) edit->ensureTempoTrack();
  ts.getTempos()[0]->setBpm(bpm); edit->sendTempoOrPitchSequenceChangedUpdates();
}

void DCSMAdapter::ensureArranger() { edit->ensureArrangerTrack(); }

void DCSMAdapter::addSection(double s, double e, const String& label)
{
  // TODO: Tracktion marker API changed; implement using new Marker helpers if needed.
}

void DCSMAdapter::play(double fromSec){ auto& t = edit->getTransport(); t.stop(false,false); t.position = tc::TimePosition::fromSeconds(fromSec); t.play(true);} 
void DCSMAdapter::stop(){ auto& t = edit->getTransport(); t.stop(false,false); t.position = tc::TimePosition::fromSeconds(0.0); }
