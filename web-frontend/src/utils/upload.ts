export interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}

export interface ChunkedUploadOptions {
  onProgress?: (progress: UploadProgress) => void;
  onChunkProgress?: (chunkIndex: number, progress: UploadProgress) => void;
}

export class ChunkedUploader {
  private file: File;
  private options: ChunkedUploadOptions;

  constructor(file: File, options: ChunkedUploadOptions = {}) {
    this.file = file;
    this.options = options;
  }

  async upload(): Promise<string> {
    // Calculate SHA256 hash
    const sha256 = await this.calculateSHA256(this.file);
    
    // Initialize upload
    const initResponse = await fetch('/api/upload/init', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        filename: this.file.name,
        size_bytes: this.file.size,
        sha256,
        mime_type: this.file.type || 'application/octet-stream'
      })
    });

    if (!initResponse.ok) {
      throw new Error(`Upload init failed: ${initResponse.statusText}`);
    }

    const { upload_id, chunk_size, upload_urls } = await initResponse.json();

    // If no upload URLs, file already exists (deduplication)
    if (upload_urls.length === 0) {
      return upload_id;
    }

    // Upload chunks
    const parts = await this.uploadChunks(upload_urls, chunk_size);

    // Complete upload
    const completeResponse = await fetch('/api/upload/complete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        upload_id,
        parts
      })
    });

    if (!completeResponse.ok) {
      throw new Error(`Upload complete failed: ${completeResponse.statusText}`);
    }

    const { key } = await completeResponse.json();
    return key;
  }

  private async uploadChunks(urls: string[], chunkSize: number) {
    const parts = [];
    let uploadedBytes = 0;

    for (let i = 0; i < urls.length; i++) {
      const start = i * chunkSize;
      const end = Math.min(start + chunkSize, this.file.size);
      const chunk = this.file.slice(start, end);

      const response = await fetch(urls[i], {
        method: 'PUT',
        body: chunk,
        headers: {
          'Content-Type': 'application/octet-stream'
        }
      });

      if (!response.ok) {
        throw new Error(`Chunk ${i + 1} upload failed: ${response.statusText}`);
      }

      const etag = response.headers.get('ETag');
      parts.push({
        PartNumber: i + 1,
        ETag: etag
      });

      uploadedBytes += chunk.size;
      
      // Report progress
      this.options.onProgress?.({
        loaded: uploadedBytes,
        total: this.file.size,
        percentage: (uploadedBytes / this.file.size) * 100
      });

      this.options.onChunkProgress?.(i, {
        loaded: chunk.size,
        total: chunk.size,
        percentage: 100
      });
    }

    return parts;
  }

  private async calculateSHA256(file: File): Promise<string> {
    const buffer = await file.arrayBuffer();
    const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  }
}
