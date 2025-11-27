import React, { useState, useRef } from 'react';
import { 
  Crown, Upload, Play, Pause, Brain, AudioWaveform, Database, 
  CheckCircle, ArrowRight, Star, Zap, Target, Music,
  FileAudio, Mic, Settings, Download, Share, Eye, Users
} from 'lucide-react';

const ExpertTier = ({ tier, navigateTo }) => {
  const [uploadMethod, setUploadMethod] = useState('file');
  const [analysisType, setAnalysisType] = useState('signature');
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisProgress, setAnalysisProgress] = useState(0);
  const [results, setResults] = useState(null);
  const fileInputRef = useRef(null);

  const uploadMethods = [
    {
      id: 'file',
      name: 'Upload Audio File',
      icon: Upload,
      description: 'Upload your own drum tracks or full songs'
    },
    {
      id: 'signature',
      name: 'Signature Songs',
      icon: Star,
      description: 'Analyze legendary drummer performances'
    },
    {
      id: 'database',
      name: 'Classic Beats',
      icon: Database,
      description: 'Choose from 40+ classic drum beats'
    },
    {
      id: 'record',
      name: 'Live Recording',
      icon: Mic,
      description: 'Record drums directly in browser'
    }
  ];

  const analysisTypes = [
    {
      id: 'signature',
      name: 'Signature Analysis',
      icon: Crown,
      description: 'Full Expert Model analysis with drummer recognition',
      features: ['88.7% AI Sophistication', 'MVSep Stem Separation', 'Pattern Recognition', 'Style Classification']
    },
    {
      id: 'pattern',
      name: 'Pattern Analysis',
      icon: Target,
      description: 'Advanced drum pattern and rhythm analysis',
      features: ['Tempo Detection', 'Rhythm Complexity', 'Fill Analysis', 'Groove Classification']
    },
    {
      id: 'comparison',
      name: 'Drummer Comparison',
      icon: Users,
      description: 'Compare against signature drummer styles',
      features: ['Style Matching', 'Technique Analysis', 'Similarity Scoring', 'Influence Detection']
    },
    {
      id: 'training',
      name: 'Custom Training',
      icon: Brain,
      description: 'Train custom models on your drum library',
      features: ['Personal Model', 'Style Learning', 'Progress Tracking', 'Custom Recognition']
    }
  ];

  const signatureSongs = [
    { name: 'Rosanna', artist: 'Toto', drummer: 'Jeff Porcaro', complexity: 'Expert', duration: '5:30' },
    { name: 'Tom Sawyer', artist: 'Rush', drummer: 'Neil Peart', complexity: 'Master', duration: '4:33' },
    { name: 'Roxanne', artist: 'The Police', drummer: 'Stewart Copeland', complexity: 'Professional', duration: '3:12' }
  ];

  const classicBeats = [
    { name: 'Funky Drummer', artist: 'James Brown', bpm: '93', style: 'Funk' },
    { name: 'When the Levee Breaks', artist: 'Led Zeppelin', bpm: '71', style: 'Rock' },
    { name: 'Cissy Strut', artist: 'The Meters', bpm: '90', style: 'Funk' },
    { name: 'We Will Rock You', artist: 'Queen', bpm: '114', style: 'Rock' }
  ];

  const handleFileUpload = (event) => {
    const files = Array.from(event.target.files);
    setSelectedFiles(files);
  };

  const startAnalysis = async () => {
    setIsAnalyzing(true);
    setAnalysisProgress(0);
    
    // Simulate analysis progress
    const progressInterval = setInterval(() => {
      setAnalysisProgress(prev => {
        if (prev >= 100) {
          clearInterval(progressInterval);
          setIsAnalyzing(false);
          setResults({
            sophistication: '92.4%',
            accuracy: '94.7%',
            drummer: 'Jeff Porcaro Style',
            complexity: 'Expert Level',
            tempo: '93 BPM',
            timeSignature: '4/4',
            fills: 12,
            patterns: ['Linear Fill', 'Ghost Notes', 'Hi-hat Foot Work'],
            confidence: '96.8%'
          });
          return 100;
        }
        return prev + 2;
      });
    }, 100);
  };

  const renderUploadMethod = () => {
    switch (uploadMethod) {
      case 'file':
        return (
          <div className="space-y-6">
            <div 
              className="border-2 border-dashed border-purple-500/50 rounded-xl p-8 text-center hover:border-purple-500 transition-colors cursor-pointer"
              onClick={() => fileInputRef.current?.click()}
            >
              <Upload className="h-12 w-12 text-purple-400 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-white mb-2">
                Drop your audio files here
              </h3>
              <p className="text-gray-400 mb-4">
                Supports WAV, MP3, FLAC, M4A and more. Unlimited file size.
              </p>
              <button className="px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors">
                Choose Files
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
                <h4 className="text-white font-semibold">Selected Files:</h4>
                {selectedFiles.map((file, index) => (
                  <div key={index} className="flex items-center justify-between bg-white/5 rounded-lg p-3">
                    <div className="flex items-center gap-3">
                      <FileAudio className="h-5 w-5 text-purple-400" />
                      <span className="text-white">{file.name}</span>
                      <span className="text-gray-400 text-sm">
                        ({(file.size / 1024 / 1024).toFixed(1)} MB)
                      </span>
                    </div>
                    <button className="text-red-400 hover:text-red-300">Remove</button>
                  </div>
                ))}
              </div>
            )}
          </div>
        );
        
      case 'signature':
        return (
          <div className="space-y-4">
            <h3 className="text-xl font-semibold text-white mb-4">Signature Songs Database</h3>
            {signatureSongs.map((song, index) => (
              <div key={index} className="bg-white/5 rounded-lg p-4 hover:bg-white/10 transition-colors cursor-pointer">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-gradient-to-r from-yellow-500 to-orange-500 rounded-lg flex items-center justify-center">
                      <Music className="h-6 w-6 text-white" />
                    </div>
                    <div>
                      <h4 className="text-white font-semibold">{song.name}</h4>
                      <p className="text-gray-400">{song.artist} • {song.drummer}</p>
                      <div className="flex items-center gap-4 text-sm text-gray-500 mt-1">
                        <span>Complexity: {song.complexity}</span>
                        <span>Duration: {song.duration}</span>
                      </div>
                    </div>
                  </div>
                  <button className="px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 transition-colors">
                    Analyze
                  </button>
                </div>
              </div>
            ))}
          </div>
        );
        
      case 'database':
        return (
          <div className="space-y-4">
            <h3 className="text-xl font-semibold text-white mb-4">Classic Drum Beats</h3>
            {classicBeats.map((beat, index) => (
              <div key={index} className="bg-white/5 rounded-lg p-4 hover:bg-white/10 transition-colors cursor-pointer">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-purple-500 rounded-lg flex items-center justify-center">
                      <AudioWaveform className="h-6 w-6 text-white" />
                    </div>
                    <div>
                      <h4 className="text-white font-semibold">{beat.name}</h4>
                      <p className="text-gray-400">{beat.artist}</p>
                      <div className="flex items-center gap-4 text-sm text-gray-500 mt-1">
                        <span>BPM: {beat.bpm}</span>
                        <span>Style: {beat.style}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button className="p-2 bg-white/10 rounded-lg hover:bg-white/20 transition-colors">
                      <Play className="h-4 w-4 text-white" />
                    </button>
                    <button className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors">
                      Analyze
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        );
        
      case 'record':
        return (
          <div className="text-center space-y-6">
            <div className="w-32 h-32 bg-gradient-to-r from-red-500 to-pink-500 rounded-full flex items-center justify-center mx-auto">
              <Mic className="h-16 w-16 text-white" />
            </div>
            <h3 className="text-2xl font-semibold text-white">Live Recording</h3>
            <p className="text-gray-400 max-w-md mx-auto">
              Record your drum performance directly in the browser using your microphone or audio interface.
            </p>
            <div className="flex justify-center gap-4">
              <button className="px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center gap-2">
                <div className="w-3 h-3 bg-white rounded-full"></div>
                Start Recording
              </button>
              <button className="px-6 py-3 bg-white/10 text-white rounded-lg hover:bg-white/20 transition-colors">
                Test Audio
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
            <div className="w-16 h-16 bg-gradient-to-r from-yellow-500 to-orange-500 rounded-2xl flex items-center justify-center">
              <Crown className="h-8 w-8 text-white" />
            </div>
            <div>
              <h1 className="text-4xl font-bold text-white">Expert Tier</h1>
              <p className="text-yellow-400">88.7% AI Sophistication</p>
            </div>
          </div>
          <p className="text-xl text-gray-300 max-w-3xl mx-auto">
            Ultimate AI-powered drum analysis with MVSep integration, signature drummer recognition, 
            and unlimited processing capabilities.
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
                        ? 'bg-gradient-to-r from-yellow-500/20 to-orange-500/20 border-2 border-yellow-500/50'
                        : 'bg-white/5 hover:bg-white/10 border-2 border-transparent'
                    }`}
                  >
                    <div className="flex items-center gap-3 mb-2">
                      <Icon className={`h-5 w-5 ${uploadMethod === method.id ? 'text-yellow-400' : 'text-gray-400'}`} />
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
                        ? 'bg-gradient-to-r from-purple-500/20 to-blue-500/20 border-2 border-purple-500/50'
                        : 'bg-white/5 hover:bg-white/10 border-2 border-transparent'
                    }`}
                  >
                    <div className="flex items-center gap-3 mb-2">
                      <Icon className={`h-5 w-5 ${analysisType === type.id ? 'text-purple-400' : 'text-gray-400'}`} />
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
              {(selectedFiles.length > 0 || uploadMethod !== 'file') && (
                <div className="mt-8 pt-8 border-t border-white/20">
                  <div className="flex items-center justify-between mb-6">
                    <div>
                      <h3 className="text-xl font-semibold text-white mb-2">Ready to Analyze</h3>
                      <p className="text-gray-400">
                        Using Expert Model with {analysisTypes.find(t => t.id === analysisType)?.name}
                      </p>
                    </div>
                    <button
                      onClick={startAnalysis}
                      disabled={isAnalyzing}
                      className="px-8 py-4 bg-gradient-to-r from-yellow-500 to-orange-500 text-white rounded-xl font-semibold hover:from-yellow-600 hover:to-orange-600 transition-all disabled:opacity-50 flex items-center gap-2"
                    >
                      {isAnalyzing ? (
                        <>
                          <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                          Analyzing...
                        </>
                      ) : (
                        <>
                          <Brain className="h-5 w-5" />
                          Start Analysis
                        </>
                      )}
                    </button>
                  </div>

                  {/* Progress Bar */}
                  {isAnalyzing && (
                    <div className="mb-6">
                      <div className="flex justify-between text-sm text-gray-400 mb-2">
                        <span>Expert Model Processing</span>
                        <span>{analysisProgress}%</span>
                      </div>
                      <div className="w-full bg-gray-700 rounded-full h-3">
                        <div 
                          className="bg-gradient-to-r from-yellow-500 to-orange-500 h-3 rounded-full transition-all duration-300"
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
                          <div className="text-2xl font-bold text-yellow-400">{results.sophistication}</div>
                          <div className="text-gray-400 text-sm">Sophistication</div>
                        </div>
                        <div className="text-center">
                          <div className="text-2xl font-bold text-green-400">{results.accuracy}</div>
                          <div className="text-gray-400 text-sm">Accuracy</div>
                        </div>
                        <div className="text-center">
                          <div className="text-2xl font-bold text-blue-400">{results.tempo}</div>
                          <div className="text-gray-400 text-sm">Tempo</div>
                        </div>
                        <div className="text-center">
                          <div className="text-2xl font-bold text-purple-400">{results.confidence}</div>
                          <div className="text-gray-400 text-sm">Confidence</div>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                          <h4 className="text-white font-semibold mb-3">Analysis Results</h4>
                          <div className="space-y-2 text-sm">
                            <div className="flex justify-between">
                              <span className="text-gray-400">Drummer Style:</span>
                              <span className="text-white">{results.drummer}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-400">Complexity:</span>
                              <span className="text-white">{results.complexity}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-400">Time Signature:</span>
                              <span className="text-white">{results.timeSignature}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-400">Fills Detected:</span>
                              <span className="text-white">{results.fills}</span>
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
                          Export Results
                        </button>
                        <button className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors flex items-center gap-2">
                          <Eye className="h-4 w-4" />
                          Visualize
                        </button>
                        <button className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex items-center gap-2">
                          <Share className="h-4 w-4" />
                          Share
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
            <div className="w-12 h-12 bg-gradient-to-r from-yellow-500 to-orange-500 rounded-xl flex items-center justify-center mx-auto mb-4">
              <Brain className="h-6 w-6 text-white" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-3">Expert AI Model</h3>
            <p className="text-gray-400">
              88.7% sophistication with advanced pattern recognition and signature drummer identification.
            </p>
          </div>
          
          <div className="bg-white/5 backdrop-blur-md rounded-xl p-6 text-center">
            <div className="w-12 h-12 bg-gradient-to-r from-purple-500 to-blue-500 rounded-xl flex items-center justify-center mx-auto mb-4">
              <AudioWaveform className="h-6 w-6 text-white" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-3">MVSep Integration</h3>
            <p className="text-gray-400">
              Professional stem separation with HDemucs and DrumSep for full song analysis.
            </p>
          </div>
          
          <div className="bg-white/5 backdrop-blur-md rounded-xl p-6 text-center">
            <div className="w-12 h-12 bg-gradient-to-r from-green-500 to-teal-500 rounded-xl flex items-center justify-center mx-auto mb-4">
              <Target className="h-6 w-6 text-white" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-3">Unlimited Processing</h3>
            <p className="text-gray-400">
              No limits on file size, batch processing, or analysis frequency. Full professional access.
            </p>
          </div>
        </div>

        {/* CTA */}
        <div className="text-center mt-12">
          <button 
            onClick={() => navigateTo('comparison')}
            className="px-8 py-4 bg-white/10 text-white rounded-xl font-semibold hover:bg-white/20 transition-all flex items-center justify-center gap-2 mx-auto"
          >
            Compare All Tiers
            <ArrowRight className="h-5 w-5" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default ExpertTier;
