/**
 * SectionPlayer.js
 * React component for playing individual sections with play/pause/loop controls
 * Features:
 * - Individual play button for each section
 * - Loop toggle
 * - Progress bar
 * - Visual feedback for active section
 * - Automatic section labeling (intro, verse, chorus, etc.)
 */

import React, { useState, useEffect, useRef } from 'react';
import AudioEngine from '../utils/AudioEngine';

const SectionPlayer = ({ audioUrl, sections, onSectionChange }) => {
  const [audioEngine] = useState(() => new AudioEngine());
  const [currentSectionIndex, setCurrentSectionIndex] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLooping, setIsLooping] = useState(false);
  const [progress, setProgress] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [audioLoaded, setAudioLoaded] = useState(false);

  // Load audio when URL changes
  useEffect(() => {
    if (audioUrl) {
      setIsLoading(true);
      audioEngine
        .loadAudio(audioUrl)
        .then(() => {
          setAudioLoaded(true);
          setIsLoading(false);
        })
        .catch((error) => {
          console.error('Failed to load audio:', error);
          setIsLoading(false);
        });
    }

    return () => {
      audioEngine.dispose();
    };
  }, [audioUrl, audioEngine]);

  // Setup playback callbacks
  useEffect(() => {
    audioEngine.onTimeUpdate = ({ progress }) => {
      setProgress(progress);
    };

    audioEngine.onPlaybackEnd = () => {
      setIsPlaying(false);
      setProgress(0);
      if (!audioEngine.isLooping) {
        setCurrentSectionIndex(null);
      }
    };
  }, [audioEngine]);

  // Handle play/pause for a section
  const handlePlaySection = async (index) => {
    const section = sections[index];

    if (currentSectionIndex === index && isPlaying) {
      // Pause current section
      audioEngine.pause();
      setIsPlaying(false);
    } else if (currentSectionIndex === index && !isPlaying) {
      // Resume current section
      await audioEngine.resume();
      setIsPlaying(true);
    } else {
      // Play new section
      setCurrentSectionIndex(index);
      setProgress(0);
      await audioEngine.playSection(section, isLooping);
      setIsPlaying(true);

      if (onSectionChange) {
        onSectionChange(section, index);
      }
    }
  };

  // Toggle loop mode
  const handleToggleLoop = () => {
    const newLooping = audioEngine.toggleLoop();
    setIsLooping(newLooping);
  };

  // Stop playback
  const handleStop = () => {
    audioEngine.stop();
    setIsPlaying(false);
    setCurrentSectionIndex(null);
    setProgress(0);
  };

  // Format time in MM:SS
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Get section label with fallback
  const getSectionLabel = (section, index) => {
    return section.label || `Section ${index + 1}`;
  };

  // Get section color based on label
  const getSectionColor = (label) => {
    const colors = {
      intro: 'bg-blue-500',
      verse: 'bg-green-500',
      chorus: 'bg-purple-500',
      bridge: 'bg-yellow-500',
      outro: 'bg-red-500',
      solo: 'bg-orange-500',
    };

    const normalizedLabel = label?.toLowerCase() || '';
    return colors[normalizedLabel] || 'bg-gray-500';
  };

  if (!sections || sections.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No sections available. Upload and analyze audio first.
      </div>
    );
  }

  return (
    <div className="section-player w-full">
      {/* Header Controls */}
      <div className="flex items-center justify-between mb-6 p-4 bg-gray-800 rounded-lg">
        <div className="flex items-center space-x-4">
          <h3 className="text-xl font-bold text-white">Section Playback</h3>
          {isLoading && <span className="text-sm text-gray-400">Loading audio...</span>}
          {audioLoaded && <span className="text-sm text-green-400">✓ Audio ready</span>}
        </div>

        <div className="flex items-center space-x-4">
          {/* Loop Toggle */}
          <button
            onClick={handleToggleLoop}
            disabled={!audioLoaded}
            className={`px-4 py-2 rounded-lg font-semibold transition-all ${
              isLooping
                ? 'bg-purple-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            } ${!audioLoaded ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            {isLooping ? '🔁 Loop ON' : '↻ Loop OFF'}
          </button>

          {/* Stop Button */}
          {isPlaying && (
            <button
              onClick={handleStop}
              className="px-4 py-2 bg-red-600 text-white rounded-lg font-semibold hover:bg-red-700 transition-all"
            >
              ⬛ Stop All
            </button>
          )}
        </div>
      </div>

      {/* Sections List */}
      <div className="space-y-3">
        {sections.map((section, index) => {
          const isActive = currentSectionIndex === index;
          const duration = section.end - section.start;
          const label = getSectionLabel(section, index);
          const colorClass = getSectionColor(label);

          return (
            <div
              key={index}
              className={`section-item p-4 rounded-lg border-2 transition-all ${
                isActive
                  ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                  : 'border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800'
              }`}
            >
              <div className="flex items-center justify-between">
                {/* Section Info */}
                <div className="flex items-center space-x-4 flex-1">
                  {/* Play/Pause Button */}
                  <button
                    onClick={() => handlePlaySection(index)}
                    disabled={!audioLoaded}
                    className={`w-12 h-12 rounded-full flex items-center justify-center transition-all ${
                      isActive && isPlaying
                        ? 'bg-blue-600 text-white hover:bg-blue-700'
                        : 'bg-green-600 text-white hover:bg-green-700'
                    } ${!audioLoaded ? 'opacity-50 cursor-not-allowed' : ''}`}
                  >
                    {isActive && isPlaying ? (
                      <span className="text-2xl">⏸</span>
                    ) : (
                      <span className="text-2xl">▶</span>
                    )}
                  </button>

                  {/* Section Details */}
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-1">
                      <span className={`px-3 py-1 rounded-full text-xs font-bold text-white ${colorClass}`}>
                        {label.toUpperCase()}
                      </span>
                      <span className="text-sm text-gray-600 dark:text-gray-400">
                        Section {index + 1} of {sections.length}
                      </span>
                    </div>

                    <div className="flex items-center space-x-4 text-sm text-gray-600 dark:text-gray-400">
                      <span>
                        ⏱ {formatTime(section.start)} - {formatTime(section.end)}
                      </span>
                      <span>📏 {formatTime(duration)}</span>
                      {section.bars && <span>🎵 {section.bars} bars</span>}
                      {section.energy && (
                        <span>⚡ Energy: {(section.energy * 100).toFixed(0)}%</span>
                      )}
                    </div>

                    {/* Progress Bar */}
                    {isActive && (
                      <div className="mt-2">
                        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                          <div
                            className="bg-blue-600 h-2 rounded-full transition-all"
                            style={{ width: `${progress * 100}%` }}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Status Indicator */}
                {isActive && (
                  <div className="ml-4">
                    {isPlaying ? (
                      <div className="flex items-center space-x-2 text-green-600">
                        <div className="w-3 h-3 bg-green-600 rounded-full animate-pulse" />
                        <span className="text-sm font-semibold">Playing</span>
                      </div>
                    ) : (
                      <span className="text-sm text-gray-500">Paused</span>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Global Progress Indicator */}
      {currentSectionIndex !== null && (
        <div className="mt-6 p-4 bg-gray-100 dark:bg-gray-800 rounded-lg">
          <div className="flex items-center justify-between text-sm mb-2">
            <span className="font-semibold text-gray-700 dark:text-gray-300">
              {getSectionLabel(sections[currentSectionIndex], currentSectionIndex)}
            </span>
            <span className="text-gray-500">
              {formatTime(sections[currentSectionIndex].start + progress * (sections[currentSectionIndex].end - sections[currentSectionIndex].start))} / {formatTime(sections[currentSectionIndex].end)}
            </span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="flex-1 bg-gray-300 dark:bg-gray-700 rounded-full h-3">
              <div
                className="bg-gradient-to-r from-blue-500 to-purple-500 h-3 rounded-full transition-all"
                style={{ width: `${progress * 100}%` }}
              />
            </div>
            {isLooping && (
              <span className="text-xs text-purple-600 font-semibold">🔁 LOOP</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default SectionPlayer;
