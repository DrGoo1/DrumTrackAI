import React, { useState, useRef } from 'react';
import { 
  Star, Upload, Play, Pause, Brain, AudioWaveform, Database, 
  CheckCircle, ArrowRight, Zap, Crown, Music, Target,
  FileAudio, Mic, Settings, Download, Share, Eye, Lock
} from 'lucide-react';

const BasicTier = ({ tier, navigateTo }) => {
  const [uploadMethod, setUploadMethod] = useState('single');
  const [analysisType, setAnalysisType] = useState('basic');
  const [selectedFile, setSelectedFile] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisProgress, setAnalysisProgress] = useState(0);
  const [results, setResults] = useState(null);
  const [monthlyUsage, setMonthlyUsage] = useState(3); // 3 out of 10 used
  const fileInputRef = useRef(null);

  const uploadMethods = [
    {
      id: 'single',
      name: 'Single File Upload',
      icon: Upload,
      description: 'Upload one drum track at a time'
    },
    {
      id: 'sample',
      name: 'Sample Tracks',
      icon: Music,
      description: 'Try our sample drum tracks'
    },
    {
      id: 'record',
      name: 'Quick Record',
      icon: Mic,
      description: 'Record a short drum sample'
    }
  ];

  const analysisTypes = [
    {
      id: 'basic',
      name: 'Basic Analysis',
      icon: Star,
      description: 'Essential drum pattern recognition and tempo detection',
      features: ['65% AI Sophistication', 'Tempo Detection', 'Basic Patterns', 'Audio Visualization']
    },
    {
      id: 'pattern',
      name: 'Pattern Recognition',
      icon: Target,
      description: 'Identify common drum patterns and fills',
      features: ['Pattern Matching', 'Fill Detection', 'Rhythm Analysis', 'Simple Classification']
    },
    {
      id: 'tempo',
      name: 'Tempo Analysis',
      icon: AudioWaveform,
      description: 'Precise BPM detection and rhythm analysis',
      features: ['BPM Detection', 'Time Signature', 'Rhythm Stability', 'Tempo Changes']
    }
  ];

  const sampleTracks = [
    { name: 'Basic Rock Beat', bpm: '120', style: 'Rock', duration: '0:30', available: true },
    { name: 'Simple Funk Groove', bpm: '95', style: 'Funk', duration: '0:45', available: true },
    { name: 'Jazz Swing Pattern', bpm: '140', style: 'Jazz', duration: '0:35', available: true },
    { name: 'Latin Rhythm', bpm: '110', style: 'Latin', duration: '0:40', available: true },
    { name: 'Advanced Fill Pattern', bpm: '130', style: 'Rock', duration: '0:25', available: false },
    { name: 'Complex Jazz Solo', bpm: '160', style: 'Jazz', duration: '1:20', available: false }
  ];

  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (file && file.size <= 50 * 1024 * 1024) { // 50MB limit
      setSelectedFile(file);
    } else {
      alert('File size must be under 50MB for Basic tier');
    }
  };

  const startAnalysis = async () => {
    if (monthlyUsage >= 10) {
      alert('Monthly limit reached! Upgrade to Professional for more analyses.');
      return;
    }

    setIsAnalyzing(true);
    setAnalysisProgress(0);
    
    // Simulate analysis progress
    const progressInterval = setInterval(() => {
      setAnalysisProgress(prev => {
        if (prev >= 100) {
          clearInterval(progressInterval);
          setIsAnalyzing(false);
          setMonthlyUsage(prev => prev + 1);
          setResults({
            sophistication: '67.3%',
            accuracy: '86.2%',
            tempo: '120 BPM',
            timeSignature: '4/4',
            complexity: 'Intermediate',
            patterns: ['Basic Rock Beat', 'Simple Fill'],
            confidence: '89.4%',
            style: 'Rock'
          });
          return 100;
        }
        return prev + 3;
      });
    }, 150);
  };

  const renderUploadMethod = () => {
    switch (uploadMethod) {
      case 'single':
        return (
          <div className="space-y-6">
            <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4 mb-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-blue-400">
                  <Star className="h-5 w-5" />
                  <span className="font-semibold">Monthly Usage: {monthlyUsage}/10</span>
                </div>
                <div className="text-blue-300 text-sm">
                  {10 - monthlyUsage} analyses remaining
                </div>
              </div>
              <div className="w-full bg-gray-700 rounded-full h-2 mt-3">
                <div 
                  className="bg-gradient-to-r from-blue-500 to-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${(monthlyUsage / 10) * 100}%` }}
                ></div>
              </div>
            </div>

            <div 
              className="border-2 border-dashed border-blue-500/50 rounded-xl p-8 text-center hover:border-blue-500 transition-colors cursor-pointer"
              onClick={() => fileInputRef.current?.click()}
            >
              <Upload className="h-12 w-12 text-blue-400 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-white mb-2">
                Upload Your Drum Track
              </h3>
              <p className="text-gray-400 mb-4">
                Supports WAV and MP3 files up to 50MB. Perfect for individual drum analysis.
              </p>
              <button className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
                Choose File
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept="audio/wav,audio/mp3"
                onChange={handleFileUpload}
                className="hidden"
              />
            </div>
            
            {selectedFile && (
              <div className="bg-white/5 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <FileAudio className="h-5 w-5 text-blue-400" />
                    <div>
                      <span className="text-white font-medium">{selectedFile.name}</span>
                      <div className="text-gray-400 text-sm">
                        {(selectedFile.size / 1024 / 1024).toFixed(1)} MB
                      </div>
                    </div>
                  </div>
                  <button 
                    onClick={() => setSelectedFile(null)}
                    className="text-red-400 hover:text-red-300 text-sm"
                  >
                    Remove
                  </button>
                </div>
              </div>
            )}
          </div>
        );
        
      case 'sample':
        return (
          <div className="space-y-4">
            <h3 className="text-xl font-semibold text-white mb-4">Sample Drum Tracks</h3>
            {sampleTracks.map((track, index) => (
              <div key={index} className={`rounded-lg p-4 ${track.available ? 'bg-white/5 hover:bg-white/10' : 'bg-gray-800/50'} transition-colors ${track.available ? 'cursor-pointer' : 'cursor-not-allowed'}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
                      track.available 
                        ? 'bg-gradient-to-r from-blue-500 to-blue-600' 
                        : 'bg-gray-600'
                    }`}>
                      {track.available ? (
                        <Music className="h-6 w-6 text-white" />
                      ) : (
                        <Lock className="h-6 w-6 text-gray-400" />
                      )}
                    </div>
                    <div>
                      <h4 className={`font-semibold ${track.available ? 'text-white' : 'text-gray-500'}`}>
                        {track.name}
                      </h4>
                      <div className="flex items-center gap-4 text-sm mt-1">
                        <span className={track.available ? 'text-gray-400' : 'text-gray-600'}>
                          BPM: {track.bpm}
                        </span>
                        <span className={track.available ? 'text-gray-400' : 'text-gray-600'}>
                          Style: {track.style}
                        </span>
                        <span className={track.available ? 'text-gray-400' : 'text-gray-600'}>
                          Duration: {track.duration}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {track.available ? (
                      <>
                        <button className="p-2 bg-white/10 rounded-lg hover:bg-white/20 transition-colors">
                          <Play className="h-4 w-4 text-white" />
                        </button>
                        <button 
                          onClick={() => setSelectedFile({ name: track.name, size: 1024 * 1024 })}
                          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                        >
                          Analyze
                        </button>
                      </>
                    ) : (
                      <div className="flex items-center gap-2 text-gray-500 text-sm">
                        <Lock className="h-4 w-4" />
                        <span>Pro/Expert Only</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        );
        
      case 'record':
        return (
          <div className="text-center space-y-6">
            <div className="w-32 h-32 bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full flex items-center justify-center mx-auto">
              <Mic className="h-16 w-16 text-white" />
            </div>
            <h3 className="text-2xl font-semibold text-white">Quick Recording</h3>
            <p className="text-gray-400 max-w-md mx-auto">
              Record a short drum sample (up to 30 seconds) directly in your browser for quick analysis.
            </p>
            <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4 mb-6">
              <p className="text-yellow-300 text-sm">
                Basic tier recording is limited to 30 seconds. Upgrade for longer recordings.
              </p>
            </div>
            <div className="flex justify-center gap-4">
              <button className="px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center gap-2">
                <div className="w-3 h-3 bg-white rounded-full"></div>
                Start Recording
              </button>
              <button className="px-6 py-3 bg-white/10 text-white rounded-lg hover:bg-white/20 transition-colors">
                Test Microphone
              </button>
            </div>
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
            <div className="w-16 h-16 bg-gradient-to-r from-blue-500 to-blue-600 rounded-2xl flex items-center justify-center">
              <Star className="h-8 w-8 text-white" />
            </div>
            <div>
              <h1 className="text-4xl font-bold text-white">Basic Tier</h1>
              <p className="text-blue-400">65% AI Sophistication</p>
            </div>
          </div>
          <p className="text-xl text-gray-300 max-w-3xl mx-auto">
            Perfect for individual drummers and music students. 
            Get started with essential drum analysis and pattern recognition.
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
                        ? 'bg-gradient-to-r from-blue-500/20 to-indigo-500/20 border-2 border-blue-500/50'
                        : 'bg-white/5 hover:bg-white/10 border-2 border-transparent'
                    }`}
                  >
                    <div className="flex items-center gap-3 mb-2">
                      <Icon className={`h-5 w-5 ${uploadMethod === method.id ? 'text-blue-400' : 'text-gray-400'}`} />
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
                        ? 'bg-gradient-to-r from-indigo-500/20 to-purple-500/20 border-2 border-indigo-500/50'
                        : 'bg-white/5 hover:bg-white/10 border-2 border-transparent'
                    }`}
                  >
                    <div className="flex items-center gap-3 mb-2">
                      <Icon className={`h-5 w-5 ${analysisType === type.id ? 'text-indigo-400' : 'text-gray-400'}`} />
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
              {selectedFile && (
                <div className="mt-8 pt-8 border-t border-white/20">
                  <div className="flex items-center justify-between mb-6">
                    <div>
                      <h3 className="text-xl font-semibold text-white mb-2">Ready for Analysis</h3>
                      <p className="text-gray-400">
                        Using Basic Model with {analysisTypes.find(t => t.id === analysisType)?.name}
                      </p>
                    </div>
                    <button
                      onClick={startAnalysis}
                      disabled={isAnalyzing || monthlyUsage >= 10}
                      className="px-8 py-4 bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-xl font-semibold hover:from-blue-600 hover:to-blue-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                    >
                      {isAnalyzing ? (
                        <>
                          <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                          Analyzing...
                        </>
                      ) : monthlyUsage >= 10 ? (
                        <>
                          <Lock className="h-5 w-5" />
                          Limit Reached
                        </>
                      ) : (
                        <>
                          <Star className="h-5 w-5" />
                          Start Analysis
                        </>
                      )}
                    </button>
                  </div>

                  {/* Progress Bar */}
                  {isAnalyzing && (
                    <div className="mb-6">
                      <div className="flex justify-between text-sm text-gray-400 mb-2">
                        <span>Basic Model Processing</span>
                        <span>{analysisProgress}%</span>
                      </div>
                      <div className="w-full bg-gray-700 rounded-full h-3">
                        <div 
                          className="bg-gradient-to-r from-blue-500 to-indigo-500 h-3 rounded-full transition-all duration-300"
                          style={{ width: `${analysisProgress}%` }}
                        ></div>
                      </div>
                    </div>
                  )}

                  {/* Results */}
                  {results && (
                    <div className="bg-black/30 rounded-xl p-6">
                      <h3 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
                        <CheckCircle className="h-6 w-6 text-green-400" />
                        Analysis Complete
                      </h3>
                      
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                        <div className="text-center">
                          <div className="text-2xl font-bold text-blue-400">{results.sophistication}</div>
                          <div className="text-gray-400 text-sm">Sophistication</div>
                        </div>
                        <div className="text-center">
                          <div className="text-2xl font-bold text-green-400">{results.accuracy}</div>
                          <div className="text-gray-400 text-sm">Accuracy</div>
                        </div>
                        <div className="text-center">
                          <div className="text-2xl font-bold text-purple-400">{results.tempo}</div>
                          <div className="text-gray-400 text-sm">Tempo</div>
                        </div>
                        <div className="text-center">
                          <div className="text-2xl font-bold text-yellow-400">{results.confidence}</div>
                          <div className="text-gray-400 text-sm">Confidence</div>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                          <h4 className="text-white font-semibold mb-3">Basic Analysis</h4>
                          <div className="space-y-2 text-sm">
                            <div className="flex justify-between">
                              <span className="text-gray-400">Style:</span>
                              <span className="text-white">{results.style}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-400">Complexity:</span>
                              <span className="text-white">{results.complexity}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-400">Time Signature:</span>
                              <span className="text-white">{results.timeSignature}</span>
                            </div>
                          </div>
                        </div>
                        
                        <div>
                          <h4 className="text-white font-semibold mb-3">Detected Patterns</h4>
                          <div className="space-y-2">
                            {results.patterns.map((pattern, index) => (
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
                          Export JSON
                        </button>
                        <button className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors flex items-center gap-2">
                          <Eye className="h-4 w-4" />
                          View Waveform
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
            <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-indigo-500 rounded-xl flex items-center justify-center mx-auto mb-4">
              <Star className="h-6 w-6 text-white" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-3">Essential Analysis</h3>
            <p className="text-gray-400">
              Perfect for beginners with 65% AI sophistication and essential pattern recognition.
            </p>
          </div>
          
          <div className="bg-white/5 backdrop-blur-md rounded-xl p-6 text-center">
            <div className="w-12 h-12 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-xl flex items-center justify-center mx-auto mb-4">
              <AudioWaveform className="h-6 w-6 text-white" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-3">Audio Visualization</h3>
            <p className="text-gray-400">
              2D waveform visualization and basic audio analysis for learning and understanding.
            </p>
          </div>
          
          <div className="bg-white/5 backdrop-blur-md rounded-xl p-6 text-center">
            <div className="w-12 h-12 bg-gradient-to-r from-purple-500 to-pink-500 rounded-xl flex items-center justify-center mx-auto mb-4">
              <Target className="h-6 w-6 text-white" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-3">Pattern Recognition</h3>
            <p className="text-gray-400">
              Identify common drum patterns, fills, and basic rhythm analysis for skill development.
            </p>
          </div>
        </div>

        {/* Upgrade CTA */}
        <div className="mt-16 bg-gradient-to-r from-purple-500/10 to-blue-500/10 border border-purple-500/30 rounded-2xl p-8 text-center">
          <h2 className="text-2xl font-bold text-white mb-4">
            Ready for More Advanced Features?
          </h2>
          <p className="text-gray-300 mb-6">
            Upgrade to Professional for batch processing, real-time monitoring, and 82% AI sophistication. 
            Or go Expert for unlimited processing and 88.7% sophistication with MVSep integration.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <button 
              onClick={() => navigateTo('professional')}
              className="px-8 py-4 bg-gradient-to-r from-purple-500 to-purple-600 text-white rounded-xl font-semibold hover:from-purple-600 hover:to-purple-700 transition-all transform hover:scale-105 flex items-center justify-center gap-2"
            >
              <Zap className="h-5 w-5" />
              Upgrade to Professional
            </button>
            <button 
              onClick={() => navigateTo('expert')}
              className="px-8 py-4 bg-gradient-to-r from-yellow-500 to-orange-500 text-white rounded-xl font-semibold hover:from-yellow-600 hover:to-orange-600 transition-all transform hover:scale-105 flex items-center justify-center gap-2"
            >
              <Crown className="h-5 w-5" />
              Go Expert
            </button>
          </div>
          <button 
            onClick={() => navigateTo('comparison')}
            className="mt-4 px-6 py-3 bg-white/10 text-white rounded-xl font-semibold hover:bg-white/20 transition-all flex items-center justify-center gap-2 mx-auto"
          >
            Compare All Tiers
            <ArrowRight className="h-5 w-5" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default BasicTier;
