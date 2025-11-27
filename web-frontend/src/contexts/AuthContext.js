import React, { createContext, useContext, useState } from 'react';

// Authentication Context
const AuthContext = createContext();

// Auth Provider Component
export const AuthProvider = ({ children }) => {
  // Auto-authenticate for development - bypass login requirement
  const [user, setUser] = useState({
    id: 1,
    email: 'dev@drumtrackai.com',
    name: 'Development User',
    tier: 'expert'
  });
  const [token, setToken] = useState('dev_token');
  const [isAuthenticated, setIsAuthenticated] = useState(true); // Auto-authenticated for dev
  const [isLoading, setIsLoading] = useState(false);
  const [tier, setTier] = useState('expert'); // Set to expert tier for full feature access
  const [usage, setUsage] = useState({ current: 5, limit: -1 }); // Unlimited usage for expert
  const [error, setError] = useState(null);

  const login = async (email, password) => {
    setIsLoading(true);
    setError(null);
    
    try {
      // Demo login for now
      const demoUser = { id: 1, email, name: 'Demo User', tier: 'expert' };
      const demoToken = 'demo_jwt_token';
      
      setUser(demoUser);
      setToken(demoToken);
      setIsAuthenticated(true);
      setTier(demoUser.tier);
      setUsage({ current: 15, limit: -1 });
      
      localStorage.setItem('drumtrackai_token', demoToken);
      
      setIsLoading(false);
      return { success: true };
    } catch (error) {
      const errorMessage = error.message || 'Login failed';
      setError(errorMessage);
      setIsLoading(false);
      return { success: false, error: errorMessage };
    }
  };

  const register = async (email, password, name) => {
    setIsLoading(true);
    setError(null);
    
    try {
      // Demo registration for now
      const demoUser = { id: 1, email, name, tier: 'basic' };
      const demoToken = 'demo_jwt_token';
      
      setUser(demoUser);
      setToken(demoToken);
      setIsAuthenticated(true);
      setTier(demoUser.tier);
      setUsage({ current: 0, limit: 10 });
      
      localStorage.setItem('drumtrackai_token', demoToken);
      
      setIsLoading(false);
      return { success: true };
    } catch (error) {
      const errorMessage = error.message || 'Registration failed';
      setError(errorMessage);
      setIsLoading(false);
      return { success: false, error: errorMessage };
    }
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    setIsAuthenticated(false);
    setTier('basic');
    setUsage({ current: 0, limit: 10 });
    setError(null);
    localStorage.removeItem('drumtrackai_token');
  };

  // Tier configurations with features and limits
  const getTierConfig = () => {
    const tierConfigs = {
      basic: {
        name: 'Basic',
        features: {
          supportedFormats: ['audio/wav', 'audio/mp3'],
          batchLimit: 1,
          maxFileSize: 50 * 1024 * 1024, // 50MB
          analysisTypes: ['pattern'],
          outputFormats: ['mp3']
        },
        limits: { daily: 10, monthly: 100 }
      },
      advanced: {
        name: 'Advanced', 
        features: {
          supportedFormats: ['audio/wav', 'audio/mp3', 'audio/flac'],
          batchLimit: 5,
          maxFileSize: 200 * 1024 * 1024, // 200MB
          analysisTypes: ['pattern', 'style'],
          outputFormats: ['mp3', 'wav']
        },
        limits: { daily: 50, monthly: 500 }
      },
      professional: {
        name: 'Professional',
        features: {
          supportedFormats: ['audio/wav', 'audio/mp3', 'audio/flac', 'audio/aiff'],
          batchLimit: 20,
          maxFileSize: 500 * 1024 * 1024, // 500MB
          analysisTypes: ['pattern', 'style', 'advanced'],
          outputFormats: ['mp3', 'wav', 'midi']
        },
        limits: { daily: -1, monthly: -1 } // unlimited
      },
      expert: {
        name: 'Expert',
        features: {
          supportedFormats: [], // all formats
          batchLimit: -1, // unlimited
          maxFileSize: 1024 * 1024 * 1024, // 1GB
          analysisTypes: ['pattern', 'style', 'advanced', 'expert'],
          outputFormats: ['mp3', 'wav', 'midi', 'stems']
        },
        limits: { daily: -1, monthly: -1 } // unlimited
      }
    };
    
    return tierConfigs[tier] || tierConfigs.basic;
  };

  // Check if user has remaining usage based on tier limits
  const hasUsageRemaining = () => {
    const config = getTierConfig();
    
    // Unlimited tiers (Professional and Expert)
    if (config.limits.daily === -1) {
      return true;
    }
    
    // Check daily limit
    return usage.current < config.limits.daily;
  };

  // Get upgrade target for current user
  const getUpgradeTarget = () => {
    const tierOrder = ['basic', 'advanced', 'professional', 'expert'];
    const currentIndex = tierOrder.indexOf(tier);
    return currentIndex < tierOrder.length - 1 ? tierOrder[currentIndex + 1] : null;
  };

  // Update usage after successful generation
  const updateUsage = (increment = 1) => {
    setUsage(prev => ({
      ...prev,
      current: prev.current + increment
    }));
  };

  // Tier-based feature access control
  const canUseFeature = (feature) => {
    const tierFeatures = {
      basic: ['upload', 'basic_generation'],
      advanced: ['upload', 'basic_generation', 'mp3_upload', 'advanced_generation', 'batchProcessing'],
      professional: ['upload', 'basic_generation', 'mp3_upload', 'advanced_generation', 'unlimited_generation', 'stem_separation', 'batchProcessing'],
      expert: ['upload', 'basic_generation', 'mp3_upload', 'advanced_generation', 'unlimited_generation', 'stem_separation', 'expert_model', 'batchProcessing']
    };
    
    return tierFeatures[tier]?.includes(feature) || false;
  };

  const contextValue = {
    user,
    token,
    isAuthenticated,
    isLoading,
    tier,
    tierConfig: getTierConfig(),
    usage,
    error,
    login,
    register,
    logout,
    canUseFeature,
    hasUsageRemaining,
    getUpgradeTarget,
    updateUsage
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};

// Hook to use auth context
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext;
