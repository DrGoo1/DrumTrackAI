import React, { useState, useRef } from 'react';
import { 
  Zap, Upload, Play, Pause, Brain, AudioWaveform, Database, 
  CheckCircle, ArrowRight, Star, Target, Music, Users,
  FileAudio, Mic, Settings, Download, Share, Eye, Clock
} from 'lucide-react';

const ProfessionalTier = ({ tier, navigateTo }) => {
  const [uploadMethod, setUploadMethod] = useState('batch');
  const [analysisType, setAnalysisType] = useState('advanced');
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisProgress, setAnalysisProgress] = useState(0);
  const [batchResults, setBatchResults] = useState(null);
  const fileInputRef = useRef(null);

  const uploadMethods = [
    {
      id: 'batch',
      name: 'Batch Processing',
      icon: Database,
      description: 'Upload up to 50 files for batch analysis'
    },
    {
      id: 'single',
      name: 'Single File',
      icon: Upload,
      description: 'Upload individual drum tracks'
    },
    {
      id: 'signature',
      name: 'Signature Songs',
      icon: Star,
      description: 'Limited access to signature songs'
    },
    {
      id: 'beats',
      name: 'Classic Beats',
      icon: Music,
      description: 'Access to 40 classic drum beats'
    }
  ];

  const analysisTypes = [
    {
      id: 'advanced',
      name: 'Advanced Analysis',
      icon: Zap,
      description: 'Professional-grade pattern and style analysis',
      features: ['82% AI Sophistication', 'Pattern Recognition', 'Style Classification', 'Real-time Monitoring']
    },
    {
      id: 'batch',
      name: 'Batch Analysis',
      icon: Database,
      description: 'Process multiple files with consistent analysis',
      features: ['Up to 50 Files', 'Progress Tracking', 'Batch Reports', 'Export Options']
    },
    {
      id: 'realtime',
      name: 'Real-time Monitor',
      icon: Clock,
      description: 'Live monitoring of analysis progress',
      features: ['Live Updates', 'Progress Tracking', 'Status Monitoring', 'Performance Metrics']
    },
    {
      id: 'comparison',
      name: 'Style Comparison',
      icon: Users,
      description: 'Compare drum styles and patterns',
      features: ['Style Matching', 'Pattern Comparison', 'Similarity Analysis', 'Genre Classification']
    }
  ];

  const classicBeats = [
    { name: 'Funky Drummer', artist: 'James Brown', bpm: '93', style: 'Funk', available: true },
    { name: 'When the Levee Breaks', artist: 'Led Zeppelin', bpm: '71', style: 'Rock', available: true },
    { name: 'Cissy Strut', artist: 'The Meters', bpm: '90', style: 'Funk', available: true },
    { name: 'We Will Rock You', artist: 'Queen', bpm: '114', style: 'Rock', available: true },
    { name: 'Tom Sawyer', artist: 'Rush', bpm: '174', style: 'Progressive', available: false },
    { name: 'Rosanna', artist: 'Toto', bpm: '93', style: 'Pop/Rock', available: false }
  ];

  const handleFileUpload = (event) => {
    const files = Array.from(event.target.files).slice(0, 50); // Limit to 50 files
    setSelectedFiles(files);
  };

  const startBatchAnalysis = async () => {
    setIsAnalyzing(true);
    setAnalysisProgress(0);
    
    // Simulate batch analysis progress
    const progressInterval = setInterval(() => {
      setAnalysisProgress(prev => {
        if (prev >= 100) {
          clearInterval(progressInterval);
          setIsAnalyzing(false);
          setBatchResults({
            totalFiles: selectedFiles.length || 8,
            completed: selectedFiles.length || 8,
            averageSophistication: '84.2%',
            averageAccuracy: '91.5%',
            processingTime: '4m 32s',
            detectedStyles: ['Funk', 'Rock', 'Jazz', 'Latin'],
            topPatterns: ['Linear Fill', 'Ghost Notes', 'Cross-stick', 'Hi-hat Work']
          });
          return 100;
        }
        return prev + 1.5;
      });
    }, 80);
  };

  const renderUploadMethod = () => {
    switch (uploadMethod) {
      case 'batch':
        return (
          <div className="space-y-6">
            <div 
              className="border-2 border-dashed border-purple-500/50 rounded-xl p-8 text-center hover:border-purple-500 transition-colors cursor-pointer"
              onClick={() => fileInputRef.current?.click()}
            >
              <Database className="h-12 w-12 text-purple-400 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-white mb-2">
                Batch Upload (Up to 50 files)
              </h3>
              <p className="text-gray-400 mb-4">
                Upload multiple drum tracks for efficient batch processing. Max 200MB per file.
              </p>
              <button className="px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors">
                Select Files for Batch
              </button>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept="audio/*"
                onChange={handleFileUpload}
                className="hidden"
              />
            </div>
            
            {selectedFiles.length > 0 && (
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <h4 className="text-white font-semibold">Batch Queue ({selectedFiles.length}/50):</h4>
                  <span className="text-purple-400 text-sm">
                    Total: {(selectedFiles.reduce((acc, file) => acc + file.size, 0) / 1024 / 1024).toFixed(1)} MB
                  </span>
                </div>
                <div className="max-h-60 overflow-y-auto space-y-2">
                  {selectedFiles.map((file, index) => (
                    <div key={index} className="flex items-center justify-between bg-white/5 rounded-lg p-3">
                      <div className="flex items-center gap-3">
                        <FileAudio className="h-5 w-5 text-purple-400" />
                        <span className="text-white">{file.name}</span>
                        <span className="text-gray-400 text-sm">
                          ({(file.size / 1024 / 1024).toFixed(1)} MB)
                        </span>
                      </div>
                      <button className="text-red-400 hover:text-red-300 text-sm">Remove</button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        );
        
      case 'single':
        return (
          <div className="space-y-6">
            <div 
              className="border-2 border-dashed border-purple-500/50 rounded-xl p-8 text-center hover:border-purple-500 transition-colors cursor-pointer"
              onClick={() => fileInputRef.current?.click()}
            >
              <Upload className="h-12 w-12 text-purple-400 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-white mb-2">
                Upload Single File
              </h3>
              <p className="text-gray-400 mb-4">
                Upload one drum track for detailed analysis. Supports WAV, MP3, FLAC, M4A up to 200MB.
              </p>
              <button className="px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors">
                Choose File
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept="audio/*"
                onChange={handleFileUpload}
                className="hidden"
              />
            </div>
          </div>
        );
        
      case 'signature':
        return (
          <div className="space-y-4">
            <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4 mb-6">
              <div className="flex items-center gap-2 text-yellow-400 mb-2">
                <Star className="h-5 w-5" />
                <span className="font-semibold">Limited Access</span>
              </div>
              <p className="text-yellow-300 text-sm">
                Professional tier includes limited access to signature songs. Upgrade to Expert for full access.
              </p>
            </div>
            
            <h3 className="text-xl font-semibold text-white mb-4">Available Signature Songs</h3>
            <div className="bg-white/5 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-purple-500 rounded-lg flex items-center justify-center">
                    <Music className="h-6 w-6 text-white" />
                  </div>
                  <div>
                    <h4 className="text-white font-semibold">Sample Analysis</h4>
                    <p className="text-gray-400">Preview of signature song analysis</p>
                  </div>
                </div>
                <button className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors">
                  Try Sample
                </button>
              </div>
            </div>
            
            <div className="text-center py-8">
              <p className="text-gray-400 mb-4">Want full access to signature songs?</p>
              <button 
                onClick={() => navigateTo('expert')}
                className="px-6 py-3 bg-gradient-to-r from-yellow-500 to-orange-500 text-white rounded-lg hover:from-yellow-600 hover:to-orange-600 transition-all"
              >
                Upgrade to Expert
              </button>
            </div>
          </div>
        );
        
      case 'beats':
        return (
          <div className="space-y-4">
            <h3 className="text-xl font-semibold text-white mb-4">Classic Drum Beats Database</h3>
            {classicBeats.map((beat, index) => (
              <div key={index} className={`rounded-lg p-4 ${beat.available ? 'bg-white/5 hover:bg-white/10' : 'bg-gray-800/50'} transition-colors ${beat.available ? 'cursor-pointer' : 'cursor-not-allowed'}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
                      beat.available 
                        ? 'bg-gradient-to-r from-blue-500 to-purple-500' 
                        : 'bg-gray-600'
                    }`}>
                      <AudioWaveform className="h-6 w-6 text-white" />
                    </div>
                    <div>
                      <h4 className={`font-semibold ${beat.available ? 'text-white' : 'text-gray-500'}`}>
                        {beat.name}
                      </h4>
                      <p className={beat.available ? 'text-gray-400' : 'text-gray-600'}>
                        {beat.artist}
                      </p>
                      <div className="flex items-center gap-4 text-sm mt-1">
                        <span className={beat.available ? 'text-gray-500' : 'text-gray-600'}>
                          BPM: {beat.bpm}
                        </span>
                        <span className={beat.available ? 'text-gray-500' : 'text-gray-600'}>
                          Style: {beat.style}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {beat.available ? (
                      <>
                        <button className="p-2 bg-white/10 rounded-lg hover:bg-white/20 transition-colors">
                          <Play className="h-4 w-4 text-white" />
                        </button>
                        <button className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors">
                          Analyze
                        </button>
                      </>
                    ) : (
                      <div className="text-gray-500 text-sm">Expert Only</div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        );
        
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen py-20">
      <div className="container mx-auto px-4">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="flex items-center justify-center gap-4 mb-6">
            <div className="w-16 h-16 bg-gradient-to-r from-purple-500 to-purple-600 rounded-2xl flex items-center justify-center">
              <Zap className="h-8 w-8 text-white" />
            </div>
            <div>
              <h1 className="text-4xl font-bold text-white">Professional Tier</h1>
              <p className="text-purple-400">82% AI Sophistication</p>
            </div>
          </div>
          <p className="text-xl text-gray-300 max-w-3xl mx-auto">
            Advanced drum analysis for producers and music professionals. 
            Batch processing, real-time monitoring, and professional-grade analysis tools.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Upload Method Selection */}
          <div className="lg:col-span-1">
            <h2 className="text-2xl font-bold text-white mb-6">Choose Input Method</h2>
            <div className="space-y-3">
              {uploadMethods.map((method) => {
                const Icon = method.icon;
                return (
                  <button
                    key={method.id}
                    onClick={() => setUploadMethod(method.id)}
                    className={`w-full p-4 rounded-xl text-left transition-all ${
                      uploadMethod === method.id
                        ? 'bg-gradient-to-r from-purple-500/20 to-blue-500/20 border-2 border-purple-500/50'
                        : 'bg-white/5 hover:bg-white/10 border-2 border-transparent'
                    }`}
                  >
                    <div className="flex items-center gap-3 mb-2">
                      <Icon className={`h-5 w-5 ${uploadMethod === method.id ? 'text-purple-400' : 'text-gray-400'}`} />
                      <span className="text-white font-semibold">{method.name}</span>
                    </div>
                    <p className="text-gray-400 text-sm">{method.description}</p>
                  </button>
                );
              })}
            </div>

            {/* Analysis Type Selection */}
            <h2 className="text-2xl font-bold text-white mb-6 mt-8">Analysis Type</h2>
            <div className="space-y-3">
              {analysisTypes.map((type) => {
                const Icon = type.icon;
                return (
                  <button
                    key={type.id}
                    onClick={() => setAnalysisType(type.id)}
                    className={`w-full p-4 rounded-xl text-left transition-all ${
                      analysisType === type.id
                        ? 'bg-gradient-to-r from-blue-500/20 to-indigo-500/20 border-2 border-blue-500/50'
                        : 'bg-white/5 hover:bg-white/10 border-2 border-transparent'
                    }`}
                  >
                    <div className="flex items-center gap-3 mb-2">
                      <Icon className={`h-5 w-5 ${analysisType === type.id ? 'text-blue-400' : 'text-gray-400'}`} />
                      <span className="text-white font-semibold">{type.name}</span>
                    </div>
                    <p className="text-gray-400 text-sm mb-2">{type.description}</p>
                    <div className="flex flex-wrap gap-1">
                      {type.features.map((feature, index) => (
                        <span key={index} className="text-xs bg-white/10 text-gray-300 px-2 py-1 rounded">
                          {feature}
                        </span>
                      ))}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Main Content Area */}
          <div className="lg:col-span-2">
            <div className="bg-white/5 backdrop-blur-md rounded-2xl p-8">
              <h2 className="text-2xl font-bold text-white mb-6">
                {uploadMethods.find(m => m.id === uploadMethod)?.name}
              </h2>
              
              {renderUploadMethod()}

              {/* Analysis Controls */}
              {(selectedFiles.length > 0 || uploadMethod !== 'single') && uploadMethod !== 'signature' && (
                <div className="mt-8 pt-8 border-t border-white/20">
                  <div className="flex items-center justify-between mb-6">
                    <div>
                      <h3 className="text-xl font-semibold text-white mb-2">Ready for Analysis</h3>
                      <p className="text-gray-400">
                        Using Professional Model with {analysisTypes.find(t => t.id === analysisType)?.name}
                      </p>
                    </div>
                    <button
                      onClick={startBatchAnalysis}
                      disabled={isAnalyzing}
                      className="px-8 py-4 bg-gradient-to-r from-purple-500 to-purple-600 text-white rounded-xl font-semibold hover:from-purple-600 hover:to-purple-700 transition-all disabled:opacity-50 flex items-center gap-2"
                    >
                      {isAnalyzing ? (
                        <>
                          <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                          Processing...
                        </>
                      ) : (
                        <>
                          <Zap className="h-5 w-5" />
                          Start Analysis
                        </>
                      )}
                    </button>
                  </div>

                  {/* Progress Bar */}
                  {isAnalyzing && (
                    <div className="mb-6">
                      <div className="flex justify-between text-sm text-gray-400 mb-2">
                        <span>Professional Model Processing</span>
                        <span>{analysisProgress.toFixed(1)}%</span>
                      </div>
                      <div className="w-full bg-gray-700 rounded-full h-3">
                        <div 
                          className="bg-gradient-to-r from-purple-500 to-blue-500 h-3 rounded-full transition-all duration-300"
                          style={{ width: `${analysisProgress}%` }}
                        ></div>
                      </div>
                      <div className="text-center text-gray-400 text-sm mt-2">
                        Processing {uploadMethod === 'batch' ? 'batch files' : 'audio file'}...
                      </div>
                    </div>
                  )}

                  {/* Batch Results */}
                  {batchResults && (
                    <div className="bg-black/30 rounded-xl p-6">
                      <h3 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
                        <CheckCircle className="h-6 w-6 text-green-400" />
                        Batch Analysis Complete
                      </h3>
                      
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                        <div className="text-center">
                          <div className="text-2xl font-bold text-purple-400">{batchResults.completed}/{batchResults.totalFiles}</div>
                          <div className="text-gray-400 text-sm">Files Processed</div>
                        </div>
                        <div className="text-center">
                          <div className="text-2xl font-bold text-blue-400">{batchResults.averageSophistication}</div>
                          <div className="text-gray-400 text-sm">Avg Sophistication</div>
                        </div>
                        <div className="text-center">
                          <div className="text-2xl font-bold text-green-400">{batchResults.averageAccuracy}</div>
                          <div className="text-gray-400 text-sm">Avg Accuracy</div>
                        </div>
                        <div className="text-center">
                          <div className="text-2xl font-bold text-yellow-400">{batchResults.processingTime}</div>
                          <div className="text-gray-400 text-sm">Total Time</div>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                          <h4 className="text-white font-semibold mb-3">Detected Styles</h4>
                          <div className="space-y-2">
                            {batchResults.detectedStyles.map((style, index) => (
                              <div key={index} className="flex items-center gap-2">
                                <div className="w-3 h-3 bg-purple-400 rounded-full"></div>
                                <span className="text-gray-300 text-sm">{style}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                        
                        <div>
                          <h4 className="text-white font-semibold mb-3">Top Patterns</h4>
                          <div className="space-y-2">
                            {batchResults.topPatterns.map((pattern, index) => (
                              <div key={index} className="flex items-center gap-2">
                                <CheckCircle className="h-4 w-4 text-green-400" />
                                <span className="text-gray-300 text-sm">{pattern}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>

                      <div className="flex gap-4 mt-6">
                        <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2">
                          <Download className="h-4 w-4" />
                          Export Batch Report
                        </button>
                        <button className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors flex items-center gap-2">
                          <Eye className="h-4 w-4" />
                          View Details
                        </button>
                        <button className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex items-center gap-2">
                          <Share className="h-4 w-4" />
                          Share Results
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Features Showcase */}
        <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="bg-white/5 backdrop-blur-md rounded-xl p-6 text-center">
            <div className="w-12 h-12 bg-gradient-to-r from-purple-500 to-blue-500 rounded-xl flex items-center justify-center mx-auto mb-4">
              <Database className="h-6 w-6 text-white" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-3">Batch Processing</h3>
            <p className="text-gray-400">
              Process up to 50 files simultaneously with advanced batch analysis and reporting.
            </p>
          </div>
          
          <div className="bg-white/5 backdrop-blur-md rounded-xl p-6 text-center">
            <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-indigo-500 rounded-xl flex items-center justify-center mx-auto mb-4">
              <Clock className="h-6 w-6 text-white" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-3">Real-time Monitoring</h3>
            <p className="text-gray-400">
              Live progress tracking and performance monitoring for all analysis operations.
            </p>
          </div>
          
          <div className="bg-white/5 backdrop-blur-md rounded-xl p-6 text-center">
            <div className="w-12 h-12 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-xl flex items-center justify-center mx-auto mb-4">
              <Target className="h-6 w-6 text-white" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-3">82% Sophistication</h3>
            <p className="text-gray-400">
              Advanced AI model with professional-grade pattern recognition and style analysis.
            </p>
          </div>
        </div>

        {/* Upgrade CTA */}
        <div className="mt-16 bg-gradient-to-r from-yellow-500/10 to-orange-500/10 border border-yellow-500/30 rounded-2xl p-8 text-center">
          <h2 className="text-2xl font-bold text-white mb-4">
            Want Even More Power?
          </h2>
          <p className="text-gray-300 mb-6">
            Upgrade to Expert tier for 88.7% AI sophistication, MVSep stem separation, 
            unlimited processing, and full signature song access.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <button 
              onClick={() => navigateTo('expert')}
              className="px-8 py-4 bg-gradient-to-r from-yellow-500 to-orange-500 text-white rounded-xl font-semibold hover:from-yellow-600 hover:to-orange-600 transition-all transform hover:scale-105 flex items-center justify-center gap-2"
            >
              <Crown className="h-5 w-5" />
              Upgrade to Expert
            </button>
            <button 
              onClick={() => navigateTo('comparison')}
              className="px-8 py-4 bg-white/10 text-white rounded-xl font-semibold hover:bg-white/20 transition-all flex items-center justify-center gap-2"
            >
              Compare All Tiers
              <ArrowRight className="h-5 w-5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProfessionalTier;
