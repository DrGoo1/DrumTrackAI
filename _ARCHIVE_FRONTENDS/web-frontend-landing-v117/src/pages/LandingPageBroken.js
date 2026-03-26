import React, { useState } from 'react';
import { 
  Play, CheckCircle, ArrowRight, Star, Zap, Crown
} from 'lucide-react';

const LandingPage = ({ tiers, navigateTo }) => {
  const [currentDemo, setCurrentDemo] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [animationTime, setAnimationTime] = useState(0);

  const demoTracks = [
    { name: "Jeff Porcaro - Rosanna", sophistication: "92%", complexity: "Expert" },
    { name: "Neil Peart - Tom Sawyer", sophistication: "89%", complexity: "Master" },
    { name: "Stewart Copeland - Roxanne", sophistication: "87%", complexity: "Professional" }
  ];

  const features = [
    {
      icon: Brain,
      title: "Expert AI Model",
      description: "88.7% sophistication score with advanced pattern recognition",
      color: "purple"
    },
    {
      icon: AudioWaveform,
      title: "MVSep Integration",
      description: "Professional stem separation with HDemucs + DrumSep pipeline",
      color: "blue"
    },
    {
      icon: Database,
      title: "Signature Songs",
      description: "Analyze legendary drummers: Porcaro, Peart, Copeland",
      color: "green"
    },
    {
      icon: Target,
      title: "Real-time Analysis",
      description: "Live progress monitoring with 1-second update intervals",
      color: "orange"
    }
  ];

  const stats = [
    { number: "88.7%", label: "AI Sophistication", icon: Brain },
    { number: "5,650+", label: "Training Files", icon: Database },
    { number: "94%", label: "Accuracy Rate", icon: Target },
    { number: "500+", label: "SD3 Samples", icon: Music }
  ];

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentDemo((prev) => (prev + 1) % demoTracks.length);
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  // Animation timer for smooth waveform
  useEffect(() => {
    let animationFrame;
    const animate = () => {
      setAnimationTime(Date.now());
      animationFrame = requestAnimationFrame(animate);
    };
    if (isPlaying) {
      animate();
    }
    return () => {
      if (animationFrame) {
        cancelAnimationFrame(animationFrame);
      }
    };
  }, [isPlaying]);

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <div className="min-h-screen pt-24 relative overflow-hidden">
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
                  className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
                >
                  <Play className="h-4 w-4" />
                  {isPlaying ? 'Pause' : 'Play'}
                </button>
              </div>
              
              <div className="text-left">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-gray-300">{demoTracks[currentDemo].name}</span>
                  <span className="text-purple-400 font-semibold">{demoTracks[currentDemo].sophistication}</span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2 mb-2">
                  <div className="bg-gradient-to-r from-purple-500 to-gold-500 h-2 rounded-full w-3/4 transition-all duration-1000"></div>
                </div>
                <div className="flex justify-between text-sm text-gray-400">
                  <span>Complexity: {demoTracks[currentDemo].complexity}</span>
                  <span>Expert Model Active</span>
                </div>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <button 
                onClick={() => navigateTo('comparison')}
                className="px-8 py-4 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-xl font-semibold hover:from-purple-700 hover:to-blue-700 transition-all transform hover:scale-105 flex items-center justify-center gap-2"
              >
                View Pricing Plans
                <ArrowRight className="h-5 w-5" />
              </button>
              <button 
                onClick={() => navigateTo('expert')}
                className="px-8 py-4 bg-gradient-to-r from-yellow-500 to-orange-500 text-white rounded-xl font-semibold hover:from-yellow-600 hover:to-orange-600 transition-all transform hover:scale-105 flex items-center justify-center gap-2"
              >
                <Crown className="h-5 w-5" />
                Try Expert Tier
              </button>
            </div>

            {/* Before/After Audio Comparison */}
            <div className="mt-16 pt-16 border-t border-white/10">
              <div className="text-center mb-12">
                <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
                  Hear the <span className="bg-gradient-to-r from-orange-400 to-orange-500 bg-clip-text text-transparent">Human Difference</span>
                </h2>
                <p className="text-xl text-gray-300 max-w-3xl mx-auto">
                  Compare robotic, algorithmic drums with our neural entrainment technology that creates truly human-feeling rhythms.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
                {/* Before - Robotic */}
                <div className="bg-red-900/20 backdrop-blur-md rounded-2xl p-6 border border-red-500/30">
                  <div className="text-center mb-4">
                    <div className="w-12 h-12 bg-red-500/20 rounded-xl flex items-center justify-center mx-auto mb-3">
                      <Target className="h-6 w-6 text-red-400" />
                    </div>
                    <h3 className="text-xl font-semibold text-white mb-2">Before: Algorithmic Drums</h3>
                    <p className="text-gray-400 text-sm">Perfectly quantized, mathematically precise</p>
                  </div>
                  
                  {/* Robotic Waveform */}
                  <div className="relative w-full h-24 bg-black/30 rounded-lg overflow-hidden mb-4">
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="flex items-end gap-1 h-16">
                        {Array.from({ length: 16 }, (_, i) => (
                          <div
                            key={i}
                            className="w-3 bg-red-400 rounded-t"
                            style={{ height: i % 4 === 0 ? '40px' : '20px' }}
                          />
                        ))}
                      </div>
                    </div>
                    <div className="absolute bottom-1 left-2 text-xs text-gray-500">
                      Rigid • Mechanical • Predictable
                    </div>
                  </div>
                  
                  <button className="w-full py-2 bg-red-600/20 border border-red-500/50 text-red-300 rounded-lg hover:bg-red-600/30 transition-colors flex items-center justify-center gap-2">
                    <Play className="h-4 w-4" />
                    Play Robotic Version
                  </button>
                </div>

                {/* After - Human-like */}
                <div className="bg-green-900/20 backdrop-blur-md rounded-2xl p-6 border border-green-500/30">
                  <div className="text-center mb-4">
                    <div className="w-12 h-12 bg-green-500/20 rounded-xl flex items-center justify-center mx-auto mb-3">
                      <Brain className="h-6 w-6 text-green-400" />
                    </div>
                    <h3 className="text-xl font-semibold text-white mb-2">After: Neural Entrainment</h3>
                    <p className="text-gray-400 text-sm">Human-like timing, natural feel</p>
                  </div>
                  
                  {/* Human-like Waveform */}
                  <div className="relative w-full h-24 bg-black/30 rounded-lg overflow-hidden mb-4">
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="flex items-end gap-1 h-16">
                        {Array.from({ length: 16 }, (_, i) => {
                          const variation = Math.sin(i * 0.8) * 5;
                          const baseHeight = i % 4 === 0 ? 40 : 20;
                          return (
                            <div
                              key={i}
                              className="w-3 bg-green-400 rounded-t"
                              style={{ height: `${baseHeight + variation}px` }}
                            />
                          );
                        })}
                      </div>
                    </div>
                    <div className="absolute bottom-1 left-2 text-xs text-gray-500">
                      Natural • Organic • Human Feel
                    </div>
                  </div>
                  
                  <button className="w-full py-2 bg-green-600/20 border border-green-500/50 text-green-300 rounded-lg hover:bg-green-600/30 transition-colors flex items-center justify-center gap-2">
                    <Play className="h-4 w-4" />
                    Play Human-like Version
                  </button>
                </div>
              </div>

              {/* Neural Entrainment Link */}
              <div className="text-center mt-8">
                <button className="inline-flex items-center gap-2 px-6 py-3 bg-purple-600/20 border border-purple-500/50 text-purple-300 rounded-lg hover:bg-purple-600/30 transition-colors">
                  <Brain className="h-5 w-5" />
                  Learn About Neural Entrainment Science
                  <ArrowRight className="h-4 w-4" />
                </button>
              </div>
            </div>

            {/* Claude AI Integration Section */}
            <div className="mt-16 pt-16 border-t border-white/10">
              <div className="bg-gradient-to-r from-blue-900/20 to-purple-900/20 backdrop-blur-md rounded-2xl p-6 md:p-8 border border-blue-500/30">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
                  {/* Left Side - Claude Info */}
                  <div>
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-12 h-12 bg-blue-500/20 rounded-xl flex items-center justify-center">
                        <MessageCircle className="h-6 w-6 text-blue-400" />
                      </div>
                      <div>
                        <h3 className="text-xl font-semibold text-white">Claude AI Assistant</h3>
                        <p className="text-blue-300 text-sm">Available 24/7</p>
                      </div>
                    </div>
                    <p className="text-gray-300 mb-4">
                      Get instant help with drum creation, neural entrainment questions, and technical support from our Claude AI assistant.
                    </p>
                    <div className="flex flex-wrap gap-2 text-xs text-gray-400 mb-4">
                      <span className="bg-blue-500/20 px-2 py-1 rounded">Drum Theory</span>
                      <span className="bg-purple-500/20 px-2 py-1 rounded">Neural Science</span>
                      <span className="bg-green-500/20 px-2 py-1 rounded">Technical Support</span>
                    </div>
                  </div>
                  
                  {/* Right Side - Chat Button */}
                  <div className="text-center md:text-right">
                    <button className="w-full md:w-auto px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-xl font-semibold hover:from-blue-700 hover:to-purple-700 transition-all transform hover:scale-105 flex items-center justify-center gap-2 shadow-lg">
                      <MessageCircle className="h-5 w-5" />
                      Chat with Claude AI
                    </button>
                    <p className="text-xs text-gray-400 mt-2">
                      Powered by Anthropic's Claude
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-16 bg-black/20 backdrop-blur-md">
        <div className="container mx-auto px-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {stats.map((stat, index) => {
              const Icon = stat.icon;
              return (
                <div key={index} className="text-center">
                  <div className="w-16 h-16 bg-gradient-to-r from-purple-500/20 to-blue-500/20 rounded-2xl flex items-center justify-center mx-auto mb-4">
                    <Icon className="h-8 w-8 text-purple-400" />
                  </div>
                  <div className="text-3xl font-bold text-white mb-2">{stat.number}</div>
                  <div className="text-gray-400">{stat.label}</div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-white mb-6">
              Powered by Advanced AI Technology
            </h2>
            <p className="text-xl text-gray-300 max-w-3xl mx-auto">
              Our Expert Model combines cutting-edge machine learning with professional audio analysis 
              to deliver unprecedented drum pattern recognition and analysis capabilities.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature, index) => {
              const Icon = feature.icon;
              const colorClasses = {
                purple: 'from-purple-500 to-purple-600',
                blue: 'from-blue-500 to-blue-600',
                green: 'from-green-500 to-green-600',
                orange: 'from-orange-500 to-orange-600'
              };

              return (
                <div key={index} className="bg-white/5 backdrop-blur-md rounded-2xl p-6 hover:bg-white/10 transition-all duration-300 transform hover:scale-105">
                  <div className={`w-12 h-12 bg-gradient-to-r ${colorClasses[feature.color]} rounded-xl flex items-center justify-center mb-4`}>
                    <Icon className="h-6 w-6 text-white" />
                  </div>
                  <h3 className="text-xl font-semibold text-white mb-3">{feature.title}</h3>
                  <p className="text-gray-400">{feature.description}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Tier Preview Section */}
      <section className="py-20 bg-black/20 backdrop-blur-md">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-white mb-6">
              Choose Your Analysis Level
            </h2>
            <p className="text-xl text-gray-300 max-w-3xl mx-auto">
              From basic pattern recognition to expert-level signature song analysis, 
              we have the perfect tier for your drumming journey.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {Object.entries(tiers).map(([key, tier]) => {
              const Icon = tier.icon;
              const colorClasses = {
                blue: 'from-blue-500 to-blue-600 border-blue-500/50',
                purple: 'from-purple-500 to-purple-600 border-purple-500/50',
                gold: 'from-yellow-500 to-orange-500 border-yellow-500/50'
              };

              return (
                <div key={key} className={`bg-white/5 backdrop-blur-md rounded-2xl p-8 border-2 ${colorClasses[tier.color]} hover:bg-white/10 transition-all duration-300 transform hover:scale-105`}>
                  <div className="text-center mb-6">
                    <div className={`w-16 h-16 bg-gradient-to-r ${colorClasses[tier.color].split(' ')[0]} ${colorClasses[tier.color].split(' ')[1]} rounded-2xl flex items-center justify-center mx-auto mb-4`}>
                      <Icon className="h-8 w-8 text-white" />
                    </div>
                    <h3 className="text-2xl font-bold text-white mb-2">{tier.name}</h3>
                    <div className="text-3xl font-bold text-white mb-2">
                      {tier.price}
                      <span className="text-lg text-gray-400">{tier.period}</span>
                    </div>
                    <p className="text-gray-400">{tier.description}</p>
                  </div>

                  <div className="space-y-3 mb-8">
                    {tier.features.slice(0, 4).map((feature, index) => (
                      <div key={index} className="flex items-center gap-3">
                        <CheckCircle className="h-5 w-5 text-green-400 flex-shrink-0" />
                        <span className="text-gray-300">{feature}</span>
                      </div>
                    ))}
                    {tier.features.length > 4 && (
                      <div className="text-gray-400 text-sm">
                        +{tier.features.length - 4} more features
                      </div>
                    )}
                  </div>

                  <button 
                    onClick={() => navigateTo(key)}
                    className={`w-full py-3 bg-gradient-to-r ${colorClasses[tier.color].split(' ')[0]} ${colorClasses[tier.color].split(' ')[1]} text-white rounded-xl font-semibold hover:opacity-90 transition-all flex items-center justify-center gap-2`}
                  >
                    Get Started
                    <ArrowRight className="h-4 w-4" />
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20">
        <div className="container mx-auto px-4 text-center">
          <div className="max-w-4xl mx-auto">
            <h2 className="text-4xl font-bold text-white mb-6">
              Ready to Create Human-Like Drums?
            </h2>
            <p className="text-xl text-gray-300 mb-8">
              Join thousands of musicians, producers, and drum enthusiasts who trust DrumTracKAI 
              for cutting-edge AI drum creation that feels authentically human.
            </p>
            
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <button 
                onClick={() => navigateTo('comparison')}
                className="px-8 py-4 bg-gradient-to-r from-orange-500 to-orange-600 text-white rounded-xl font-semibold hover:from-orange-600 hover:to-orange-700 transition-all transform hover:scale-105 flex items-center justify-center gap-2"
              >
                <Star className="h-5 w-5" />
                View Pricing Tiers
              </button>
              <div className="flex justify-center mb-12">
              <button 
                onClick={() => navigateTo('expert')}
                className="px-8 py-4 bg-purple-600 text-white rounded-xl font-semibold hover:bg-purple-700 transition-all transform hover:scale-105 flex items-center justify-center gap-2"
              >
                <Play className="h-5 w-5" />
                Start Creating
              </button>
            </div>
            </div>

            {/* Features Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 items-center">
              {/* Left Side - Features */}
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <div className="w-3 h-3 bg-gradient-to-r from-purple-400 to-purple-500 rounded-full flex-shrink-0"></div>
                  <span className="text-gray-300">Instrument-specific timing intelligence</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-3 h-3 bg-gradient-to-r from-purple-400 to-purple-500 rounded-full flex-shrink-0"></div>
                  <span className="text-gray-300">Tempo-aware timing that adapts like real drummers</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-3 h-3 bg-gradient-to-r from-purple-400 to-purple-500 rounded-full flex-shrink-0"></div>
                  <span className="text-gray-300">Genre-authentic grooves, not random variations</span>
                </div>
              </div>

              {/* Right Side - 3D Waveform Visualization */}
              <div className="bg-black/40 backdrop-blur-md rounded-2xl p-6 border border-purple-500/20">
                <div className="text-center mb-4">
                  <h3 className="text-white font-semibold mb-2">Real-Time Drum Pattern Visualization</h3>
                  <p className="text-gray-400 text-sm mb-4">Watch AI create human-like rhythms in real-time</p>
                </div>
                
                {/* Animated Waveform Display */}
                <div className="relative w-full h-48 bg-gradient-to-br from-purple-900/30 to-blue-900/30 rounded-xl overflow-hidden mb-4">
                  <div className="absolute inset-0 flex items-center justify-center">
                    {/* Animated Drum Waveform */}
                    <div className="flex items-end gap-1 h-32">
                      {Array.from({ length: 32 }, (_, i) => {
                        const height = isPlaying 
                          ? Math.sin((animationTime / 200 + i * 0.3)) * 20 + 30
                          : i % 4 === 0 ? 50 : i % 2 === 0 ? 30 : 20;
                        const color = i % 4 === 0 ? 'bg-orange-400' : i % 2 === 0 ? 'bg-purple-400' : 'bg-blue-400';
                        return (
                          <div
                            key={i}
                            className={`w-2 ${color} rounded-t transition-all duration-200`}
                            style={{ height: `${Math.max(height, 10)}px` }}
                          />
                        );
                      })}
                    </div>
                  </div>
                  
                  {/* Neural Network Overlay */}
                  <div className="absolute top-2 right-2">
                    <Brain className="h-6 w-6 text-purple-400 animate-pulse" />
                  </div>
                  
                  {/* BPM Display */}
                  <div className="absolute bottom-2 left-2 text-xs text-gray-400">
                    <span className="bg-black/50 px-2 py-1 rounded">120 BPM • Neural Processing</span>
                  </div>
                </div>
                
                {/* Play Controls */}
                <div className="flex items-center justify-center gap-3">
                  <button 
                    onClick={() => setIsPlaying(!isPlaying)}
                    className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
                  >
                    <Play className="h-4 w-4" />
                    {isPlaying ? 'Pause' : 'Play'} Demo
                  </button>
                  <div className="text-xs text-gray-400">
                    <span className="text-green-400">●</span> Live Neural Processing
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default LandingPage;
