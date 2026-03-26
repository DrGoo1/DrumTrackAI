import React, { useState, useEffect } from 'react';
import { 
  Music, Star, Zap, Upload, Play, CheckCircle, ArrowRight, 
  Brain, AudioWaveform, Database, Crown, Shield, Sparkles,
  Users, TrendingUp, Award, Target, Headphones, Mic
} from 'lucide-react';
import LandingPage from './pages/LandingPage';
import TierComparison from './pages/TierComparison';
import BasicTier from './pages/BasicTier';
import ProfessionalTier from './pages/ProfessionalTier';
import ExpertTier from './pages/ExpertTier';
import SectionPlaybackDemo from './pages/SectionPlaybackDemo';
import './App.css';

function App() {
  // Check URL parameter for initial page
  const urlParams = new URLSearchParams(window.location.search);
  const initialPage = urlParams.get('page') || 'landing';
  
  const [currentPage, setCurrentPage] = useState(initialPage);
  const [selectedTier, setSelectedTier] = useState(null);

  // Navigation handler
  const navigateTo = (page, tier = null) => {
    setCurrentPage(page);
    if (tier) setSelectedTier(tier);
    // Update URL
    window.history.pushState({}, '', `?page=${page}`);
  };

  // Tier data structure
  const tiers = {
    basic: {
      name: 'Basic',
      icon: Star,
      color: 'blue',
      price: '$9.99',
      period: '/month',
      description: 'Perfect for individual drummers and music students',
      features: [
        'Individual drum file analysis',
        'Basic pattern recognition',
        'Tempo and rhythm detection',
        'Simple beat matching',
        'Audio visualization',
        '10 analyses per month',
        'Standard support'
      ],
      capabilities: {
        sophistication: '65%',
        accuracy: '85%',
        processing: 'Standard',
        fileTypes: 'WAV, MP3',
        maxFileSize: '50MB',
        analysisTime: '30-60 seconds'
      }
    },
    professional: {
      name: 'Professional',
      icon: Zap,
      color: 'purple',
      price: '$29.99',
      period: '/month',
      description: 'Advanced analysis for producers and music professionals',
      features: [
        'Batch processing (up to 50 files)',
        'Advanced pattern analysis',
        'Signature song database access',
        'Real-time monitoring',
        'Professional visualizations',
        'Export capabilities',
        'Priority support',
        'API access'
      ],
      capabilities: {
        sophistication: '82%',
        accuracy: '91%',
        processing: 'Advanced',
        fileTypes: 'WAV, MP3, FLAC, M4A',
        maxFileSize: '200MB',
        analysisTime: '15-30 seconds'
      }
    },
    expert: {
      name: 'Expert',
      icon: Crown,
      color: 'gold',
      price: '$79.99',
      period: '/month',
      description: 'Ultimate AI-powered drum analysis with MVSep integration',
      features: [
        'Unlimited batch processing',
        'MVSep stem separation',
        'Expert Model (88.7% sophistication)',
        'Full song analysis',
        'Signature drummer recognition',
        'Custom model training',
        'White-label solutions',
        'Dedicated support'
      ],
      capabilities: {
        sophistication: '88.7%',
        accuracy: '94%',
        processing: 'Expert AI',
        fileTypes: 'All formats',
        maxFileSize: 'Unlimited',
        analysisTime: '5-15 seconds'
      }
    }
  };

  const renderPage = () => {
    switch (currentPage) {
      case 'landing':
        return <LandingPage tiers={tiers} navigateTo={navigateTo} />;
      case 'comparison':
        return <TierComparison tiers={tiers} navigateTo={navigateTo} />;
      case 'basic':
        return <BasicTier tier={tiers.basic} navigateTo={navigateTo} />;
      case 'professional':
        return <ProfessionalTier tier={tiers.professional} navigateTo={navigateTo} />;
      case 'expert':
        return <ExpertTier tier={tiers.expert} navigateTo={navigateTo} />;
      case 'section-player':
        return <SectionPlaybackDemo />;
      default:
        return <LandingPage tiers={tiers} navigateTo={navigateTo} />;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Navigation Header */}
      <header className="bg-gradient-to-r from-purple-900 to-indigo-900 shadow-lg sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-0.5">
            <div 
              className="flex items-center cursor-pointer"
              onClick={() => navigateTo('landing')}
            >
              <div className="w-48 h-48 bg-white rounded-2xl flex items-center justify-center overflow-hidden shadow-lg">
                <img 
                  src="/images/drumtrackai-logo.png" 
                  alt="DrumTracKAI Logo" 
                  className="w-full h-full object-contain p-2"
                />
              </div>
            </div>
            
            <div className="hidden md:flex items-center gap-6">
              <button 
                onClick={() => navigateTo('landing')}
                className={`text-sm transition-colors ${
                  currentPage === 'landing' ? 'text-white' : 'text-gray-300 hover:text-white'
                }`}
              >
                Home
              </button>
              <button 
                onClick={() => navigateTo('comparison')}
                className={`text-sm transition-colors ${
                  currentPage === 'comparison' ? 'text-white' : 'text-gray-300 hover:text-white'
                }`}
              >
                Pricing
              </button>
              <button 
                onClick={() => navigateTo('section-player')}
                className={`text-sm transition-colors ${
                  currentPage === 'section-player' ? 'text-white' : 'text-gray-300 hover:text-white'
                }`}
              >
                Section Player
              </button>
              <div className="flex items-center gap-3">
                <button 
                  className="px-4 py-2 text-sm text-white border border-white/20 rounded-lg hover:bg-white/10 transition-all"
                >
                  Log In
                </button>
                <button 
                  className="px-4 py-2 text-sm bg-gradient-to-r from-purple-600 to-purple-700 text-white rounded-lg hover:from-purple-700 hover:to-purple-800 transition-all"
                >
                  Sign Up
                </button>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main>
        {renderPage()}
      </main>

      {/* Footer */}
      <footer className="bg-black/40 backdrop-blur-md border-t border-white/10 mt-16">
        <div className="container mx-auto px-4 py-8">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <Music className="h-6 w-6 text-purple-400" />
                <span className="text-white font-bold">DrumTracKAI</span>
              </div>
              <p className="text-gray-400 text-sm">
                Professional AI-powered drum analysis with advanced neural network sophistication.
              </p>
            </div>
            
            <div>
              <h3 className="text-white font-semibold mb-3">Services</h3>
              <ul className="space-y-2 text-sm text-gray-400">
                <li>Drum Pattern Analysis</li>
                <li>Stem Separation</li>
                <li>Batch Processing</li>
                <li>Real-time Monitoring</li>
              </ul>
            </div>
            
            <div>
              <h3 className="text-white font-semibold mb-3">Features</h3>
              <ul className="space-y-2 text-sm text-gray-400">
                <li>Expert Model (88.7%)</li>
                <li>Neural Processing</li>
                <li>Signature Songs</li>
                <li>Professional Analysis</li>
              </ul>
            </div>
            
            <div>
              <h3 className="text-white font-semibold mb-3">Support</h3>
              <ul className="space-y-2 text-sm text-gray-400">
                <li>Documentation</li>
                <li>API Reference</li>
                <li>Community</li>
                <li>Contact</li>
              </ul>
            </div>
          </div>
          
          <div className="border-t border-white/10 mt-8 pt-6 text-center">
            <p className="text-gray-400 text-sm">
              © 2025 DrumTracKAI. Professional drum analysis powered by AI.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
