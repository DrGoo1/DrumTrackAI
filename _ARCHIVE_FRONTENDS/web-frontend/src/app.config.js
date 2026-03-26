// DrumTracKAI Application Configuration
const APP_CONFIG = {
  // API Configuration
  API_BASE_URL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
  
  // Authentication
  JWT_STORAGE_KEY: 'drumtrackai_token',
  
  // File Upload Limits (in MB)
  UPLOAD_LIMITS: {
    basic: 50,
    advanced: 200,
    professional: 500
  },
  
  // Supported File Formats
  SUPPORTED_FORMATS: {
    audio: ['.mp3', '.wav', '.flac', '.aac', '.m4a'],
    midi: ['.mid', '.midi']
  },
  
  // Tier Configuration
  TIERS: {
    basic: {
      name: 'Basic',
      price: 'Free',
      sophistication: '65%',
      features: {
        upload_limit: 50,
        formats: ['mp3', 'wav'],
        drum_characteristics: 'Minimal',
        arrangement: 'Standard',
        output: 'Stereo mp3',
        storage: 'None'
      }
    },
    advanced: {
      name: 'Advanced',
      price: '$19/month',
      sophistication: '82%',
      features: {
        upload_limit: 200,
        formats: ['mp3', 'wav', 'flac', 'midi'],
        drum_characteristics: 'Moderate',
        arrangement: 'Minimal Custom',
        output: 'Stereo mp3/wav and MIDI',
        storage: 'Limited'
      }
    },
    professional: {
      name: 'Professional',
      price: '$49/month',
      sophistication: '88.7%',
      features: {
        upload_limit: 500,
        formats: ['mp3', 'wav', 'flac', 'aac', 'm4a', 'midi'],
        drum_characteristics: 'Complex',
        arrangement: 'Fully Custom',
        output: 'Stereo, Stem, MIDI',
        storage: 'Extensive'
      }
    }
  },
  
  // WebSocket Configuration
  WEBSOCKET_URL: process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws',
  
  // Progress Polling
  PROGRESS_POLL_INTERVAL: 2000, // 2 seconds
  
  // UI Configuration
  THEME: {
    primary: '#7C3AED', // Purple
    secondary: '#F59E0B', // Gold
    accent: '#10B981', // Green
    background: '#0F172A' // Dark slate
  }
};

export default APP_CONFIG;
