import React, { useState, useCallback } from 'react';
import { ChunkedUploader, UploadProgress } from '../utils/upload';

interface UploadComponentProps {
  onUploadComplete?: (key: string) => void;
  onUploadError?: (error: string) => void;
  accept?: string;
  maxSize?: number;
}

export function UploadComponent({ 
  onUploadComplete, 
  onUploadError, 
  accept = "audio/*",
  maxSize = 100 * 1024 * 1024 // 100MB default
}: UploadComponentProps) {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState<UploadProgress | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const handleFileUpload = useCallback(async (file: File) => {
    if (file.size > maxSize) {
      onUploadError?.(`File too large. Maximum size: ${Math.round(maxSize / 1024 / 1024)}MB`);
      return;
    }

    setUploading(true);
    setProgress({ loaded: 0, total: file.size, percentage: 0 });

    try {
      const uploader = new ChunkedUploader(file, {
        onProgress: setProgress
      });
      
      const key = await uploader.upload();
      onUploadComplete?.(key);
    } catch (error) {
      onUploadError?.(error instanceof Error ? error.message : 'Upload failed');
    } finally {
      setUploading(false);
      setProgress(null);
    }
  }, [maxSize, onUploadComplete, onUploadError]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFileUpload(files[0]);
    }
  }, [handleFileUpload]);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileUpload(files[0]);
    }
  }, [handleFileUpload]);

  return (
    <div 
      className={`upload-zone ${dragOver ? 'drag-over' : ''} ${uploading ? 'uploading' : ''}`}
      onDrop={handleDrop}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      style={{
        border: '2px dashed #ccc',
        borderRadius: '8px',
        padding: '40px',
        textAlign: 'center',
        backgroundColor: dragOver ? '#f0f8ff' : '#fafafa',
        cursor: uploading ? 'not-allowed' : 'pointer',
        transition: 'all 0.3s ease'
      }}
    >
      {uploading ? (
        <div>
          <div>Uploading...</div>
          {progress && (
            <div style={{ marginTop: '10px' }}>
              <div style={{ 
                width: '100%', 
                height: '8px', 
                backgroundColor: '#e0e0e0', 
                borderRadius: '4px',
                overflow: 'hidden'
              }}>
                <div 
                  style={{ 
                    width: `${progress.percentage}%`, 
                    height: '100%', 
                    backgroundColor: '#4caf50',
                    transition: 'width 0.3s ease'
                  }} 
                />
              </div>
              <div style={{ marginTop: '5px', fontSize: '12px', color: '#666' }}>
                {Math.round(progress.percentage)}% - {Math.round(progress.loaded / 1024 / 1024)}MB / {Math.round(progress.total / 1024 / 1024)}MB
              </div>
            </div>
          )}
        </div>
      ) : (
        <div>
          <div style={{ fontSize: '18px', marginBottom: '10px' }}>
            Drop audio file here or click to browse
          </div>
          <input
            type="file"
            accept={accept}
            onChange={handleFileSelect}
            style={{ display: 'none' }}
            id="file-input"
            disabled={uploading}
          />
          <label 
            htmlFor="file-input" 
            style={{ 
              display: 'inline-block',
              padding: '10px 20px',
              backgroundColor: '#2196f3',
              color: 'white',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Choose File
          </label>
          <div style={{ marginTop: '10px', fontSize: '12px', color: '#666' }}>
            Maximum file size: {Math.round(maxSize / 1024 / 1024)}MB
          </div>
        </div>
      )}
    </div>
  );
}
