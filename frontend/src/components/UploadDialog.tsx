import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';

interface UploadDialogProps {
  onUpload: (file: File) => void;
  onClose: () => void;
  isLoading?: boolean;
  error?: string | null;
  userId?: string;
}

export const UploadDialog: React.FC<UploadDialogProps> = ({
  onUpload,
  onClose,
  isLoading,
  error,
  userId
}) => {
  const [dragActive, setDragActive] = useState(false);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      onUpload(acceptedFiles[0]);
    }
  }, [onUpload]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'audio/*': ['.mp3', '.wav', '.flac', '.m4a', '.ogg']
    },
    multiple: false,
    disabled: isLoading
  });

  return (
    <div className="max-w-2xl mx-auto p-8">
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold text-blue-400 mb-2">
          DrumTracKAI v1.1.11 - Enhanced DCSM
        </h1>
        <p className="text-gray-400 text-lg">
          Enhanced Drum Composer and Song Map with Advanced Features
        </p>
      </div>

      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-all
          ${isDragActive || dragActive 
            ? 'border-blue-500 bg-blue-500/10' 
            : 'border-gray-600 hover:border-gray-500'
          }
          ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <input {...getInputProps()} />
        
        <div className="mb-6">
          <svg
            className="w-16 h-16 mx-auto text-gray-400 mb-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"
            />
          </svg>
        </div>

        {isLoading ? (
          <div>
            <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-4"></div>
            <p className="text-lg font-medium">Processing your audio...</p>
            <p className="text-sm text-gray-400 mt-2">
              Analyzing structure • Composing drums • Rendering MIDI
            </p>
          </div>
        ) : (
          <div>
            <p className="text-lg font-medium mb-2">
              Drop your audio file here, or click to browse
            </p>
            <p className="text-sm text-gray-400 mb-4">
              Supports MP3, WAV, FLAC, M4A, OGG
            </p>
            <div className="text-xs text-gray-500">
              {userId ? (
                <div>
                  <p>Logged in as: {userId}</p>
                  <p>Professional tier: 100 uploads/month • 200MB max</p>
                </div>
              ) : (
                <p>Anonymous: Basic tier • 10 uploads/month • 50MB max</p>
              )}
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="mt-6 p-4 bg-red-900/50 border border-red-700 rounded-lg">
          <div className="flex items-center">
            <svg
              className="w-5 h-5 text-red-400 mr-2"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                clipRule="evenodd"
              />
            </svg>
            <span className="text-red-200">{error}</span>
          </div>
        </div>
      )}

      <div className="mt-8 grid grid-cols-3 gap-4 text-center text-sm">
        <div className="p-4 bg-gray-800 rounded-lg">
          <div className="text-blue-400 font-bold text-lg">SMAP</div>
          <div className="text-gray-400">Song structure analysis</div>
        </div>
        <div className="p-4 bg-gray-800 rounded-lg">
          <div className="text-purple-400 font-bold text-lg">DGRAPH</div>
          <div className="text-gray-400">Drum pattern composition</div>
        </div>
        <div className="p-4 bg-gray-800 rounded-lg">
          <div className="text-green-400 font-bold text-lg">1/64th</div>
          <div className="text-gray-400">High-resolution editing</div>
        </div>
      </div>
    </div>
  );
};
