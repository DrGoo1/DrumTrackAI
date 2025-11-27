import React, { useState } from 'react';
import { 
  Star, Zap, Crown, CheckCircle, X, ArrowRight, 
  Brain, AudioWaveform, Database, Upload, Clock, Shield,
  Users, TrendingUp, Award, Target, Headphones, Mic
} from 'lucide-react';

const TierComparison = ({ tiers, navigateTo }) => {
  const [selectedTier, setSelectedTier] = useState('professional');

  const comparisonFeatures = [
    {
      category: "Analysis Capabilities",
      features: [
        {
          name: "AI Sophistication Level",
          basic: "65% - Standard Recognition",
          professional: "82% - Advanced Analysis",
          expert: "88.7% - Expert Model"
        },
        {
          name: "Pattern Recognition",
          basic: "Basic patterns only",
          professional: "Advanced patterns + styles",
          expert: "Signature drummer recognition"
        },
        {
          name: "Tempo & Rhythm Analysis",
          basic: true,
          professional: true,
          expert: true
        },
        {
          name: "Spectral Analysis",
          basic: "Basic frequency analysis",
          professional: "Advanced spectral features",
          expert: "Professional-grade analysis"
        },
        {
          name: "Real-time Processing",
          basic: false,
          professional: true,
          expert: true
        }
      ]
    },
    {
      category: "Audio Processing",
      features: [
        {
          name: "File Formats Supported",
          basic: "WAV, MP3",
          professional: "WAV, MP3, FLAC, M4A",
          expert: "All formats + custom"
        },
        {
          name: "Maximum File Size",
          basic: "50MB",
          professional: "200MB",
          expert: "Unlimited"
        },
        {
          name: "Batch Processing",
          basic: false,
          professional: "Up to 50 files",
          expert: "Unlimited batches"
        },
        {
          name: "MVSep Stem Separation",
          basic: false,
          professional: false,
          expert: "HDemucs + DrumSep pipeline"
        },
        {
          name: "Processing Speed",
          basic: "30-60 seconds",
          professional: "15-30 seconds",
          expert: "5-15 seconds"
        }
      ]
    },
    {
      category: "Database Access",
      features: [
        {
          name: "Classic Drum Beats",
          basic: "10 tracks",
          professional: "40 classic tracks",
          expert: "Full database + custom"
        },
        {
          name: "Signature Songs",
          basic: false,
          professional: "Limited access",
          expert: "Full signature database"
        },
        {
          name: "SD3 Samples",
          basic: false,
          professional: "500+ samples",
          expert: "Full 1,200+ collection"
        },
        {
          name: "Training Data Access",
          basic: false,
          professional: false,
          expert: "5,650+ training files"
        }
      ]
    },
    {
      category: "Features & Tools",
      features: [
        {
          name: "Audio Visualization",
          basic: "2D waveforms",
          professional: "3D visualizations",
          expert: "Professional exports"
        },
        {
          name: "Export Capabilities",
          basic: "Basic JSON",
          professional: "JSON + visualizations",
          expert: "All formats + API"
        },
        {
          name: "Real-time Monitoring",
          basic: false,
          professional: true,
          expert: true
        },
        {
          name: "API Access",
          basic: false,
          professional: "Limited API",
          expert: "Full API + webhooks"
        },
        {
          name: "Custom Model Training",
          basic: false,
          professional: false,
          expert: true
        }
      ]
    },
    {
      category: "Support & Service",
      features: [
        {
          name: "Support Level",
          basic: "Community support",
          professional: "Priority support",
          expert: "Dedicated support"
        },
        {
          name: "Response Time",
          basic: "48-72 hours",
          professional: "24 hours",
          expert: "4-8 hours"
        },
        {
          name: "Documentation",
          basic: "Basic guides",
          professional: "Advanced docs",
          expert: "Complete documentation"
        },
        {
          name: "White-label Solutions",
          basic: false,
          professional: false,
          expert: true
        }
      ]
    }
  ];

  const renderFeatureValue = (feature, tier) => {
    const value = feature[tier];
    
    if (typeof value === 'boolean') {
      return value ? (
        <CheckCircle className="h-5 w-5 text-green-400 mx-auto" />
      ) : (
        <X className="h-5 w-5 text-gray-500 mx-auto" />
      );
    }
    
    return (
      <span className={`text-sm ${
        tier === 'expert' ? 'text-yellow-400 font-semibold' : 
        tier === 'professional' ? 'text-purple-400' : 'text-blue-400'
      }`}>
        {value}
      </span>
    );
  };

  const getTierColor = (tier) => {
    const colors = {
      basic: 'blue',
      professional: 'purple', 
      expert: 'gold'
    };
    return colors[tier];
  };

  const getTierColorClasses = (tier) => {
    const classes = {
      basic: 'from-blue-500 to-blue-600 border-blue-500/50',
      professional: 'from-purple-500 to-purple-600 border-purple-500/50',
      expert: 'from-yellow-500 to-orange-500 border-yellow-500/50'
    };
    return classes[tier];
  };

  return (
    <div className="min-h-screen py-20">
      <div className="container mx-auto px-4">
        {/* Header */}
        <div className="text-center mb-16">
          <h1 className="text-4xl md:text-6xl font-bold text-white mb-6">
            Choose Your 
            <span className="bg-gradient-to-r from-purple-400 to-gold-400 bg-clip-text text-transparent"> Perfect Plan</span>
          </h1>
          <p className="text-xl text-gray-300 max-w-3xl mx-auto">
            From basic drum analysis to expert-level AI processing with MVSep integration. 
            Find the tier that matches your professional needs.
          </p>
        </div>

        {/* Tier Cards */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-16">
          {Object.entries(tiers).map(([key, tier]) => {
            const Icon = tier.icon;
            const isPopular = key === 'professional';
            const colorClasses = getTierColorClasses(key);

            return (
              <div key={key} className={`relative bg-white/5 backdrop-blur-md rounded-2xl p-8 border-2 ${colorClasses} hover:bg-white/10 transition-all duration-300 transform hover:scale-105 ${isPopular ? 'lg:scale-110' : ''}`}>
                {isPopular && (
                  <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                    <div className="bg-gradient-to-r from-purple-500 to-purple-600 text-white px-4 py-2 rounded-full text-sm font-semibold">
                      Most Popular
                    </div>
                  </div>
                )}
                
                <div className="text-center mb-8">
                  <div className={`w-20 h-20 bg-gradient-to-r ${colorClasses.split(' ')[0]} ${colorClasses.split(' ')[1]} rounded-2xl flex items-center justify-center mx-auto mb-6`}>
                    <Icon className="h-10 w-10 text-white" />
                  </div>
                  <h3 className="text-3xl font-bold text-white mb-4">{tier.name}</h3>
                  <div className="text-4xl font-bold text-white mb-2">
                    {tier.price}
                    <span className="text-lg text-gray-400">{tier.period}</span>
                  </div>
                  <p className="text-gray-400 mb-6">{tier.description}</p>
                  
                  <div className="grid grid-cols-2 gap-4 mb-6 text-sm">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-white">{tier.capabilities.sophistication}</div>
                      <div className="text-gray-400">Sophistication</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-white">{tier.capabilities.accuracy}</div>
                      <div className="text-gray-400">Accuracy</div>
                    </div>
                  </div>
                </div>

                <div className="space-y-3 mb-8">
                  {tier.features.map((feature, index) => (
                    <div key={index} className="flex items-start gap-3">
                      <CheckCircle className="h-5 w-5 text-green-400 flex-shrink-0 mt-0.5" />
                      <span className="text-gray-300 text-sm">{feature}</span>
                    </div>
                  ))}
                </div>

                <button 
                  onClick={() => navigateTo(key)}
                  className={`w-full py-4 bg-gradient-to-r ${colorClasses.split(' ')[0]} ${colorClasses.split(' ')[1]} text-white rounded-xl font-semibold hover:opacity-90 transition-all flex items-center justify-center gap-2 text-lg`}
                >
                  Get Started
                  <ArrowRight className="h-5 w-5" />
                </button>
              </div>
            );
          })}
        </div>

        {/* Detailed Comparison Table */}
        <div className="bg-white/5 backdrop-blur-md rounded-2xl p-8">
          <h2 className="text-3xl font-bold text-white mb-8 text-center">
            Detailed Feature Comparison
          </h2>
          
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/20">
                  <th className="text-left py-4 px-4 text-white font-semibold">Features</th>
                  <th className="text-center py-4 px-4 text-blue-400 font-semibold">Basic</th>
                  <th className="text-center py-4 px-4 text-purple-400 font-semibold">Professional</th>
                  <th className="text-center py-4 px-4 text-yellow-400 font-semibold">Expert</th>
                </tr>
              </thead>
              <tbody>
                {comparisonFeatures.map((category, categoryIndex) => (
                  <React.Fragment key={categoryIndex}>
                    <tr>
                      <td colSpan="4" className="py-6">
                        <h3 className="text-xl font-semibold text-white">{category.category}</h3>
                      </td>
                    </tr>
                    {category.features.map((feature, featureIndex) => (
                      <tr key={featureIndex} className="border-b border-white/10 hover:bg-white/5">
                        <td className="py-4 px-4 text-gray-300">{feature.name}</td>
                        <td className="py-4 px-4 text-center">
                          {renderFeatureValue(feature, 'basic')}
                        </td>
                        <td className="py-4 px-4 text-center">
                          {renderFeatureValue(feature, 'professional')}
                        </td>
                        <td className="py-4 px-4 text-center">
                          {renderFeatureValue(feature, 'expert')}
                        </td>
                      </tr>
                    ))}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* FAQ Section */}
        <div className="mt-16">
          <h2 className="text-3xl font-bold text-white mb-8 text-center">
            Frequently Asked Questions
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="bg-white/5 backdrop-blur-md rounded-xl p-6">
              <h3 className="text-xl font-semibold text-white mb-3">
                What makes the Expert tier special?
              </h3>
              <p className="text-gray-400">
                The Expert tier features our advanced AI model with 88.7% sophistication, 
                MVSep stem separation, and access to signature drummer analysis including 
                Jeff Porcaro, Neil Peart, and Stewart Copeland.
              </p>
            </div>
            
            <div className="bg-white/5 backdrop-blur-md rounded-xl p-6">
              <h3 className="text-xl font-semibold text-white mb-3">
                Can I upgrade or downgrade my plan?
              </h3>
              <p className="text-gray-400">
                Yes! You can change your plan at any time. Upgrades take effect immediately, 
                and downgrades take effect at your next billing cycle.
              </p>
            </div>
            
            <div className="bg-white/5 backdrop-blur-md rounded-xl p-6">
              <h3 className="text-xl font-semibold text-white mb-3">
                What is MVSep integration?
              </h3>
              <p className="text-gray-400">
                MVSep is our professional stem separation technology that uses HDemucs and 
                DrumSep models to isolate drum tracks from full songs for precise analysis.
              </p>
            </div>
            
            <div className="bg-white/5 backdrop-blur-md rounded-xl p-6">
              <h3 className="text-xl font-semibold text-white mb-3">
                Is there a free trial available?
              </h3>
              <p className="text-gray-400">
                We offer a 7-day free trial for all tiers so you can experience the full 
                power of DrumTracKAI before committing to a subscription.
              </p>
            </div>
          </div>
        </div>

        {/* CTA Section */}
        <div className="text-center mt-16">
          <h2 className="text-3xl font-bold text-white mb-6">
            Ready to Start Your Drum Analysis Journey?
          </h2>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <button 
              onClick={() => navigateTo('basic')}
              className="px-8 py-4 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-700 transition-all transform hover:scale-105 flex items-center justify-center gap-2"
            >
              <Star className="h-5 w-5" />
              Start with Basic
            </button>
            <button 
              onClick={() => navigateTo('expert')}
              className="px-8 py-4 bg-gradient-to-r from-yellow-500 to-orange-500 text-white rounded-xl font-semibold hover:from-yellow-600 hover:to-orange-600 transition-all transform hover:scale-105 flex items-center justify-center gap-2"
            >
              <Crown className="h-5 w-5" />
              Go Expert
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TierComparison;
