/**
 * Audio Upload Component - Phase 3 Slice A
 * Handles file upload and triggers waveform generation
 */

import React, { useCallback, useState } from 'react';
// @ts-ignore  -- JS file importing a TS module; shim ensures types
import * as Phase3 from '../api/phase3';
import { fetchWaveform } from '../api/files';

interface AudioUploadProps {
  onWaveformLoaded: (waveformData: { key: string; sr: number; peaks: number[]; filename: string }) => void;
  onError: (error: string) => void;
}

export const AudioUpload: React.FC<AudioUploadProps> = ({ onWaveformLoaded, onError }) => {
  const [isUploading, setIsUploading] = useState(false);

  const handleFileSelect = useCallback(async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('audio/')) {
      onError('Please select an audio file');
      return;
    }

    setIsUploading(true);
    
    try {
      // Upload file and get S3 key
      const key = await Phase3.uploadFileSmart(file);
      
      // Generate waveform peaks
      const peaks = await fetchWaveform(key);
      
      // Notify parent component
      onWaveformLoaded({
        key,
        sr: 44100, // Default sample rate
        peaks: peaks,
        filename: file.name
      });
      
    } catch (error) {
      console.error('Upload failed:', error);
      onError(`Upload failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsUploading(false);
    }
  }, [onWaveformLoaded, onError]);

  return (
    <div className="audio-upload">
      <label className="upload-button">
        <input
          type="file"
          accept="audio/*"
          onChange={handleFileSelect}
          disabled={isUploading}
          style={{ display: 'none' }}
        />
        <span className="upload-text">
          {isUploading ? 'Uploading & Processing...' : 'Import Audio File'}
        </span>
      </label>
      
      <style>{`
        .audio-upload {
          margin: 10px 0;
        }
        
        .upload-button {
          display: inline-block;
          padding: 12px 24px;
          background: #4CAF50;
          color: white;
          border-radius: 6px;
          cursor: pointer;
          font-weight: 500;
          transition: background-color 0.2s;
        }
        
        .upload-button:hover {
          background: #45a049;
        }
        
        .upload-button:disabled {
          background: #cccccc;
          cursor: not-allowed;
        }
        
        .upload-text {
          display: block;
        }
      `}</style>
    </div>
  );
};
