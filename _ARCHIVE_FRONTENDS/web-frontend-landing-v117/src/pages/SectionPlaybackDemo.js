/**
 * SectionPlaybackDemo.js
 * Demo page showing section-based playback with loop functionality
 * Complete integration example with upload, analysis, and playback
 */

import React, { useState } from 'react';
import SectionPlayer from '../components/SectionPlayer';
import api from '../services/api';

const SectionPlaybackDemo = () => {
  const [uploadedFile, setUploadedFile] = useState(null);
  const [fileKey, setFileKey] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [sections, setSections] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState(null);
  const [bpm, setBpm] = useState(120);
  const [autoDetectBpm, setAutoDetectBpm] = useState(true);
  const [currentSection, setCurrentSection] = useState(null);

  // Handle file selection
  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file) {
      setUploadedFile(file);
      setError(null);
      setSections([]);
      setAudioUrl(null);
      setFileKey(null);
    }
  };

  // Handle file upload
  const handleUpload = async () => {
    if (!uploadedFile) return;

    setIsUploading(true);
    setError(null);

    try {
      const response = await api.uploadFile(uploadedFile, 'professional');
      
      if (response.key) {
        setFileKey(response.key);
        const url = api.getAudioUrl(response.key);
        setAudioUrl(url);
        console.log('File uploaded successfully:', response.key);
      } else {
        throw new Error('Upload failed: no file key returned');
      }
    } catch (err) {
      console.error('Upload error:', err);
      setError(`Upload failed: ${err.message}`);
    } finally {
      setIsUploading(false);
    }
  };

  // Handle section analysis
  const handleAnalyze = async () => {
    if (!fileKey) return;

    setIsAnalyzing(true);
    setError(null);

    try {
      // Use enhanced sectionization with auto BPM detection
      const response = await api.getSectionsEnhanced(fileKey, {
        bpm: autoDetectBpm ? 0 : bpm,
        mode: 'smart',
        minBars: 4,
        maxBars: 16,
      });

      if (response.sections) {
        setSections(response.sections);
        console.log(`Found ${response.sections.length} sections:`, response.sections);

        if (response.bpm) {
          setBpm(Math.round(response.bpm));
          console.log('Detected BPM:', response.bpm);
        }
      } else {
        throw new Error('No sections returned from analysis');
      }
    } catch (err) {
      console.error('Analysis error:', err);
      setError(`Analysis failed: ${err.message}`);
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Handle section change callback
  const handleSectionChange = (section, index) => {
    setCurrentSection({ ...section, index });
    console.log('Now playing:', section.label || `Section ${index + 1}`);
  };

  // Load demo sections for testing
  const loadDemoSections = () => {
    const demoSections = [
      { start: 0, end: 8, label: 'intro', bars: 4, energy: 0.4 },
      { start: 8, end: 24, label: 'verse', bars: 8, energy: 0.6 },
      { start: 24, end: 40, label: 'chorus', bars: 8, energy: 0.9 },
      { start: 40, end: 56, label: 'verse', bars: 8, energy: 0.6 },
      { start: 56, end: 72, label: 'chorus', bars: 8, energy: 0.9 },
      { start: 72, end: 88, label: 'bridge', bars: 8, energy: 0.7 },
      { start: 88, end: 104, label: 'chorus', bars: 8, energy: 0.95 },
      { start: 104, end: 112, label: 'outro', bars: 4, energy: 0.5 },
    ];

    setSections(demoSections);
    setFileKey('demo-file');
    setAudioUrl('demo-audio.mp3'); // Replace with actual demo URL
    setError(null);
  };

  return (
    <div className="section-playback-demo min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold text-white mb-4">
            🎵 Section Playback System
          </h1>
          <p className="text-xl text-gray-300">
            Upload audio, analyze sections, and play them individually with loop support
          </p>
        </div>

        {/* Upload Section */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-2xl p-8 mb-8">
          <h2 className="text-2xl font-bold text-gray-800 dark:text-white mb-6">
            📤 Step 1: Upload Audio
          </h2>

          <div className="space-y-6">
            {/* File Input */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Select Audio File (WAV, MP3, FLAC, M4A)
              </label>
              <input
                type="file"
                accept="audio/*"
                onChange={handleFileSelect}
                className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
              />
            </div>

            {/* Upload Button */}
            {uploadedFile && !fileKey && (
              <button
                onClick={handleUpload}
                disabled={isUploading}
                className="w-full py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isUploading ? '⏳ Uploading...' : '📤 Upload File'}
              </button>
            )}

            {fileKey && (
              <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
                <p className="text-green-800 dark:text-green-300 font-semibold">
                  ✓ File uploaded successfully: {uploadedFile?.name}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Analysis Section */}
        {fileKey && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-2xl p-8 mb-8">
            <h2 className="text-2xl font-bold text-gray-800 dark:text-white mb-6">
              🔍 Step 2: Analyze Sections
            </h2>

            <div className="space-y-6">
              {/* BPM Settings */}
              <div className="flex items-center space-x-4">
                <label className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={autoDetectBpm}
                    onChange={(e) => setAutoDetectBpm(e.target.checked)}
                    className="w-4 h-4"
                  />
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    Auto-detect BPM
                  </span>
                </label>

                {!autoDetectBpm && (
                  <div className="flex items-center space-x-2">
                    <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      Manual BPM:
                    </label>
                    <input
                      type="number"
                      value={bpm}
                      onChange={(e) => setBpm(parseInt(e.target.value) || 120)}
                      min="60"
                      max="200"
                      className="w-20 px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    />
                  </div>
                )}

                {autoDetectBpm && bpm && bpm !== 120 && (
                  <span className="text-sm text-green-600 font-semibold">
                    Detected: {bpm} BPM
                  </span>
                )}
              </div>

              {/* Analyze Button */}
              {sections.length === 0 && (
                <button
                  onClick={handleAnalyze}
                  disabled={isAnalyzing}
                  className="w-full py-3 bg-purple-600 text-white rounded-lg font-semibold hover:bg-purple-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isAnalyzing ? '⏳ Analyzing...' : '🔍 Analyze Sections'}
                </button>
              )}

              {sections.length > 0 && (
                <div className="p-4 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg">
                  <p className="text-purple-800 dark:text-purple-300 font-semibold">
                    ✓ Found {sections.length} sections at {bpm} BPM
                  </p>
                </div>
              )}

              {/* Demo Button */}
              <button
                onClick={loadDemoSections}
                className="w-full py-2 bg-gray-600 text-white rounded-lg font-semibold hover:bg-gray-700 transition-all"
              >
                🎬 Load Demo Sections (Testing)
              </button>
            </div>
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-8">
            <p className="text-red-800 dark:text-red-300 font-semibold">❌ {error}</p>
          </div>
        )}

        {/* Section Player */}
        {sections.length > 0 && audioUrl && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-2xl p-8">
            <h2 className="text-2xl font-bold text-gray-800 dark:text-white mb-6">
              🎮 Step 3: Play Sections
            </h2>

            <SectionPlayer
              audioUrl={audioUrl}
              sections={sections}
              onSectionChange={handleSectionChange}
            />

            {/* Current Section Info */}
            {currentSection && (
              <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                <h3 className="text-lg font-bold text-blue-900 dark:text-blue-300 mb-2">
                  Now Playing
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <span className="text-gray-600 dark:text-gray-400">Section:</span>
                    <span className="ml-2 font-semibold text-gray-900 dark:text-white">
                      {currentSection.label || `Section ${currentSection.index + 1}`}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-600 dark:text-gray-400">Time:</span>
                    <span className="ml-2 font-semibold text-gray-900 dark:text-white">
                      {currentSection.start.toFixed(1)}s - {currentSection.end.toFixed(1)}s
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-600 dark:text-gray-400">Duration:</span>
                    <span className="ml-2 font-semibold text-gray-900 dark:text-white">
                      {(currentSection.end - currentSection.start).toFixed(1)}s
                    </span>
                  </div>
                  {currentSection.bars && (
                    <div>
                      <span className="text-gray-600 dark:text-gray-400">Bars:</span>
                      <span className="ml-2 font-semibold text-gray-900 dark:text-white">
                        {currentSection.bars}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Instructions */}
        <div className="mt-12 bg-gray-800 rounded-lg p-8 text-gray-300">
          <h3 className="text-2xl font-bold text-white mb-4">📖 How to Use</h3>
          <ol className="space-y-3 list-decimal list-inside">
            <li><strong>Upload Audio:</strong> Select a WAV, MP3, FLAC, or M4A file and click Upload</li>
            <li><strong>Analyze Sections:</strong> Click "Analyze Sections" to detect musical sections (intro, verse, chorus, etc.)</li>
            <li><strong>Play Sections:</strong> Click the play button (▶) on any section to start playback</li>
            <li><strong>Loop Mode:</strong> Toggle "Loop ON" to continuously repeat the current section</li>
            <li><strong>Pause/Resume:</strong> Click the pause button (⏸) to pause, click play again to resume</li>
            <li><strong>Switch Sections:</strong> Click play on a different section to switch immediately</li>
            <li><strong>Stop All:</strong> Click "Stop All" to stop playback completely</li>
          </ol>

          <div className="mt-6 p-4 bg-gray-700 rounded-lg">
            <h4 className="font-bold text-white mb-2">✨ Features:</h4>
            <ul className="space-y-1 list-disc list-inside">
              <li>Individual play/pause for each section</li>
              <li>Loop mode for practice and analysis</li>
              <li>Real-time progress bars</li>
              <li>Automatic section labeling (intro, verse, chorus, bridge, outro)</li>
              <li>Energy and timing metadata display</li>
              <li>Visual feedback for active sections</li>
              <li>Smooth transitions between sections</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SectionPlaybackDemo;
