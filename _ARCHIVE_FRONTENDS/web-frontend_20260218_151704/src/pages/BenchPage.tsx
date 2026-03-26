import React, { useState } from "react";
import { benchPeaks, benchAnalysis, benchGenerate } from "../services/api";

interface BenchResult {
  label: string;
  python_ms?: number;
  rust_ms?: number;
  notes?: number;
  python_error?: string;
  rust_error?: string;
}

export default function BenchPage() {
  const [key, setKey] = useState("");
  const [bpm, setBpm] = useState(120);
  const [bars, setBars] = useState(8);
  const [style, setStyle] = useState("rock");
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState<BenchResult[]>([]);

  const runBenchmarks = async () => {
    if (!key.trim()) {
      alert("Please enter a valid audio file key (e.g., uploads/your-file.wav)");
      return;
    }

    setRunning(true);
    setResults([]);

    try {
      // Run all benchmarks in parallel
      const [peaksResult, analysisResult, generateResult] = await Promise.all([
        benchPeaks(key, "both").catch(e => ({ python_error: e.message, rust_error: e.message })),
        benchAnalysis(key, "both").catch(e => ({ python_error: e.message, rust_error: e.message })),
        benchGenerate(bpm, bars, style).catch(e => ({ rust_error: e.message }))
      ]);

      setResults([
        { label: "Peaks Extraction", ...peaksResult },
        { label: "Audio Analysis", ...analysisResult },
        { label: `Generate (${bars} bars)`, ...generateResult }
      ]);
    } catch (error) {
      console.error("Benchmark failed:", error);
      alert("Benchmark failed: " + (error as Error).message);
    } finally {
      setRunning(false);
    }
  };

  const formatTime = (ms?: number) => {
    if (ms === undefined) return "—";
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  const getSpeedup = (pythonMs?: number, rustMs?: number) => {
    if (!pythonMs || !rustMs) return "—";
    const speedup = pythonMs / rustMs;
    return `${speedup.toFixed(1)}×`;
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6">
      <div className="max-w-6xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Performance Benchmarks</h1>
          <div className="text-sm text-slate-400">
            Rust vs Python Performance Comparison
          </div>
        </div>

        <div className="bg-slate-900 rounded-lg border border-slate-800 p-4">
          <h2 className="text-lg font-semibold mb-4">Benchmark Configuration</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm text-slate-400 mb-1">Audio File Key</label>
              <input
                className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm"
                placeholder="uploads/your-file.wav"
                value={key}
                onChange={(e) => setKey(e.target.value)}
              />
            </div>
            
            <div>
              <label className="block text-sm text-slate-400 mb-1">BPM</label>
              <input
                className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm"
                type="number"
                min="60"
                max="200"
                value={bpm}
                onChange={(e) => setBpm(parseInt(e.target.value) || 120)}
              />
            </div>
            
            <div>
              <label className="block text-sm text-slate-400 mb-1">Bars</label>
              <input
                className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm"
                type="number"
                min="1"
                max="32"
                value={bars}
                onChange={(e) => setBars(parseInt(e.target.value) || 8)}
              />
            </div>
            
            <div>
              <label className="block text-sm text-slate-400 mb-1">Style</label>
              <select
                className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm"
                value={style}
                onChange={(e) => setStyle(e.target.value)}
              >
                <option value="rock">Rock</option>
                <option value="funk">Funk</option>
                <option value="edm">EDM</option>
                <option value="hiphop">Hip Hop</option>
                <option value="jazz">Jazz</option>
                <option value="pop">Pop</option>
              </select>
            </div>
          </div>

          <div className="mt-4">
            <button
              className={`px-6 py-2 rounded font-medium ${
                running
                  ? "bg-slate-700 text-slate-400 cursor-not-allowed"
                  : "bg-emerald-600 hover:bg-emerald-700 text-white"
              }`}
              onClick={runBenchmarks}
              disabled={running}
            >
              {running ? "Running Benchmarks..." : "Run Benchmarks"}
            </button>
          </div>
        </div>

        {results.length > 0 && (
          <div className="bg-slate-900 rounded-lg border border-slate-800 p-4">
            <h2 className="text-lg font-semibold mb-4">Results</h2>
            
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-700">
                    <th className="text-left py-2 px-3 text-slate-300">Task</th>
                    <th className="text-right py-2 px-3 text-slate-300">Python</th>
                    <th className="text-right py-2 px-3 text-slate-300">Rust</th>
                    <th className="text-right py-2 px-3 text-slate-300">Speedup</th>
                    <th className="text-right py-2 px-3 text-slate-300">Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((result, i) => (
                    <tr key={i} className="border-b border-slate-800">
                      <td className="py-3 px-3 font-medium">{result.label}</td>
                      <td className="py-3 px-3 text-right">
                        {result.python_error ? (
                          <span className="text-red-400 text-xs">Error</span>
                        ) : (
                          <span className="text-blue-400">{formatTime(result.python_ms)}</span>
                        )}
                      </td>
                      <td className="py-3 px-3 text-right">
                        {result.rust_error ? (
                          <span className="text-red-400 text-xs">Error</span>
                        ) : (
                          <span className="text-emerald-400">{formatTime(result.rust_ms)}</span>
                        )}
                      </td>
                      <td className="py-3 px-3 text-right">
                        <span className="text-amber-400 font-medium">
                          {getSpeedup(result.python_ms, result.rust_ms)}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-right text-slate-400">
                        {result.notes ? `${result.notes} notes` : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="mt-4 text-xs text-slate-500 space-y-1">
              <div>• Speedup calculated as Python time ÷ Rust time</div>
              <div>• Rust implementation uses Symphonia decoder + spectral flux analysis</div>
              <div>• Python fallback uses librosa + soundfile for compatibility</div>
            </div>
          </div>
        )}

        <div className="bg-slate-900 rounded-lg border border-slate-800 p-4">
          <h2 className="text-lg font-semibold mb-2">Usage Instructions</h2>
          <div className="text-sm text-slate-400 space-y-2">
            <div>1. Upload an audio file through the main interface first</div>
            <div>2. Copy the file key from the upload response (e.g., "uploads/your-file.wav")</div>
            <div>3. Paste the key above and configure benchmark parameters</div>
            <div>4. Click "Run Benchmarks" to compare Rust vs Python performance</div>
          </div>
        </div>
      </div>
    </div>
  );
}
