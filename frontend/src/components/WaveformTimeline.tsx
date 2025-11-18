/**
 * Waveform Timeline Component - Phase 3 Slice A
 * Renders waveform peaks on the timeline for visual feedback
 */

import React, { useRef, useEffect } from 'react';

interface WaveformTimelineProps {
  peaks: number[];
  width: number;
  height: number;
  color?: string;
  backgroundColor?: string;
}

export const WaveformTimeline: React.FC<WaveformTimelineProps> = ({
  peaks,
  width,
  height,
  color = '#00ff00',
  backgroundColor = '#1a1a1a'
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !peaks.length) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas
    ctx.fillStyle = backgroundColor;
    ctx.fillRect(0, 0, width, height);

    // Draw waveform
    ctx.fillStyle = color;
    ctx.strokeStyle = color;
    ctx.lineWidth = 1;

    const barWidth = width / peaks.length;
    const centerY = height / 2;

    peaks.forEach((peak, index) => {
      const x = index * barWidth;
      const barHeight = peak * (height * 0.8); // 80% of canvas height
      const y = centerY - barHeight / 2;

      // Draw waveform bar
      ctx.fillRect(x, y, Math.max(1, barWidth - 1), barHeight);
    });

  }, [peaks, width, height, color, backgroundColor]);

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      style={{
        display: 'block',
        border: '1px solid #333',
        backgroundColor
      }}
    />
  );
};
