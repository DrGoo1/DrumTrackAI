import React, { useRef, useEffect, useState } from 'react';

// Professional Waveform Visualization Component
const WaveformVisualization = ({ 
  audioBuffer, 
  width = 800, 
  height = 60, 
  color = '#10B981',
  backgroundColor = '#1F2937',
  currentTime = 0,
  duration = 0,
  onTimeClick = null,
  zoom = 1,
  className = ''
}) => {
  const canvasRef = useRef(null);
  const [waveformData, setWaveformData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  // Generate waveform data from audio buffer
  useEffect(() => {
    if (!audioBuffer) return;

    setIsLoading(true);
    
    const generateWaveform = async () => {
      try {
        const channelData = audioBuffer.getChannelData(0);
        const samplesPerPixel = Math.floor(channelData.length / (width * zoom));
        const waveform = [];

        for (let i = 0; i < width * zoom; i++) {
          const start = i * samplesPerPixel;
          const end = Math.min(start + samplesPerPixel, channelData.length);
          
          let min = 0;
          let max = 0;
          let rms = 0;

          for (let j = start; j < end; j++) {
            const sample = channelData[j];
            if (sample > max) max = sample;
            if (sample < min) min = sample;
            rms += sample * sample;
          }

          rms = Math.sqrt(rms / (end - start));
          waveform.push({ min, max, rms });
        }

        setWaveformData(waveform);
      } catch (error) {
        console.error('Error generating waveform:', error);
      } finally {
        setIsLoading(false);
      }
    };

    generateWaveform();
  }, [audioBuffer, width, zoom]);

  // Draw waveform on canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !waveformData) return;

    const ctx = canvas.getContext('2d');
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
    const amplitude = height * 0.4;

    ctx.fillStyle = color;
    ctx.strokeStyle = color;
    ctx.lineWidth = 1;

    // Draw waveform bars
    const barWidth = width / waveformData.length;
    
    waveformData.forEach((sample, index) => {
      const x = index * barWidth;
      const maxHeight = Math.abs(sample.max) * amplitude;
      const minHeight = Math.abs(sample.min) * amplitude;
      
      // Draw positive peak
      if (sample.max > 0) {
        ctx.fillRect(x, centerY - maxHeight, barWidth, maxHeight);
      }
      
      // Draw negative peak
      if (sample.min < 0) {
        ctx.fillRect(x, centerY, barWidth, minHeight);
      }
    });

    // Draw RMS overlay (softer representation)
    ctx.fillStyle = color + '40'; // 25% opacity
    waveformData.forEach((sample, index) => {
      const x = index * barWidth;
      const rmsHeight = sample.rms * amplitude;
      ctx.fillRect(x, centerY - rmsHeight, barWidth, rmsHeight * 2);
    });

    // Draw playhead
    if (duration > 0 && currentTime >= 0) {
      const playheadX = (currentTime / duration) * width;
      ctx.strokeStyle = '#EF4444'; // Red playhead
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(playheadX, 0);
      ctx.lineTo(playheadX, height);
      ctx.stroke();
    }

    // Draw grid lines (beats)
    ctx.strokeStyle = '#374151'; // Gray grid
    ctx.lineWidth = 1;
    ctx.setLineDash([2, 2]);
    
    const beatsPerSecond = 120 / 60; // Assuming 120 BPM
    const totalBeats = duration * beatsPerSecond;
    const pixelsPerBeat = width / totalBeats;
    
    for (let beat = 0; beat < totalBeats; beat++) {
      const x = beat * pixelsPerBeat;
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }
    
    ctx.setLineDash([]); // Reset dash

  }, [waveformData, width, height, color, backgroundColor, currentTime, duration]);

  // Handle canvas click for seeking
  const handleCanvasClick = (event) => {
    if (!onTimeClick || !duration) return;

    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const clickTime = (x / width) * duration;
    
    onTimeClick(Math.max(0, Math.min(duration, clickTime)));
  };

  return (
    <div className={`relative ${className}`}>
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-800 bg-opacity-75 rounded">
          <div className="text-white text-sm">Generating waveform...</div>
        </div>
      )}
      
      <canvas
        ref={canvasRef}
        onClick={handleCanvasClick}
        className="cursor-pointer rounded"
        style={{ 
          width: `${width}px`, 
          height: `${height}px`,
          backgroundColor: backgroundColor
        }}
      />
      
      {/* Time markers */}
      <div className="absolute bottom-0 left-0 right-0 flex justify-between text-xs text-gray-400 px-1">
        <span>0:00</span>
        {duration > 0 && (
          <span>
            {Math.floor(duration / 60)}:{Math.floor(duration % 60).toString().padStart(2, '0')}
          </span>
        )}
      </div>
    </div>
  );
};

// Simplified waveform for track overview
export const TrackWaveform = ({ 
  audioBuffer, 
  trackColor = '#10B981',
  currentTime = 0,
  duration = 0,
  height = 40,
  className = ''
}) => {
  return (
    <WaveformVisualization
      audioBuffer={audioBuffer}
      width={600}
      height={height}
      color={trackColor}
      backgroundColor="transparent"
      currentTime={currentTime}
      duration={duration}
      className={className}
    />
  );
};

// Mini waveform for track list
export const MiniWaveform = ({ 
  audioBuffer, 
  trackColor = '#10B981',
  width = 200,
  height = 30 
}) => {
  return (
    <WaveformVisualization
      audioBuffer={audioBuffer}
      width={width}
      height={height}
      color={trackColor}
      backgroundColor="#374151"
      zoom={0.5}
      className="rounded"
    />
  );
};

export default WaveformVisualization;
