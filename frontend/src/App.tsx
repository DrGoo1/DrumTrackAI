import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import WebDAWApp from './components/WebDAWApp';
import BenchPage from './pages/BenchPage';
import { WebDAW } from './pages/WebDAW';
import { UploadWithWaveform } from './components/UploadWithWaveform';
import './App.css';

function App() {
  return (
    <Router>
      <div className="App min-h-screen bg-slate-950">
        <nav className="bg-slate-900 border-b border-slate-800 px-4 py-2">
          <div className="flex items-center justify-between max-w-6xl mx-auto">
            <div className="flex items-center space-x-6">
              <h1 className="text-xl font-bold text-slate-100">DrumTracKAI v1.1.16</h1>
              <div className="flex space-x-4">
                <Link 
                  to="/upload" 
                  className="text-slate-300 hover:text-slate-100 px-3 py-2 rounded transition-colors"
                >
                  Upload Audio
                </Link>
                <Link 
                  to="/" 
                  className="text-slate-300 hover:text-slate-100 px-3 py-2 rounded transition-colors"
                >
                  DCSM Studio
                </Link>
                <Link 
                  to="/bench" 
                  className="text-slate-300 hover:text-slate-100 px-3 py-2 rounded transition-colors"
                >
                  Benchmarks
                </Link>
                <Link 
                  to="/webdaw" 
                  className="text-slate-300 hover:text-slate-100 px-3 py-2 rounded transition-colors"
                >
                  WebDAW (Scaffold)
                </Link>
              </div>
            </div>
            <div className="text-xs text-slate-400">
              Advanced Groove • Fill Library • Rust Performance
            </div>
          </div>
        </nav>
        
        <Routes>
          <Route path="/upload" element={<UploadWithWaveform />} />
          <Route path="/" element={<WebDAWApp />} />
          <Route path="/bench" element={<BenchPage />} />
          <Route path="/webdaw" element={<WebDAW />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
