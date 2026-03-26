import React, { useEffect, useRef } from 'react';

type Props = {
  peaks?: number[]; // mono fallback
  peaksL?: number[]; // stereo left
  peaksR?: number[]; // stereo right
  durationSec?: number; // total audio duration in seconds for time->x mapping
  beatLanes?: Array<{ start: number; end: number; beats: number[]; confidence?: number }>; // per-section beat arrays
  barLanes?: Array<{ start: number; end: number; bars: number[] }>; // per-section bar arrays
  onSelect?: (startSec: number, endSec: number) => void;
};

export const WaveformView: React.FC<Props> = ({ peaks, peaksL, peaksR, durationSec, beatLanes, barLanes }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const l = peaksL || peaks;
    const r = peaksR || peaks;
    if (!canvas || !l) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const draw = (data: number[], top: number, height: number, color: string) => {
      ctx.strokeStyle = color;
      ctx.beginPath();
      for (let x = 0; x < canvas.width; x++) {
        const idx = Math.floor((x / canvas.width) * data.length);
        const v = data[idx] || 0;
        const y = top + height * (0.5 - v * 0.5);
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
    };

    const half = canvas.height / 2;
    draw(l, 0, half, '#64b5f6');
    if (r) draw(r, half, half, '#9575cd');

    // Draw beat grid overlay
    if (durationSec && beatLanes && beatLanes.length) {
      ctx.save();
      ctx.globalAlpha = 0.6;
      for (const lane of beatLanes) {
        const { beats } = lane;
        if (!beats || !beats.length) continue;
        // Color by confidence (if provided)
        let color = '#26a69a';
        const conf = lane.confidence ?? 1.0;
        if (conf < 1.1) color = '#ef5350'; // low confidence: red
        else if (conf < 1.5) color = '#ffca28'; // medium: amber
        else color = '#26a69a'; // high: teal
        ctx.strokeStyle = color;
        ctx.lineWidth = 1;
        ctx.beginPath();
        for (const t of beats) {
          if (t < 0 || t > durationSec) continue;
          const x = Math.floor((t / durationSec) * canvas.width);
          ctx.moveTo(x + 0.5, 0);
          ctx.lineTo(x + 0.5, canvas.height);
        }
        ctx.stroke();
      }
      ctx.restore();
    }

    // Draw bar lines overlay (thicker)
    if (durationSec && barLanes && barLanes.length) {
      ctx.save();
      ctx.globalAlpha = 0.9;
      ctx.strokeStyle = '#80cbc4'; // teal-light for bars
      ctx.lineWidth = 2;
      for (const lane of barLanes) {
        const { bars } = lane;
        if (!bars || !bars.length) continue;
        ctx.beginPath();
        for (const t of bars) {
          if (t < 0 || t > durationSec) continue;
          const x = Math.floor((t / durationSec) * canvas.width);
          ctx.moveTo(x + 0.5, 0);
          ctx.lineTo(x + 0.5, canvas.height);
        }
        ctx.stroke();
      }
      ctx.restore();
    }
  }, [peaks, peaksL, peaksR, beatLanes, barLanes, durationSec]);

  return <canvas ref={canvasRef} width={800} height={160} style={{ width: '100%', height: 160, background: '#1e1e1e' }} />;
};
