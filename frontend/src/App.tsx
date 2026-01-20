import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import WebDAWApp from './components/WebDAWApp';
import BenchPage from './pages/BenchPage';
import { WebDAW } from './pages/WebDAW';
import WebDAWAppV3 from './pages/WebDAWAppV3';
import { UploadWithWaveform } from './components/UploadWithWaveform';
import { initializeTransportBridge } from './integration/tempoBridge';
import './App.css';

function App() {
  useEffect(() => {
    initializeTransportBridge();
  }, []);

  return (
    <Router>
      <div className="App min-h-screen bg-slate-950">
        <nav className="bg-slate-900 border-b border-slate-800 px-4 py-2">
          <div className="flex items-center justify-center max-w-6xl mx-auto">
            <div className="flex items-center gap-3 min-w-0">
              <div className="flex flex-col leading-tight min-w-0 text-center">
                <div className="text-[10px] uppercase tracking-wide text-slate-400 truncate">DrumTracKAI</div>
                <div className="text-base font-semibold text-white truncate">
                  <span className="text-lg">D</span>
                  <span className="text-sm text-slate-200">rumTrack</span>
                  <span className="ml-1 text-lg">C</span>
                  <span className="text-sm text-slate-200">reation</span>
                  <span className="ml-1 text-lg">S</span>
                  <span className="text-sm text-slate-200">tudio</span>
                  <span className="ml-1 text-lg">M</span>
                  <span className="text-sm text-slate-200">odule</span>
                </div>
              </div>
              <span className="text-[11px] px-2 py-1 rounded border border-slate-700 bg-slate-950 text-slate-300">
                v1.1.17
              </span>
            </div>
          </div>
        </nav>
        
        <Routes>
          <Route path="/upload" element={<UploadWithWaveform />} />
          <Route path="/" element={<WebDAWApp />} />
          <Route path="/v3" element={<WebDAWAppV3 />} />
          <Route path="/bench" element={<BenchPage />} />
          <Route path="/webdaw" element={<WebDAW />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
