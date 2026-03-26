import React, { useState, useRef } from 'react';
import { 
  Zap, Upload, Play, Pause, Music, Users, Youtube,
  FileAudio, Mic, Settings, Download, Share, Eye, Search, ExternalLink
} from 'lucide-react';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

const ProfessionalTier = ({ tier, navigateTo }) => {
  const [selectedSection, setSelectedSection] = useState('upload');
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadedFileKey, setUploadedFileKey] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [drummerName, setDrummerName] = useState('');
  const [selectedDrummer, setSelectedDrummer] = useState(null);
  const [selectedClassicBeat, setSelectedClassicBeat] = useState(null);
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState([]);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [recordedAudio, setRecordedAudio] = useState(null);
  const fileInputRef = useRef(null);

  const openDCSM = (sourceType, data) => {
    // Build URL with parameters for DCSM
    const params = new URLSearchParams();
    params.set('source', sourceType);
    
    if (sourceType === 'upload' && uploadedFileKey) {
      params.set('fileKey', uploadedFileKey);
      params.set('filename', selectedFile.name);
      console.log('🚀 Opening DCSM with upload:', {
        fileKey: uploadedFileKey,
        filename: selectedFile.name,
        fullURL: `http://localhost:3000?${params.toString()}`
      });
    } else if (sourceType === 'drummer' && selectedDrummer) {
      params.set('drummer', selectedDrummer);
    } else if (sourceType === 'classic' && selectedClassicBeat) {
      params.set('beat', selectedClassicBeat.name);
      params.set('bpm', selectedClassicBeat.bpm);
      params.set('style', selectedClassicBeat.style);
    } else if (sourceType === 'recorded' && recordedAudio) {
      params.set('duration', recordingTime);
    }
    
    const dcsmUrl = `http://localhost:3000?${params.toString()}`;
    console.log('📤 Opening DCSM at:', dcsmUrl);
    
    // Open DCSM in new window
    window.open(dcsmUrl, '_blank');
  };

  const classicBeats = [
    { name: 'Funky Drummer', artist: 'James Brown', bpm: '93', style: 'Funk', available: true },
    { name: 'When the Levee Breaks', artist: 'Led Zeppelin', bpm: '71', style: 'Rock', available: true },
    { name: 'Cissy Strut', artist: 'The Meters', bpm: '90', style: 'Funk', available: true },
    { name: 'We Will Rock You', artist: 'Queen', bpm: '114', style: 'Rock', available: true },
    { name: 'Amen Break', artist: 'The Winstons', bpm: '136', style: 'Breakbeat', available: true },
    { name: 'Good Times Bad Times', artist: 'Led Zeppelin', bpm: '96', style: 'Rock', available: true },
  ];

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (file) {
      setSelectedFile(file);
      setIsUploading(true);
      
      try {
        // Upload to backend immediately
        const formData = new FormData();
        formData.append('file', file);  // Backend expects 'file' field name
        
        const response = await fetch(`${API_BASE_URL}/upload`, {
          method: 'POST',
          body: formData
        });
        
        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`Upload failed: ${errorText}`);
        }
        
        const result = await response.json();
        setUploadedFileKey(result.key || result.file_key);
        console.log('File uploaded to backend:', result.key || result.file_key);
      } catch (error) {
        console.error('Upload error:', error);
        alert(`Failed to upload file: ${error.message}`);
      } finally {
        setIsUploading(false);
      }
    }
  };

  const searchDrummer = async () => {
    if (!drummerName.trim()) return;
    
    setIsSearching(true);
    // Simulate YouTube search
    setTimeout(() => {
      setSearchResults([
        { title: `${drummerName} - Drum Solo Compilation`, views: '1.2M views', duration: '10:34' },
        { title: `${drummerName} - Best Performances`, views: '856K views', duration: '8:45' },
        { title: `${drummerName} - Technique Breakdown`, views: '423K views', duration: '12:15' },
      ]);
      setIsSearching(false);
    }, 1500);
  };

  const startRecording = () => {
    setIsRecording(true);
    setRecordingTime(0);
    const interval = setInterval(() => {
      setRecordingTime(prev => {
        if (prev >= 30) {
          clearInterval(interval);
          setIsRecording(false);
          return 30;
        }
        return prev + 1;
      });
    }, 1000);
  };

  const stopRecording = () => {
    setIsRecording(false);
    setRecordedAudio(true); // Mark that we have recorded audio
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
              <p className="text-purple-400">Advanced Drum Track Creation</p>
            </div>
          </div>
          <p className="text-xl text-gray-300 max-w-3xl mx-auto">
            Upload your music, analyze professional drummers, access classic beats, or sing in your own groove.
          </p>
        </div>

        {/* Main Content */}
        <div className="max-w-5xl mx-auto space-y-8">
          
          {/* 1. Upload Audio File Section */}
          <div className="bg-white/5 backdrop-blur-md rounded-2xl p-8">
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
              <Upload className="h-7 w-7 text-purple-400" />
              Upload Audio File
            </h2>
            
            <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4 mb-6">
              <p className="text-blue-300 text-sm mb-3">
                <strong>Important:</strong> Upload audio files <strong>WITHOUT</strong> existing drum tracks for best results.
              </p>
              <p className="text-blue-200 text-sm mb-3">
                If your audio has drums, use MVSep's DrumSep process to remove them first:
              </p>
              <a 
                href="https://mvsep.com" 
                target="_blank" 
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
              >
                <ExternalLink className="h-4 w-4" />
                Open MVSep DrumSep Tool
              </a>
              <p className="text-blue-200 text-xs mt-3">
                On MVSep: Select "DrumSep" model, upload your track, download the "no_drums" version, then upload here.
              </p>
            </div>

            <div 
              className="border-2 border-dashed border-purple-500/50 rounded-xl p-12 text-center hover:border-purple-500 transition-colors cursor-pointer"
              onClick={() => fileInputRef.current?.click()}
            >
              <Upload className="h-16 w-16 text-purple-400 mx-auto mb-4" />
              <h3 className="text-2xl font-semibold text-white mb-3">
                Drop Your Audio Here
              </h3>
              <p className="text-gray-400 mb-4 max-w-md mx-auto">
                Upload drum-free audio (vocals, guitar, bass, etc.) and we'll create the perfect drum track to match.
              </p>
              <p className="text-gray-500 text-sm mb-6">
                Supports: MP3, WAV, FLAC, M4A • Max 200MB
              </p>
              <button className="px-8 py-4 bg-gradient-to-r from-purple-500 to-purple-600 text-white rounded-xl font-semibold hover:from-purple-600 hover:to-purple-700 transition-all">
                Select Audio File
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept="audio/*"
                onChange={handleFileUpload}
                className="hidden"
              />
            </div>

            {selectedFile && (
              <div className="mt-6 bg-white/10 rounded-lg p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <FileAudio className="h-6 w-6 text-purple-400" />
                  <div>
                    <div className="text-white font-semibold">{selectedFile.name}</div>
                    <div className="text-gray-400 text-sm">
                      {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                    </div>
                    {isUploading && (
                      <div className="text-yellow-400 text-sm mt-1">Uploading to server...</div>
                    )}
                    {uploadedFileKey && !isUploading && (
                      <div className="text-green-400 text-sm mt-1">✓ Ready for drum track creation</div>
                    )}
                  </div>
                </div>
                <button 
                  onClick={() => openDCSM('upload')}
                  disabled={isUploading || !uploadedFileKey}
                  className={`px-6 py-2 text-white rounded-lg transition-colors ${
                    isUploading || !uploadedFileKey 
                      ? 'bg-gray-600 cursor-not-allowed' 
                      : 'bg-green-600 hover:bg-green-700'
                  }`}
                >
                  {isUploading ? 'Uploading...' : 'Create Drum Track'}
                </button>
              </div>
            )}
          </div>

          {/* 2. Professional Drummer Analysis Section */}
          <div className="bg-white/5 backdrop-blur-md rounded-2xl p-8">
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
              <Users className="h-7 w-7 text-blue-400" />
              Professional Drummer Analysis
            </h2>
            
            <p className="text-gray-300 mb-6">
              Search for drum tracks from professional drummers on YouTube. Our system will analyze their style and apply it to your music.
            </p>

            <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4 mb-6">
              <p className="text-yellow-300 text-sm">
                <strong>Note:</strong> Search for one drummer at a time. You can perform multiple searches to compare different drumming styles.
              </p>
            </div>

            <div className="space-y-4">
              <div className="flex gap-3">
                <input
                  type="text"
                  value={drummerName}
                  onChange={(e) => setDrummerName(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && searchDrummer()}
                  placeholder="Enter drummer name (e.g., Dave Grohl, Neil Peart, John Bonham)"
                  className="flex-1 px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-blue-500"
                />
                <button
                  onClick={searchDrummer}
                  disabled={isSearching || !drummerName.trim()}
                  className="px-8 py-3 bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-lg font-semibold hover:from-blue-600 hover:to-blue-700 transition-all disabled:opacity-50 flex items-center gap-2"
                >
                  {isSearching ? (
                    <>
                      <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      Searching...
                    </>
                  ) : (
                    <>
                      <Search className="h-5 w-5" />
                      Search YouTube
                    </>
                  )}
                </button>
              </div>

              {searchResults.length > 0 && (
                <div className="space-y-3 mt-6">
                  <h3 className="text-lg font-semibold text-white">Search Results for "{drummerName}":</h3>
                  {searchResults.map((result, index) => (
                    <div key={index} className="bg-white/10 rounded-lg p-4 hover:bg-white/20 transition-colors cursor-pointer">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                          <div className="w-12 h-12 bg-gradient-to-r from-red-500 to-red-600 rounded-lg flex items-center justify-center">
                            <Youtube className="h-6 w-6 text-white" />
                          </div>
                          <div>
                            <div className="text-white font-semibold">{result.title}</div>
                            <div className="text-gray-400 text-sm flex items-center gap-3">
                              <span>{result.views}</span>
                              <span>•</span>
                              <span>{result.duration}</span>
                            </div>
                          </div>
                        </div>
                        <button 
                          onClick={() => {
                            setSelectedDrummer(drummerName);
                            openDCSM('drummer');
                          }}
                          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                        >
                          Analyze Style
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* 3. Classic Beats Section */}
          <div className="bg-white/5 backdrop-blur-md rounded-2xl p-8">
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
              <Music className="h-7 w-7 text-green-400" />
              Classic Beats Library
            </h2>
            
            <p className="text-gray-300 mb-6">
              Access our database of legendary drum beats, already extracted and ready to use as the foundation for your tracks.
            </p>

            <div className="space-y-3">
              {classicBeats.map((beat, index) => (
                <div key={index} className="bg-white/10 rounded-lg p-4 hover:bg-white/15 transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="w-14 h-14 bg-gradient-to-r from-green-500 to-green-600 rounded-lg flex items-center justify-center">
                        <Music className="h-7 w-7 text-white" />
                      </div>
                      <div>
                        <h3 className="text-white font-bold text-lg">{beat.name}</h3>
                        <p className="text-gray-400">{beat.artist}</p>
                        <div className="flex items-center gap-4 text-sm mt-1">
                          <span className="text-green-400">{beat.bpm} BPM</span>
                          <span className="text-gray-500">•</span>
                          <span className="text-gray-400">{beat.style}</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button className="p-3 bg-white/10 rounded-lg hover:bg-white/20 transition-colors">
                        <Play className="h-5 w-5 text-white" />
                      </button>
                      <button 
                        onClick={() => {
                          setSelectedClassicBeat(beat);
                          openDCSM('classic');
                        }}
                        className="px-6 py-3 bg-gradient-to-r from-green-500 to-green-600 text-white rounded-lg hover:from-green-600 hover:to-green-700 transition-colors font-semibold"
                      >
                        Use This Beat
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 4. Sing In a Beat Section */}
          <div className="bg-white/5 backdrop-blur-md rounded-2xl p-8">
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
              <Mic className="h-7 w-7 text-orange-400" />
              Sing In a Beat
            </h2>
            
            <p className="text-gray-300 mb-6">
              Sing, beatbox, or tap out your desired groove. We'll record it and use it as the foundation for your custom drum track.
            </p>

            <div className="bg-purple-500/10 border border-purple-500/30 rounded-lg p-6 mb-6">
              <p className="text-purple-200 text-sm mb-3">
                <strong>How it works:</strong>
              </p>
              <ol className="text-purple-200 text-sm space-y-2 list-decimal list-inside">
                <li>Click "Start Recording" and begin singing your beat</li>
                <li>We'll capture up to 30 seconds of your groove</li>
                <li>Our AI analyzes your rhythm and timing</li>
                <li>We create a professional drum track matching your feel</li>
              </ol>
            </div>

            <div className="text-center py-8">
              <div className="w-32 h-32 bg-gradient-to-r from-orange-500 to-red-500 rounded-full flex items-center justify-center mx-auto mb-6 relative">
                {isRecording && (
                  <div className="absolute inset-0 rounded-full border-4 border-red-500 animate-ping"></div>
                )}
                <Mic className="h-16 w-16 text-white" />
              </div>

              {isRecording && (
                <div className="mb-6">
                  <div className="text-4xl font-bold text-white mb-2">
                    {recordingTime}s / 30s
                  </div>
                  <div className="w-full max-w-md mx-auto bg-gray-700 rounded-full h-3">
                    <div 
                      className="bg-gradient-to-r from-orange-500 to-red-500 h-3 rounded-full transition-all duration-300"
                      style={{ width: `${(recordingTime / 30) * 100}%` }}
                    ></div>
                  </div>
                </div>
              )}

              <div className="flex justify-center gap-4">
                {!isRecording ? (
                  <button
                    onClick={startRecording}
                    className="px-8 py-4 bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-xl font-bold text-lg hover:from-orange-600 hover:to-red-600 transition-all flex items-center gap-3"
                  >
                    <div className="w-4 h-4 bg-white rounded-full"></div>
                    Start Recording
                  </button>
                ) : (
                  <button
                    onClick={stopRecording}
                    className="px-8 py-4 bg-gray-700 text-white rounded-xl font-bold text-lg hover:bg-gray-600 transition-all flex items-center gap-3"
                  >
                    <div className="w-4 h-4 bg-white"></div>
                    Stop Recording
                  </button>
                )}
                <button className="px-6 py-4 bg-white/10 text-white rounded-xl font-semibold hover:bg-white/20 transition-all">
                  Test Microphone
                </button>
              </div>

              {recordingTime > 0 && !isRecording && (
                <div className="mt-6 p-4 bg-green-500/10 border border-green-500/30 rounded-lg">
                  <p className="text-green-300 mb-3">
                    ✓ Recording captured ({recordingTime} seconds)
                  </p>
                  <button 
                    onClick={() => openDCSM('recorded')}
                    className="px-6 py-3 bg-gradient-to-r from-green-500 to-green-600 text-white rounded-lg hover:from-green-600 hover:to-green-700 transition-colors font-semibold"
                  >
                    Generate Drum Track from Recording
                  </button>
                </div>
              )}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};

export default ProfessionalTier;
