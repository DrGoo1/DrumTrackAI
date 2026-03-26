import React, { useState } from 'react';
import { 
  Play, CheckCircle, ArrowRight, Star, Zap, Crown, Upload, Music, Headphones, MessageCircle
} from 'lucide-react';

const LandingPage = ({ tiers, navigateTo }) => {
  const [isPlaying, setIsPlaying] = useState(false);

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Hero Section - Redesigned with New Logo and Drumset */}
      <section className="relative overflow-hidden py-12">
        {/* Background Drumset Image */}
        <div className="absolute right-0 top-1/2 transform -translate-y-1/2 opacity-20 z-0">
          <img 
            src="/images/drumset-illustration.png" 
            alt="DrumTracKAI Drumset" 
            className="w-96 h-auto"
          />
        </div>
        
        <div className="relative z-10 max-w-7xl mx-auto px-4">
          <div className="text-center mb-8">
            {/* DrumTracKAI Logo */}
            <div className="mb-6">
              <img 
                src="/images/drumtrackai-logo.png" 
                alt="DrumTracKAI Logo" 
                className="w-32 h-32 mx-auto mb-4"
              />
            </div>
            
            {/* Centered DrumTracKAI Name with Artistic Font */}
            <h1 className="text-6xl md:text-7xl font-bold mb-4 gradient-text" style={{fontFamily: 'serif'}}>
              DrumTracKAI
            </h1>
            
            {/* Subtitle */}
            <p className="text-2xl font-bold mb-6 gradient-text-gold">
              Create human sounding drum tracks!
            </p>
            
            {/* Main Description */}
            <p className="text-xl text-gray-300 mb-8 max-w-3xl mx-auto">
              Use DrumTracKAI to create realistic drum tracks that sound like they were played by a real drummer!
            </p>
          </div>

          {/* Audio Upload Feature Highlight */}
          <div className="bg-gradient-to-r from-purple-900/30 to-blue-900/30 rounded-xl p-8 mb-12 max-w-4xl mx-auto">
            <div className="text-center">
              <Upload className="w-16 h-16 text-purple-400 mx-auto mb-4" />
              <h2 className="text-3xl font-bold mb-4 gradient-text">
                Upload Your Audio - Get Perfect Drum Tracks
              </h2>
              <p className="text-lg text-gray-300 mb-6">
                Simply upload any audio file and DrumTracKAI will analyze it and create a drum track that perfectly matches your music's style, tempo, and feel.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-white/5 rounded-lg p-4">
                  <Star className="w-8 h-8 text-blue-400 mx-auto mb-2" />
                  <h3 className="font-bold text-blue-400 mb-2">Basic</h3>
                  <p className="text-sm text-gray-400">Simple drum arrangement that matches your audio</p>
                </div>
                <div className="bg-white/5 rounded-lg p-4">
                  <Zap className="w-8 h-8 text-purple-400 mx-auto mb-2" />
                  <h3 className="font-bold text-purple-400 mb-2">Advanced</h3>
                  <p className="text-sm text-gray-400">Customizable drum arrangements with modification options</p>
                </div>
                <div className="bg-white/5 rounded-lg p-4">
                  <Crown className="w-8 h-8 text-yellow-400 mx-auto mb-2" />
                  <h3 className="font-bold text-yellow-400 mb-2">Professional</h3>
                  <p className="text-sm text-gray-400">Bass integration and complex drum arrangements</p>
                </div>
              </div>
            </div>
          </div>

          {/* Before/After Audio Comparison - Tightened */}
          <div className="mb-12">
            <h2 className="text-3xl font-bold text-center mb-8 gradient-text">
              Hear the Difference
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto">
              {/* Before - Robotic */}
              <div className="bg-white/5 backdrop-blur-md rounded-xl p-6">
                <h3 className="text-xl font-bold text-white mb-3">Before: Robotic</h3>
                <div className="bg-gray-800 rounded-lg p-3 mb-3">
                  <div className="flex items-center gap-1 mb-2">
                    <div className="w-1 h-6 bg-red-500 rounded"></div>
                    <div className="w-1 h-4 bg-red-400 rounded"></div>
                    <div className="w-1 h-8 bg-red-500 rounded"></div>
                    <div className="w-1 h-3 bg-red-400 rounded"></div>
                    <div className="w-1 h-6 bg-red-500 rounded"></div>
                  </div>
                  <p className="text-gray-400 text-xs">Mechanical, predictable timing</p>
                </div>
                <button className="w-full px-3 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center justify-center text-sm">
                  <Play className="mr-2 h-3 w-3" /> Play Robotic
                </button>
              </div>

              {/* After - DrumTracKAI */}
              <div className="bg-white/5 backdrop-blur-md rounded-xl p-6">
                <h3 className="text-xl font-bold text-white mb-3">After: DrumTracKAI</h3>
                <div className="bg-gray-800 rounded-lg p-3 mb-3">
                  <div className="flex items-center gap-1 mb-2">
                    <div className="w-1 h-5 bg-green-500 rounded"></div>
                    <div className="w-1 h-7 bg-green-400 rounded"></div>
                    <div className="w-1 h-4 bg-green-500 rounded"></div>
                    <div className="w-1 h-6 bg-green-400 rounded"></div>
                    <div className="w-1 h-3 bg-green-500 rounded"></div>
                  </div>
                  <p className="text-gray-400 text-xs">Natural, human-like feel</p>
                </div>
                <button className="w-full px-3 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex items-center justify-center text-sm">
                  <Play className="mr-2 h-3 w-3" /> Play DrumTracKAI
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Neural Based Technology Section - Tightened */}
      <section className="py-12 px-4">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl font-bold mb-4 gradient-text">
            Our Neural Based Technology
          </h2>
          <p className="text-lg text-gray-300 mb-6">
            Advanced AI algorithms analyze and replicate the subtle timing variations that make human drumming feel natural and musical.
          </p>
          <button className="px-6 py-3 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-lg hover:from-purple-700 hover:to-blue-700 transition-colors">
            Learn More About Our Technology
          </button>
        </div>
      </section>

      {/* Pricing Tiers - Updated */}
      <section className="py-12 px-4">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-8 gradient-text">
            Choose Your Plan
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Basic Tier - FREE with Noticeable Border */}
            <div className="bg-white/5 backdrop-blur-md rounded-xl p-6 border-2 border-blue-500">
              <div className="text-center mb-6">
                <Star className="h-10 w-10 text-blue-400 mx-auto mb-3" />
                <h3 className="text-xl font-bold text-white mb-2">Basic</h3>
                <div className="text-2xl font-bold gradient-text mb-2">FREE</div>
                <p className="text-gray-400 text-sm">Perfect for getting started</p>
              </div>
              <ul className="space-y-2 mb-6 text-sm">
                <li className="flex items-center text-gray-300">
                  <CheckCircle className="h-4 w-4 text-green-400 mr-2" />
                  Simple drum arrangement
                </li>
                <li className="flex items-center text-gray-300">
                  <CheckCircle className="h-4 w-4 text-green-400 mr-2" />
                  Audio upload & analysis
                </li>
                <li className="flex items-center text-gray-300">
                  <CheckCircle className="h-4 w-4 text-green-400 mr-2" />
                  Stereo mp3 output
                </li>
                <li className="flex items-center text-gray-300">
                  <CheckCircle className="h-4 w-4 text-green-400 mr-2" />
                  5 tracks per month
                </li>
              </ul>
              <button 
                onClick={() => navigateTo && navigateTo('basic')}
                className="w-full px-4 py-2 bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-lg hover:from-blue-600 hover:to-blue-700 transition-colors text-sm"
              >
                Get Started Free
              </button>
            </div>

            {/* Advanced Tier */}
            <div className="bg-white/5 backdrop-blur-md rounded-xl p-6 border border-purple-500 relative">
              <div className="absolute -top-2 left-1/2 transform -translate-x-1/2">
                <span className="bg-gradient-to-r from-purple-500 to-pink-500 text-white px-3 py-1 rounded-full text-xs font-semibold">
                  POPULAR
                </span>
              </div>
              <div className="text-center mb-6">
                <Zap className="h-10 w-10 text-purple-400 mx-auto mb-3" />
                <h3 className="text-xl font-bold text-white mb-2">Advanced</h3>
                <div className="text-2xl font-bold gradient-text mb-2">$19/mo</div>
                <p className="text-gray-400 text-sm">For serious musicians</p>
              </div>
              <ul className="space-y-2 mb-6 text-sm">
                <li className="flex items-center text-gray-300">
                  <CheckCircle className="h-4 w-4 text-green-400 mr-2" />
                  Moderate drum characteristics
                </li>
                <li className="flex items-center text-gray-300">
                  <CheckCircle className="h-4 w-4 text-green-400 mr-2" />
                  Drum arrangement modification
                </li>
                <li className="flex items-center text-gray-300">
                  <CheckCircle className="h-4 w-4 text-green-400 mr-2" />
                  Stereo mp3/wav and MIDI output
                </li>
                <li className="flex items-center text-gray-300">
                  <CheckCircle className="h-4 w-4 text-green-400 mr-2" />
                  Limited project storage
                </li>
              </ul>
              <button 
                onClick={() => navigateTo && navigateTo('professional')}
                className="w-full px-4 py-2 bg-gradient-to-r from-purple-500 to-purple-600 text-white rounded-lg hover:from-purple-600 hover:to-purple-700 transition-colors text-sm"
              >
                Upgrade to Advanced
              </button>
            </div>

            {/* Professional Tier */}
            <div className="bg-white/5 backdrop-blur-md rounded-xl p-6 border border-yellow-500">
              <div className="text-center mb-6">
                <Crown className="h-10 w-10 text-yellow-400 mx-auto mb-3" />
                <h3 className="text-xl font-bold text-white mb-2">Professional</h3>
                <div className="text-2xl font-bold gradient-text-gold mb-2">$49/mo</div>
                <p className="text-gray-400 text-sm">For professional studios</p>
              </div>
              <ul className="space-y-2 mb-6 text-sm">
                <li className="flex items-center text-gray-300">
                  <CheckCircle className="h-4 w-4 text-green-400 mr-2" />
                  Complex drum characteristics
                </li>
                <li className="flex items-center text-gray-300">
                  <CheckCircle className="h-4 w-4 text-green-400 mr-2" />
                  Bass integration & complex arrangements
                </li>
                <li className="flex items-center text-gray-300">
                  <CheckCircle className="h-4 w-4 text-green-400 mr-2" />
                  Stereo, Stem, MIDI output
                </li>
                <li className="flex items-center text-gray-300">
                  <CheckCircle className="h-4 w-4 text-green-400 mr-2" />
                  Extensive project storage
                </li>
              </ul>
              <button 
                onClick={() => navigateTo && navigateTo('expert')}
                className="w-full px-4 py-2 bg-gradient-to-r from-yellow-500 to-orange-500 text-white rounded-lg hover:from-yellow-600 hover:to-orange-600 transition-colors text-sm"
              >
                Go Professional
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Feature Comparison Table */}
      <section className="py-12 px-4">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-8 gradient-text">
            Feature Comparison
          </h2>
          
          <div className="bg-white/5 backdrop-blur-md rounded-xl p-6 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left py-3 px-4 text-gray-300">Feature</th>
                  <th className="text-center py-3 px-4 text-blue-400">Basic</th>
                  <th className="text-center py-3 px-4 text-purple-400">Advanced</th>
                  <th className="text-center py-3 px-4 text-yellow-400">Professional</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-gray-800">
                  <td className="py-3 px-4 text-gray-300">Custom Drum Characteristics</td>
                  <td className="text-center py-3 px-4 text-gray-400">Minimal</td>
                  <td className="text-center py-3 px-4 text-gray-400">Moderate</td>
                  <td className="text-center py-3 px-4 text-gray-400">Complex</td>
                </tr>
                <tr className="border-b border-gray-800">
                  <td className="py-3 px-4 text-gray-300">Musical Style and Arrangement</td>
                  <td className="text-center py-3 px-4 text-gray-400">Standard</td>
                  <td className="text-center py-3 px-4 text-gray-400">Minimal Custom</td>
                  <td className="text-center py-3 px-4 text-gray-400">Fully Custom</td>
                </tr>
                <tr className="border-b border-gray-800">
                  <td className="py-3 px-4 text-gray-300">Output</td>
                  <td className="text-center py-3 px-4 text-gray-400">Stereo mp3</td>
                  <td className="text-center py-3 px-4 text-gray-400">Stereo mp3/wav and MIDI</td>
                  <td className="text-center py-3 px-4 text-gray-400">Stereo, Stem, MIDI</td>
                </tr>
                <tr>
                  <td className="py-3 px-4 text-gray-300">Project Storage</td>
                  <td className="text-center py-3 px-4 text-gray-400">None</td>
                  <td className="text-center py-3 px-4 text-gray-400">Limited</td>
                  <td className="text-center py-3 px-4 text-gray-400">Extensive</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="py-12 px-4">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-8 gradient-text">
            Frequently Asked Questions
          </h2>
          
          <div className="space-y-6">
            <div className="bg-white/5 backdrop-blur-md rounded-xl p-6">
              <h3 className="text-lg font-bold text-white mb-3">What makes Professional tier special?</h3>
              <p className="text-gray-300">
                The Pro tier has access to very specific and comprehensive drum characteristics and human factors to achieve the highest degree of real sounding tracks. This includes advanced bass integration and complex arrangement capabilities.
              </p>
            </div>
            
            <div className="bg-white/5 backdrop-blur-md rounded-xl p-6">
              <h3 className="text-lg font-bold text-white mb-3">How does the audio upload feature work?</h3>
              <p className="text-gray-300">
                Simply upload any audio file and our AI will analyze the tempo, style, and musical characteristics to generate a drum track that perfectly complements your music. Different tiers offer varying levels of customization and complexity.
              </p>
            </div>
            
            <div className="bg-white/5 backdrop-blur-md rounded-xl p-6">
              <h3 className="text-lg font-bold text-white mb-3">What file formats are supported?</h3>
              <p className="text-gray-300">
                We support all major audio formats including MP3, WAV, FLAC, and more. Output formats vary by tier, with Professional offering the most comprehensive options including individual stems and MIDI files.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Claude AI Assistant Section */}
      <section className="py-12 px-4">
        <div className="max-w-4xl mx-auto">
          <div className="bg-white/5 backdrop-blur-md rounded-xl p-8 text-center">
            <MessageCircle className="w-12 h-12 text-blue-400 mx-auto mb-4" />
            <h2 className="text-2xl font-bold text-white mb-4">
              Need Help? Chat with Claude AI
            </h2>
            <p className="text-gray-300 mb-6">
              Get instant answers about drum creation, mixing techniques, and more from our intelligent Claude AI assistant.
            </p>
            <button className="px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg hover:from-blue-700 hover:to-purple-700 transition-colors">
              Start Chatting with Claude AI
            </button>
          </div>
        </div>
      </section>
    </div>
  );
};

export default LandingPage;
