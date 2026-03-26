import React, { useState } from 'react';
import { 
  Play, CheckCircle, ArrowRight, Star, Zap, Crown
} from 'lucide-react';

const LandingPage = ({ tiers, navigateTo }) => {
  const [isPlaying, setIsPlaying] = useState(false);

  return (
    <div className="min-h-screen">
      {/* Hero Section - Restored Original Design */}
      <section className="min-h-screen pt-24 relative overflow-hidden">
        <h1 className="text-5xl md:text-6xl font-bold text-center gradient-text pt-8">
          DrumTracKAI
        </h1>
        
        <div className="max-w-7xl mx-auto px-4 py-12">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            {/* Left side content */}
            <div className="p-6 order-2 lg:order-1">
              <h2 className="text-4xl md:text-5xl font-bold mb-6 gradient-text">
                Soul of a Drummer<br />Precision of AI
              </h2>
              
              <p className="text-2xl font-bold mb-4 gradient-text-gold">
                Beyond Samples, Beyond Loops, Beyond Belief!
              </p>
              
              <p className="text-xl text-gray-300 mb-8 max-w-lg">
                Use DrumTracKAI to create realistic drum tracks that sound like they were played by a human drummer!
              </p>
              
              <div className="flex flex-col sm:flex-row space-y-4 sm:space-y-0 sm:space-x-4 max-w-xs sm:max-w-md">
                <button 
                  onClick={() => window.open('#demo', '_blank')}
                  className="px-6 py-3 rounded-lg bg-transparent border border-purple-500/50 text-white hover:bg-purple-500/10 transition-colors flex items-center justify-center"
                >
                  <Play className="mr-2 h-4 w-4" /> Watch Demo
                </button>
                
                <button 
                  onClick={() => navigateTo && navigateTo('basic')}
                  className="px-6 py-3 rounded-lg bg-gradient-to-br from-purple-500 to-purple-700 text-white hover:from-purple-600 hover:to-purple-800 transition-colors flex items-center justify-center"
                >
                  <ArrowRight className="mr-2 h-4 w-4" /> Get Started
                </button>
              </div>
            </div>

            {/* Right side - 3D Drumming Graphic */}
            <div className="order-1 lg:order-2 flex justify-center">
              <div className="relative">
                <img 
                  src="/images/drumset.png" 
                  alt="3D Drumming Visualization" 
                  className="w-full max-w-lg h-auto rounded-lg shadow-2xl"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-purple-500/20 to-transparent rounded-lg"></div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Before/After Audio Comparison */}
      <section className="py-20 px-4">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-4xl font-bold text-center mb-12 gradient-text">
            Hear the Difference
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* Before - Robotic */}
            <div className="bg-white/5 backdrop-blur-md rounded-xl p-6">
              <h3 className="text-2xl font-bold text-white mb-4">Before: Robotic</h3>
              <div className="bg-gray-800 rounded-lg p-4 mb-4">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-2 h-8 bg-red-500 rounded"></div>
                  <div className="w-2 h-6 bg-red-400 rounded"></div>
                  <div className="w-2 h-10 bg-red-500 rounded"></div>
                  <div className="w-2 h-4 bg-red-400 rounded"></div>
                  <div className="w-2 h-8 bg-red-500 rounded"></div>
                </div>
                <p className="text-gray-400 text-sm">Mechanical, predictable timing</p>
              </div>
              <button className="w-full px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center justify-center">
                <Play className="mr-2 h-4 w-4" /> Play Robotic
              </button>
            </div>

            {/* After - DrumTracKAI */}
            <div className="bg-white/5 backdrop-blur-md rounded-xl p-6">
              <h3 className="text-2xl font-bold text-white mb-4">After: DrumTracKAI</h3>
              <div className="bg-gray-800 rounded-lg p-4 mb-4">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-2 h-7 bg-green-500 rounded"></div>
                  <div className="w-2 h-9 bg-green-400 rounded"></div>
                  <div className="w-2 h-6 bg-green-500 rounded"></div>
                  <div className="w-2 h-8 bg-green-400 rounded"></div>
                  <div className="w-2 h-5 bg-green-500 rounded"></div>
                </div>
                <p className="text-gray-400 text-sm">Natural, human-like feel</p>
              </div>
              <button className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex items-center justify-center">
                <Play className="mr-2 h-4 w-4" /> Play DrumTracKAI
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Neural Based Technology Section */}
      <section className="py-20 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-4xl font-bold mb-6 gradient-text">
            Our Neural Based Technology
          </h2>
          <p className="text-xl text-gray-300 mb-8">
            Advanced AI algorithms analyze and replicate the subtle timing variations that make human drumming feel natural and musical.
          </p>
          <button className="px-8 py-3 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-lg hover:from-purple-700 hover:to-blue-700 transition-colors">
            Learn More About Our Technology
          </button>
        </div>
      </section>

      {/* Pricing Tiers */}
      <section className="py-20 px-4">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-4xl font-bold text-center mb-12 gradient-text">
            Choose Your Plan
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {/* Basic Tier - FREE */}
            <div className="bg-white/5 backdrop-blur-md rounded-xl p-6 border border-gray-700">
              <div className="text-center mb-6">
                <Star className="h-12 w-12 text-blue-400 mx-auto mb-4" />
                <h3 className="text-2xl font-bold text-white mb-2">Basic</h3>
                <div className="text-3xl font-bold gradient-text mb-2">FREE</div>
                <p className="text-gray-400">Perfect for getting started</p>
              </div>
              <ul className="space-y-3 mb-6">
                <li className="flex items-center text-gray-300">
                  <CheckCircle className="h-5 w-5 text-green-400 mr-3" />
                  Basic drum pattern generation
                </li>
                <li className="flex items-center text-gray-300">
                  <CheckCircle className="h-5 w-5 text-green-400 mr-3" />
                  Standard audio quality
                </li>
                <li className="flex items-center text-gray-300">
                  <CheckCircle className="h-5 w-5 text-green-400 mr-3" />
                  5 tracks per month
                </li>
              </ul>
              <button 
                onClick={() => navigateTo && navigateTo('basic')}
                className="w-full px-6 py-3 bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-lg hover:from-blue-600 hover:to-blue-700 transition-colors"
              >
                Get Started Free
              </button>
            </div>

            {/* Advanced Tier */}
            <div className="bg-white/5 backdrop-blur-md rounded-xl p-6 border border-purple-500 relative">
              <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                <span className="bg-gradient-to-r from-purple-500 to-pink-500 text-white px-4 py-1 rounded-full text-sm font-semibold">
                  POPULAR
                </span>
              </div>
              <div className="text-center mb-6">
                <Zap className="h-12 w-12 text-purple-400 mx-auto mb-4" />
                <h3 className="text-2xl font-bold text-white mb-2">Advanced</h3>
                <div className="text-3xl font-bold gradient-text mb-2">$19/mo</div>
                <p className="text-gray-400">For serious musicians</p>
              </div>
              <ul className="space-y-3 mb-6">
                <li className="flex items-center text-gray-300">
                  <CheckCircle className="h-5 w-5 text-green-400 mr-3" />
                  Advanced neural processing
                </li>
                <li className="flex items-center text-gray-300">
                  <CheckCircle className="h-5 w-5 text-green-400 mr-3" />
                  High-quality audio output
                </li>
                <li className="flex items-center text-gray-300">
                  <CheckCircle className="h-5 w-5 text-green-400 mr-3" />
                  Unlimited tracks
                </li>
                <li className="flex items-center text-gray-300">
                  <CheckCircle className="h-5 w-5 text-green-400 mr-3" />
                  Custom drummer styles
                </li>
              </ul>
              <button 
                onClick={() => navigateTo && navigateTo('professional')}
                className="w-full px-6 py-3 bg-gradient-to-r from-purple-500 to-purple-600 text-white rounded-lg hover:from-purple-600 hover:to-purple-700 transition-colors"
              >
                Upgrade to Advanced
              </button>
            </div>

            {/* Professional Tier */}
            <div className="bg-white/5 backdrop-blur-md rounded-xl p-6 border border-gold-500">
              <div className="text-center mb-6">
                <Crown className="h-12 w-12 text-yellow-400 mx-auto mb-4" />
                <h3 className="text-2xl font-bold text-white mb-2">Professional</h3>
                <div className="text-3xl font-bold gradient-text-gold mb-2">$49/mo</div>
                <p className="text-gray-400">For professional studios</p>
              </div>
              <ul className="space-y-3 mb-6">
                <li className="flex items-center text-gray-300">
                  <CheckCircle className="h-5 w-5 text-green-400 mr-3" />
                  Professional studio quality
                </li>
                <li className="flex items-center text-gray-300">
                  <CheckCircle className="h-5 w-5 text-green-400 mr-3" />
                  AI drummer personalities
                </li>
                <li className="flex items-center text-gray-300">
                  <CheckCircle className="h-5 w-5 text-green-400 mr-3" />
                  Advanced mixing controls
                </li>
                <li className="flex items-center text-gray-300">
                  <CheckCircle className="h-5 w-5 text-green-400 mr-3" />
                  Priority support
                </li>
              </ul>
              <button 
                onClick={() => navigateTo && navigateTo('expert')}
                className="w-full px-6 py-3 bg-gradient-to-r from-yellow-500 to-orange-500 text-white rounded-lg hover:from-yellow-600 hover:to-orange-600 transition-colors"
              >
                Go Professional
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* AI Assistant Section */}
      <section className="py-20 px-4">
        <div className="max-w-4xl mx-auto">
          <div className="bg-white/5 backdrop-blur-md rounded-xl p-8 text-center">
            <h2 className="text-3xl font-bold text-white mb-4">
              Need Help? Chat with Our AI Assistant
            </h2>
            <p className="text-gray-300 mb-6">
              Get instant answers about drum creation, mixing techniques, and more from our intelligent assistant.
            </p>
            <button className="px-8 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg hover:from-blue-700 hover:to-purple-700 transition-colors">
              Start Chatting
            </button>
          </div>
        </div>
      </section>
    </div>
  );
};

export default LandingPage;
