/**
 * Internet Song Lookup Modal
 * For famous songs - search and auto-populate tempo, time sig, and arrangement
 */
import React, { useState } from 'react';

export interface SongInfo {
  title: string;
  artist: string;
  tempo: number;
  timeSignature: [number, number];
  key?: string;
  sections?: Array<{
    label: string;
    startTime: number;
    endTime: number;
  }>;
  source: string; // 'musicbrainz', 'spotify', 'songsterr', etc.
}

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (songInfo: SongInfo) => void;
}

export const InternetSongLookupModal: React.FC<Props> = ({
  isOpen,
  onClose,
  onSelect
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [searching, setSearching] = useState(false);
  const [results, setResults] = useState<SongInfo[]>([]);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    setSearching(true);
    setError(null);
    
    try {
      // Call backend to search multiple sources
      const response = await fetch(`/api/song-lookup?q=${encodeURIComponent(searchQuery)}`);
      
      if (!response.ok) {
        throw new Error('Search failed');
      }

      const data = await response.json();
      setResults(data.results || []);
      
      if (data.results.length === 0) {
        setError('No results found. Try different search terms.');
      }
    } catch (err) {
      setError('Failed to search. Check your connection.');
      console.error('Song lookup error:', err);
    } finally {
      setSearching(false);
    }
  };

  const handleSelect = (song: SongInfo) => {
    onSelect(song);
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-slate-800 rounded-lg shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-slate-700 bg-gradient-to-r from-blue-900/40 to-cyan-900/40">
          <h2 className="text-xl font-bold text-white">🌐 Internet Song Lookup</h2>
          <p className="text-sm text-slate-300 mt-1">Search for famous songs to auto-populate arrangement data</p>
        </div>

        {/* Search Bar */}
        <div className="p-4 border-b border-slate-700 bg-slate-900">
          <div className="flex gap-2">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              placeholder='Search: "Torn Natalie Imbruglia" or "Bohemian Rhapsody Queen"'
              className="flex-1 px-4 py-2 bg-slate-800 text-white rounded border border-slate-600 focus:border-blue-500 focus:outline-none"
            />
            <button
              onClick={handleSearch}
              disabled={searching || !searchQuery.trim()}
              className="px-6 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:cursor-not-allowed text-white font-semibold rounded transition-colors"
            >
              {searching ? '🔍 Searching...' : '🔍 Search'}
            </button>
          </div>

          {error && (
            <div className="mt-2 text-sm text-red-400">
              ⚠️ {error}
            </div>
          )}

          <div className="mt-2 text-xs text-slate-400">
            <strong>Sources:</strong> MusicBrainz, Spotify, Songsterr, Ultimate Guitar, TheSessionData
          </div>
        </div>

        {/* Results */}
        <div className="flex-1 overflow-y-auto p-4">
          {searching && (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
                <p className="text-slate-400">Searching music databases...</p>
              </div>
            </div>
          )}

          {!searching && results.length === 0 && !error && (
            <div className="text-center py-12 text-slate-400">
              <div className="text-4xl mb-4">🎵</div>
              <p>Enter a song name and artist to search</p>
              <p className="text-sm mt-2">Example: "Torn Natalie Imbruglia"</p>
            </div>
          )}

          {results.length > 0 && (
            <div className="space-y-3">
              {results.map((song, idx) => (
                <div
                  key={idx}
                  className="p-4 bg-slate-900 rounded border border-slate-700 hover:border-blue-500 transition-colors cursor-pointer"
                  onClick={() => handleSelect(song)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-white">{song.title}</h3>
                      <p className="text-sm text-slate-400">{song.artist}</p>

                      <div className="mt-3 grid grid-cols-2 gap-4">
                        <div>
                          <span className="text-xs text-slate-500">Tempo:</span>
                          <span className="ml-2 text-sm text-white font-semibold">{song.tempo} BPM</span>
                        </div>
                        <div>
                          <span className="text-xs text-slate-500">Time Signature:</span>
                          <span className="ml-2 text-sm text-white font-semibold">
                            {song.timeSignature[0]}/{song.timeSignature[1]}
                          </span>
                        </div>
                        {song.key && (
                          <div>
                            <span className="text-xs text-slate-500">Key:</span>
                            <span className="ml-2 text-sm text-white font-semibold">{song.key}</span>
                          </div>
                        )}
                        {song.sections && (
                          <div>
                            <span className="text-xs text-slate-500">Sections:</span>
                            <span className="ml-2 text-sm text-white font-semibold">
                              {song.sections.length} detected
                            </span>
                          </div>
                        )}
                      </div>

                      {song.sections && song.sections.length > 0 && (
                        <div className="mt-3">
                          <span className="text-xs text-slate-500">Structure:</span>
                          <div className="mt-1 flex flex-wrap gap-1">
                            {song.sections.map((sec, i) => (
                              <span
                                key={i}
                                className="px-2 py-0.5 bg-blue-900/40 text-blue-300 text-xs rounded"
                              >
                                {sec.label}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      <div className="mt-2 text-xs text-slate-500">
                        Source: {song.source}
                      </div>
                    </div>

                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleSelect(song);
                      }}
                      className="ml-4 px-3 py-1 bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold rounded shadow-lg transition-colors"
                      title="Apply this song's tempo and arrangement"
                    >
                      ✅ Use This
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-700 bg-slate-900 flex justify-between items-center">
          <div className="text-xs text-slate-500">
            💡 Tip: Include both song title and artist for best results
          </div>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
