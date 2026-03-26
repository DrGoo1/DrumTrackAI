// DrumTracKAI API Integration Layer
// Connects 3-tier frontend with backend services

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

class DrumTracKAIAPI {
  constructor() {
    this.baseURL = API_BASE_URL;
  }

  // Generic API request handler
  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        throw new Error(`API Error: ${response.status} ${response.statusText}`);
      }

      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        return await response.json();
      }
      
      return await response.text();
    } catch (error) {
      console.error(`API Request failed: ${endpoint}`, error);
      throw error;
    }
  }

  // System status and health check
  async getStatus() {
    return await this.request('/status');
  }

  // File upload with tier-specific limits
  async uploadFile(file, tier = 'basic') {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('tier', tier);

    return await this.request('/upload', {
      method: 'POST',
      headers: {}, // Let browser set Content-Type for FormData
      body: formData,
    });
  }

  // Start analysis with tier and type selection
  async startAnalysis(fileId, analysisType, tier) {
    return await this.request('/analyze', {
      method: 'POST',
      body: JSON.stringify({
        fileId,
        analysisType,
        tier,
        timestamp: new Date().toISOString(),
      }),
    });
  }

  // Get real-time analysis progress
  async getProgress(jobId) {
    return await this.request(`/progress/${jobId}`);
  }

  // Get analysis results
  async getResults(jobId) {
    return await this.request(`/results/${jobId}`);
  }

  // Get user usage statistics
  async getUserUsage() {
    return await this.request('/user/usage');
  }

  // Batch analysis for Professional/Expert tiers
  async startBatchAnalysis(fileIds, analysisType, tier) {
    return await this.request('/batch/analyze', {
      method: 'POST',
      body: JSON.stringify({
        fileIds,
        analysisType,
        tier,
        timestamp: new Date().toISOString(),
      }),
    });
  }

  // Get signature songs database
  async getSignatureSongs() {
    return await this.request('/signature-songs');
  }

  // Get classic beats database
  async getClassicBeats() {
    return await this.request('/classic-beats');
  }

  // MVSep stem separation (Expert tier only)
  async startMVSepProcessing(fileId) {
    return await this.request('/mvsep/process', {
      method: 'POST',
      body: JSON.stringify({
        fileId,
        models: ['HDemucs', 'DrumSep'],
        timestamp: new Date().toISOString(),
      }),
    });
  }

  // Get MVSep processing status
  async getMVSepStatus(jobId) {
    return await this.request(`/mvsep/status/${jobId}`);
  }

  // Real-time progress monitoring with WebSocket fallback
  subscribeToProgress(jobId, callback) {
    // Try WebSocket first, fallback to polling
    const wsUrl = this.baseURL.replace('http', 'ws') + `/progress/${jobId}/ws`;
    
    try {
      const ws = new WebSocket(wsUrl);
      
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        callback(data);
      };
      
      ws.onerror = () => {
        // Fallback to polling
        this.pollProgress(jobId, callback);
      };
      
      return () => ws.close();
    } catch (error) {
      // Fallback to polling
      return this.pollProgress(jobId, callback);
    }
  }

  // Polling fallback for progress monitoring
  pollProgress(jobId, callback) {
    const interval = setInterval(async () => {
      try {
        const progress = await this.getProgress(jobId);
        callback(progress);
        
        if (progress.status === 'completed' || progress.status === 'failed') {
          clearInterval(interval);
        }
      } catch (error) {
        console.error('Progress polling error:', error);
        clearInterval(interval);
      }
    }, 1000);

    return () => clearInterval(interval);
  }

  // Tier validation and limits
  validateUpload(file, tier) {
    const limits = {
      basic: {
        maxSize: 50 * 1024 * 1024, // 50MB
        formats: ['audio/wav', 'audio/mp3'],
        monthlyLimit: 10,
      },
      professional: {
        maxSize: 200 * 1024 * 1024, // 200MB
        formats: ['audio/wav', 'audio/mp3', 'audio/flac', 'audio/m4a'],
        monthlyLimit: -1, // Unlimited
      },
      expert: {
        maxSize: -1, // Unlimited
        formats: [], // All formats
        monthlyLimit: -1, // Unlimited
      },
    };

    const tierLimits = limits[tier];
    if (!tierLimits) {
      throw new Error(`Invalid tier: ${tier}`);
    }

    // Check file size
    if (tierLimits.maxSize > 0 && file.size > tierLimits.maxSize) {
      throw new Error(`File size exceeds ${tier} tier limit of ${tierLimits.maxSize / 1024 / 1024}MB`);
    }

    // Check file format
    if (tierLimits.formats.length > 0 && !tierLimits.formats.includes(file.type)) {
      throw new Error(`File format not supported in ${tier} tier`);
    }

    return true;
  }

  // Section-based playback API
  /**
   * Get audio file URL for playback
   * @param {string} fileKey - File key from upload
   */
  getAudioUrl(fileKey) {
    return `${this.baseURL}/files/audio?key=${encodeURIComponent(fileKey)}`;
  }

  /**
   * Get sections for an audio file (sectionization)
   * @param {string} fileKey - File key from upload
   * @param {Object} options - Sectionization options
   */
  async getSections(fileKey, options = {}) {
    const {
      bpm = 120,
      mode = 'smart',
      minBars = 4,
      maxBars = 16,
    } = options;

    const params = new URLSearchParams({
      key: fileKey,
      bpm: bpm.toString(),
      mode,
      min_bars: minBars.toString(),
      max_bars: maxBars.toString(),
    });

    return await this.request(`/dcsm/sectionize?${params.toString()}`);
  }

  /**
   * Get enhanced sections with intelligent labeling
   * @param {string} fileKey - File key from upload
   * @param {Object} options - Enhanced sectionization options
   */
  async getSectionsEnhanced(fileKey, options = {}) {
    const {
      bpm = 0, // 0 = auto-detect
      mode = 'smart',
      minBars = 4,
      maxBars = 16,
    } = options;

    const params = new URLSearchParams({
      key: fileKey,
      bpm: bpm.toString(),
      mode,
      min_bars: minBars.toString(),
      max_bars: maxBars.toString(),
    });

    return await this.request(`/dcsm/sectionize-enhanced?${params.toString()}`);
  }

  /**
   * Analyze full song and get SongMap with sections
   * @param {string} fileKey - File key from upload
   * @param {number} bpm - Optional BPM (0 for auto-detect)
   */
  async analyzeSong(fileKey, bpm = 0) {
    const params = new URLSearchParams({
      key: fileKey,
      bpm: bpm.toString(),
    });

    return await this.request(`/dcsm/analyze-full?${params.toString()}`);
  }

  // Demo data for development/testing
  getDemoData() {
    return {
      signatureSongs: [
        {
          id: 'porcaro_rosanna',
          name: 'Rosanna',
          artist: 'Toto',
          drummer: 'Jeff Porcaro',
          complexity: 'Expert',
          duration: '5:30',
          sophistication: '92.4%',
        },
        {
          id: 'peart_tom_sawyer',
          name: 'Tom Sawyer',
          artist: 'Rush',
          drummer: 'Neil Peart',
          complexity: 'Master',
          duration: '4:33',
          sophistication: '89.7%',
        },
        {
          id: 'copeland_roxanne',
          name: 'Roxanne',
          artist: 'The Police',
          drummer: 'Stewart Copeland',
          complexity: 'Professional',
          duration: '3:12',
          sophistication: '87.3%',
        },
      ],
      classicBeats: [
        {
          id: 'funky_drummer',
          name: 'Funky Drummer',
          artist: 'James Brown',
          bpm: '93',
          style: 'Funk',
          available: true,
        },
        {
          id: 'when_levee_breaks',
          name: 'When the Levee Breaks',
          artist: 'Led Zeppelin',
          bpm: '71',
          style: 'Rock',
          available: true,
        },
        {
          id: 'cissy_strut',
          name: 'Cissy Strut',
          artist: 'The Meters',
          bpm: '90',
          style: 'Funk',
          available: true,
        },
      ],
      analysisResults: {
        sophistication: '88.7%',
        accuracy: '94.2%',
        tempo: '120 BPM',
        timeSignature: '4/4',
        complexity: 'Expert Level',
        patterns: ['Linear Fill', 'Ghost Notes', 'Hi-hat Work', 'Cross-stick'],
        confidence: '96.8%',
        drummerStyle: 'Jeff Porcaro Style',
        fills: 12,
        processingTime: '2m 15s',
      },
    };
  }
}

// Export singleton instance
const api = new DrumTracKAIAPI();
export default api;

// Export class for testing
export { DrumTracKAIAPI };
