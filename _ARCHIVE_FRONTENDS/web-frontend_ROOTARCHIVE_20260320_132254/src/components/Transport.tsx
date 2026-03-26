import React from 'react';

interface TransportControlsProps {
  isPlaying: boolean;
  onPlay: () => void;
  onStop: () => void;
  onSeek: (position: number) => void;
  position: number;
  duration: number;
}

export const TransportControls: React.FC<TransportControlsProps> = ({
  isPlaying,
  onPlay,
  onStop,
  onSeek,
  position,
  duration
}) => {
  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleSeekChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const newPosition = parseFloat(event.target.value);
    onSeek(newPosition);
  };

  return (
    <div className="h-full flex items-center px-4 space-x-4">
      {/* Transport Buttons */}
      <div className="flex items-center space-x-2">
        <button
          onClick={onStop}
          className="w-8 h-8 bg-gray-700 hover:bg-gray-600 rounded flex items-center justify-center"
          title="Stop"
        >
          <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 24 24">
            <rect x="6" y="6" width="12" height="12" />
          </svg>
        </button>

        <button
          onClick={onPlay}
          className="w-8 h-8 bg-blue-600 hover:bg-blue-700 rounded flex items-center justify-center"
          title={isPlaying ? "Pause" : "Play"}
        >
          {isPlaying ? (
            <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 24 24">
              <rect x="6" y="4" width="4" height="16" />
              <rect x="14" y="4" width="4" height="16" />
            </svg>
          ) : (
            <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 24 24">
              <polygon points="5,3 19,12 5,21" />
            </svg>
          )}
        </button>

        <button
          onClick={() => onSeek(0)}
          className="w-8 h-8 bg-gray-700 hover:bg-gray-600 rounded flex items-center justify-center"
          title="Return to Start"
        >
          <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 24 24">
            <polygon points="11,5 6,9 6,15 11,19 11,13 16,17 16,7 11,11" />
          </svg>
        </button>
      </div>

      {/* Time Display */}
      <div className="flex items-center space-x-2 text-sm font-mono">
        <span className="text-white min-w-[3rem]">
          {formatTime(position)}
        </span>
        <span className="text-gray-400">/</span>
        <span className="text-gray-400 min-w-[3rem]">
          {formatTime(duration)}
        </span>
      </div>

      {/* Seek Bar */}
      <div className="flex-1 max-w-md">
        <input
          type="range"
          min="0"
          max={duration || 1}
          step="0.1"
          value={position}
          onChange={handleSeekChange}
          className="w-full h-2 bg-gray-600 rounded-lg appearance-none cursor-pointer slider"
        />
      </div>

      {/* Tempo Display */}
      <div className="flex items-center space-x-2 text-sm">
        <span className="text-gray-400">BPM:</span>
        <span className="text-white font-mono">120</span>
      </div>

      {/* Loop Controls */}
      <div className="flex items-center space-x-2">
        <button
          className="w-8 h-8 bg-gray-700 hover:bg-gray-600 rounded flex items-center justify-center"
          title="Loop"
        >
          <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>

        <button
          className="w-8 h-8 bg-gray-700 hover:bg-gray-600 rounded flex items-center justify-center"
          title="Metronome"
        >
          <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </button>
      </div>
    </div>
  );
};
