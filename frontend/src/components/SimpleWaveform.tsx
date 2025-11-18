/**
 * Simple Waveform Display - Uses peaks array from backend
 */
import React, { useRef, useEffect } from 'react';

interface SimpleWaveformProps {
  peaks: number[];
  width?: number;
  height?: number;
  color?: string;
  backgroundColor?: string;
  className?: string;
}

export const SimpleWaveform: React.FC<SimpleWaveformProps> = ({
  peaks,
  width = 800,
  height = 120,
  color = '#10B981',
  backgroundColor = '#1F2937',
  className = ''
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !peaks || peaks.length === 0) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    
    // Set canvas size for high DPI displays
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    ctx.scale(dpr, dpr);

    // Clear canvas
    ctx.fillStyle = backgroundColor;
    ctx.fillRect(0, 0, width, height);

    // Draw waveform
    const centerY = height / 2;
    const barWidth = width / peaks.length;
    const amplitude = height * 0.45; // Use 90% of height for waveform

    ctx.fillStyle = color;

    peaks.forEach((peak, index) => {
      const x = index * barWidth;
      const barHeight = Math.abs(peak) * amplitude;
      
      // Draw from center
      ctx.fillRect(
        x,
        centerY - barHeight,
        Math.max(1, barWidth), // At least 1px wide
        barHeight * 2 // Both positive and negative
      );
    });

    // Add a subtle gradient overlay
    const gradient = ctx.createLinearGradient(0, 0, 0, height);
    gradient.addColorStop(0, 'rgba(16, 185, 129, 0.3)');
    gradient.addColorStop(0.5, 'rgba(16, 185, 129, 0.1)');
    gradient.addColorStop(1, 'rgba(16, 185, 129, 0.3)');
    
    ctx.fillStyle = gradient;
    peaks.forEach((peak, index) => {
      const x = index * barWidth;
      const barHeight = Math.abs(peak) * amplitude;
      ctx.fillRect(x, centerY - barHeight, Math.max(1, barWidth), barHeight * 2);
    });

  }, [peaks, width, height, color, backgroundColor]);

  if (!peaks || peaks.length === 0) {
    return (
      <div 
        className={`flex items-center justify-center rounded ${className}`}
        style={{ 
          width: `${width}px`, 
          height: `${height}px`,
          backgroundColor: backgroundColor 
        }}
      >
        <span className="text-gray-400 text-sm">No waveform data</span>
      </div>
    );
  }

  return (
    <div className={`relative ${className}`}>
      <canvas
        ref={canvasRef}
        className="rounded"
        style={{ 
          width: `${width}px`, 
          height: `${height}px`,
          backgroundColor: backgroundColor
        }}
      />
      <div className="absolute bottom-1 left-2 text-xs text-gray-400">
        {peaks.length} samples
      </div>
    </div>
  );
};

export default SimpleWaveform;
