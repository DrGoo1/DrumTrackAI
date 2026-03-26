import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, Navigate } from 'react-router-dom';
import BenchPage from './pages/BenchPage';
import { AppDAW } from './daw/AppDAW';
import { EuclideanPage } from './pages/EuclideanPage';
import { DrummerProfilesPanel } from './daw/ui/DrummerProfilesPanel';
import './App.css';
import BeatSketchPage from './pages/BeatSketch';
import BeatPromptPage from './pages/BeatPrompt';
import LandingPage from './pages/LandingPage';
import BeatToolsPage from './pages/BeatToolsPage';

function App() {
  return (
    <Router>
      <div className="App min-h-screen bg-slate-950">
        <nav className="bg-black/70 backdrop-blur border-b border-white/10">
          <div className="max-w-6xl mx-auto px-4 py-4 flex flex-wrap items-center gap-4 justify-between">
            <Link to="/" className="flex items-center gap-3 group">
              <span className="inline-flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-amber-400 to-amber-200 text-slate-900 font-black">
                DT
              </span>
              <div className="leading-tight">
                <p className="text-white font-semibold text-lg tracking-tight">DrumTracKAI</p>
                <p className="text-[10px] uppercase tracking-[0.35em] text-amber-200">Release Candidate</p>
              </div>
            </Link>
            <div className="flex-1 flex flex-wrap items-center justify-center gap-2 text-sm text-slate-200">
              <Link to="/#studio-workflows" className="px-3 py-2 rounded-full hover:bg-white/10">Features</Link>
              <Link to="/beat-tools" className="px-3 py-2 rounded-full hover:bg-white/10">Beat Tools</Link>
              <Link to="/#pricing" className="px-3 py-2 rounded-full hover:bg-white/10">Pricing</Link>
              <Link to="/" className="px-3 py-2 rounded-full hover:bg-white/10">Pro Studio</Link>
              <Link to="/bench" className="px-3 py-2 rounded-full hover:bg-white/10">Benchmarks</Link>
            </div>
            <div className="flex items-center gap-3">
              <Link
                to="/beat-prompt?auth=signin"
                className="text-sm px-4 py-2 rounded-full border border-white/30 text-white/90 hover:text-white"
              >
                Sign in
              </Link>
              <Link
                to="/beat-prompt?auth=signup"
                className="text-sm px-5 py-2 rounded-full bg-gradient-to-r from-amber-400 to-amber-200 text-slate-900 font-semibold shadow-lg"
              >
                Sign up
              </Link>
            </div>
          </div>
        </nav>
        
        <Routes>
          {/* DCSM Studio (primary in v1.1.17) */}
          <Route path="/" element={<AppDAW />} />

          {/* Backward-compatible entry path(s) */}
          <Route path="/daw" element={<Navigate to="/" replace />} />

          {/* Marketing landing */}
          <Route path="/landing" element={<LandingPage />} />

          {/* Benchmarks and other tools */}
          <Route path="/bench" element={<BenchPage />} />

          {/* Euclidean groove designer */}
          <Route path="/euclidean" element={<EuclideanPage />} />

          {/* Beatbox capture pipeline */}
          <Route path="/beat-sketch" element={<BeatSketchPage />} />

          {/* Prompt-to-groove consumer flow */}
          <Route path="/beat-prompt" element={<BeatPromptPage />} />

          {/* Beat Tools landing for Basic tier */}
          <Route path="/beat-tools" element={<BeatToolsPage />} />

          {/* Admin-only drummer personas/profile dashboard */}
          <Route path="/admin/drummers" element={
            <div className="max-w-5xl mx-auto mt-4">
              <DrummerProfilesPanel />
            </div>
          } />

          {/* Safety net: unknown routes go to the primary module */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
