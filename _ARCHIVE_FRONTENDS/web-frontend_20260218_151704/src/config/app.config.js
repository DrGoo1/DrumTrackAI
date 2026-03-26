// DrumTracKAI Application Configuration
// Centralized configuration for 3-tier system

export const APP_CONFIG = {
  // Application Info
  name: 'DrumTracKAI',
  version: '1.1.8',
  description: 'Professional AI Drum Analysis with 88.7% Sophistication',
  
  // API Configuration
  api: {
    baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000/api',
    timeout: 30000, // 30 seconds
    retryAttempts: 3,
    retryDelay: 1000, // 1 second
  },

  // Tier Configuration
  tiers: {
    basic: {
      id: 'basic',
      name: 'Basic',
      price: 9.99,
      currency: 'USD',
      period: 'month',
      sophistication: '65%',
      accuracy: '85%',
      color: 'blue',
      features: {
        monthlyLimit: 10,
        maxFileSize: 50 * 1024 * 1024, // 50MB
        supportedFormats: ['audio/wav', 'audio/mp3'],
        batchProcessing: false,
        realTimeMonitoring: false,
        mvsepIntegration: false,
        signatureSongs: false,
        customTraining: false,
        apiAccess: false,
        support: 'community',
      },
    },
    professional: {
      id: 'professional',
      name: 'Professional',
      price: 29.99,
      currency: 'USD',
      period: 'month',
      sophistication: '82%',
      accuracy: '91%',
      color: 'purple',
      features: {
        monthlyLimit: -1, // Unlimited
        maxFileSize: 200 * 1024 * 1024, // 200MB
        supportedFormats: ['audio/wav', 'audio/mp3', 'audio/flac', 'audio/m4a'],
        batchProcessing: true,
        batchLimit: 50,
        realTimeMonitoring: true,
        mvsepIntegration: false,
        signatureSongs: 'limited',
        customTraining: false,
        apiAccess: 'limited',
        support: 'priority',
      },
    },
    expert: {
      id: 'expert',
      name: 'Expert',
      price: 79.99,
      currency: 'USD',
      period: 'month',
      sophistication: '88.7%',
      accuracy: '94%',
      color: 'gold',
      features: {
        monthlyLimit: -1, // Unlimited
        maxFileSize: -1, // Unlimited
        supportedFormats: [], // All formats
        batchProcessing: true,
        batchLimit: -1, // Unlimited
        realTimeMonitoring: true,
        mvsepIntegration: true,
        signatureSongs: 'full',
        customTraining: true,
        apiAccess: 'full',
        support: 'dedicated',
        whiteLabelSolutions: true,
      },
    },
  },

  // Expert Model Configuration
  expertModel: {
    sophistication: '88.7%',
    validationAccuracy: '91.2%',
    testAccuracy: '89.5%',
    confidence: '92.4%',
    trainingFiles: 5650,
    capabilities: [
      'Advanced Pattern Recognition',
      'Signature Drummer Identification',
      'Style Classification',
      'Tempo and Rhythm Analysis',
      'Fill Detection and Analysis',
      'Spectral Analysis',
      'Professional Complexity Scoring',
    ],
  },

  // MVSep Integration
  mvsep: {
    enabled: true,
    models: ['HDemucs', 'DrumSep'],
    processingTime: '2-5 minutes per song',
    supportedFormats: ['wav', 'mp3', 'flac', 'm4a'],
    maxFileSize: -1, // Unlimited for Expert tier
  },

  // Database Configuration
  databases: {
    signatureSongs: {
      count: 3,
      drummers: ['Jeff Porcaro', 'Neil Peart', 'Stewart Copeland'],
      songs: [
        { name: 'Rosanna', artist: 'Toto', drummer: 'Jeff Porcaro' },
        { name: 'Tom Sawyer', artist: 'Rush', drummer: 'Neil Peart' },
        { name: 'Roxanne', artist: 'The Police', drummer: 'Stewart Copeland' },
      ],
    },
    classicBeats: {
      count: 40,
      styles: ['Rock', 'Funk', 'Jazz', 'Latin', 'Blues', 'Pop'],
      featured: [
        'Funky Drummer',
        'When the Levee Breaks',
        'Cissy Strut',
        'We Will Rock You',
        'Take Five',
      ],
    },
    sd3Samples: {
      count: 500,
      types: ['Hi-hat', 'Ride', 'Crash', 'China', 'Kick', 'Snare', 'Toms'],
      quality: '24-bit, 44.1kHz',
      duration: '1.3s average',
    },
  },

  // UI Configuration
  ui: {
    theme: {
      colors: {
        basic: '#3b82f6',
        professional: '#8b5cf6',
        expert: '#f59e0b',
        success: '#10b981',
        warning: '#f59e0b',
        error: '#ef4444',
      },
      animations: {
        duration: 300,
        easing: 'ease-out',
      },
    },
    progressUpdate: {
      interval: 1000, // 1 second
      animationDuration: 300,
    },
    notifications: {
      duration: 5000, // 5 seconds
      position: 'top-right',
    },
  },

  // Feature Flags
  features: {
    demoMode: process.env.REACT_APP_ENABLE_DEMO_MODE === 'true',
    realTimeProgress: true,
    fileUploadProgress: true,
    batchProcessing: true,
    mvsepIntegration: true,
    signatureSongs: true,
    customTraining: true,
    analytics: false, // Disabled for privacy
  },

  // Development Configuration
  development: {
    mockAPI: process.env.NODE_ENV === 'development' && !process.env.REACT_APP_API_URL,
    debugMode: process.env.NODE_ENV === 'development',
    logLevel: process.env.NODE_ENV === 'development' ? 'debug' : 'error',
  },

  // Performance Configuration
  performance: {
    uploadChunkSize: 1024 * 1024, // 1MB chunks
    maxConcurrentUploads: 3,
    progressUpdateThrottle: 100, // milliseconds
    resultsCacheTime: 300000, // 5 minutes
  },

  // Error Messages
  errors: {
    fileSize: {
      basic: 'File size exceeds Basic tier limit of 50MB. Upgrade to Professional for larger files.',
      professional: 'File size exceeds Professional tier limit of 200MB. Upgrade to Expert for unlimited size.',
    },
    fileFormat: {
      basic: 'File format not supported in Basic tier. Supported: WAV, MP3.',
      professional: 'File format not supported in Professional tier. Supported: WAV, MP3, FLAC, M4A.',
    },
    monthlyLimit: {
      basic: 'Monthly analysis limit reached (10/10). Upgrade to Professional for unlimited analyses.',
    },
    network: 'Network error. Please check your connection and try again.',
    server: 'Server error. Please try again later or contact support.',
    upload: 'Upload failed. Please check your file and try again.',
    analysis: 'Analysis failed. Please try again or contact support.',
  },

  // Success Messages
  success: {
    upload: 'File uploaded successfully!',
    analysis: 'Analysis completed successfully!',
    export: 'Results exported successfully!',
    share: 'Results shared successfully!',
  },

  // Contact Information
  contact: {
    support: 'support@drumtrackai.com',
    sales: 'sales@drumtrackai.com',
    documentation: 'https://docs.drumtrackai.com',
    github: 'https://github.com/drumtrackai',
  },
};

export default APP_CONFIG;
