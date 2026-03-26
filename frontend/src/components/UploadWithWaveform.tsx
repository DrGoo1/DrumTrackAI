/**
 * Upload Component with Waveform Display
 * Shows upload button, waveform, and analysis results
 */
import React, { useState } from 'react';
import { SimpleWaveform } from './SimpleWaveform';

interface AnalysisResult {
  tempo: string;
  bpm_value: number;
  sophistication: string;
  accuracy: string;
  patterns: string[];
}

export const UploadWithWaveform: React.FC = () => {
  const [isUploading, setIsUploading] = useState(false);
  const [waveformData, setWaveformData] = useState<{ peaks: number[]; key: string } | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string>('');

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('audio/')) {
      setError('Please select an audio file');
      return;
    }

    setIsUploading(true);
    setError('');
    setWaveformData(null);
    setAnalysis(null);

    try {
      // Step 1: Upload file
      const formData = new FormData();
      formData.append('file', file);

      const uploadResponse = await fetch('/api/upload', {
        method: 'POST',
        body: formData
      });

      if (!uploadResponse.ok) {
        throw new Error(`Upload failed: ${uploadResponse.statusText}`);
      }

      const uploadResult = await uploadResponse.json();
      
      console.log('Upload result:', uploadResult);

      // Extract waveform data
      if (uploadResult.waveform && uploadResult.waveform.peaks) {
        setWaveformData({
          peaks: uploadResult.waveform.peaks,
          key: uploadResult.key || uploadResult.file_id
        });
      }

      // Step 2: Get analysis results if available
      if (uploadResult.file_id || uploadResult.key) {
        const jobId = (uploadResult.file_id || uploadResult.key).replace(/\//g, '_').replace(/\\/g, '_');
        
        try {
          const resultsResponse = await fetch(`/api/results/${jobId}`);
          if (resultsResponse.ok) {
            const resultsData = await resultsResponse.json();
            console.log('Analysis results:', resultsData);
            setAnalysis(resultsData);
          }
        } catch (e) {
          console.warn('Analysis not available yet:', e);
        }
      }

    } catch (err) {
      console.error('Upload failed:', err);
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="bg-gray-800 rounded-lg p-6 shadow-xl">
        <h2 className="text-2xl font-bold text-white mb-4">DrumTracKAI - Audio Upload</h2>
        
        {/* Upload Button */}
        <label className="inline-block px-6 py-3 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg cursor-pointer transition-colors disabled:bg-gray-600 disabled:cursor-not-allowed">
          <input
            type="file"
            accept="audio/*"
            onChange={handleFileSelect}
            disabled={isUploading}
            className="hidden"
          />
          <span>{isUploading ? 'Uploading & Processing...' : 'Load Audio File'}</span>
        </label>

        {/* Error Message */}
        {error && (
          <div className="mt-4 p-3 bg-red-900 text-red-200 rounded">
            {error}
          </div>
        )}

        {/* Waveform Display */}
        {waveformData && waveformData.peaks && waveformData.peaks.length > 0 && (
          <div className="mt-6">
            <h3 className="text-lg font-semibold text-white mb-2">Waveform</h3>
            <SimpleWaveform 
              peaks={waveformData.peaks}
              width={800}
              height={120}
              color="#10B981"
              backgroundColor="#1F2937"
              className="shadow-lg"
            />
            <p className="text-sm text-gray-400 mt-2">
              File: {waveformData.key}
            </p>
          </div>
        )}

        {/* Analysis Results */}
        {analysis && (
          <div className="mt-6 bg-gray-700 rounded-lg p-4">
            <h3 className="text-lg font-semibold text-white mb-3">Analysis Results</h3>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-400">Tempo:</span>
                <span className="text-white font-bold ml-2">{analysis.tempo}</span>
              </div>
              <div>
                <span className="text-gray-400">Sophistication:</span>
                <span className="text-white ml-2">{analysis.sophistication}</span>
              </div>
              <div>
                <span className="text-gray-400">Accuracy:</span>
                <span className="text-white ml-2">{analysis.accuracy}</span>
              </div>
              <div>
                <span className="text-gray-400">Confidence:</span>
                <span className="text-white ml-2">High</span>
              </div>
            </div>
            {analysis.patterns && analysis.patterns.length > 0 && (
              <div className="mt-3">
                <span className="text-gray-400 text-sm">Detected Patterns:</span>
                <div className="flex flex-wrap gap-2 mt-1">
                  {analysis.patterns.map((pattern, idx) => (
                    <span key={idx} className="px-2 py-1 bg-green-900 text-green-200 rounded text-xs">
                      {pattern}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Instructions */}
        {!waveformData && !isUploading && (
          <div className="mt-6 text-gray-400 text-sm">
            <p>📁 Supported formats: MP3, WAV, FLAC, AAC</p>
            <p>📊 Maximum file size: 500MB</p>
            <p>⚡ Fast waveform generation with Rust</p>
            <p>🎵 Real-time tempo detection: {analysis?.bpm_value ? `${analysis.bpm_value} BPM` : 'Ready'}</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default UploadWithWaveform;
