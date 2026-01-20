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
    const dpr = window.devicePixelRatio || 1;
    const cssW = Math.max(1, Math.floor(canvas.parentElement?.clientWidth || canvas.clientWidth || 800));
    const cssH = 160;
    canvas.style.width = '100%';
    canvas.style.height = `${cssH}px`;
    canvas.width = Math.floor(cssW * dpr);
    canvas.height = Math.floor(cssH * dpr);

    ctx.resetTransform();
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, cssW, cssH);
    ctx.fillStyle = '#1e1e1e';
    ctx.fillRect(0, 0, cssW, cssH);

    const drawBars = (data: number[], centerY: number, laneHeight: number, color: string) => {
      ctx.strokeStyle = color;
      ctx.lineWidth = 1;
      ctx.beginPath();
      const n = data.length;
      const halfLane = laneHeight / 2;
      for (let x = 0; x < cssW; x++) {
        const idx = Math.floor((x / cssW) * n);
        const v = Math.max(0, Math.min(1, data[idx] ?? 0));
        const amp = v * (halfLane - 2);
        ctx.moveTo(x + 0.5, centerY - amp);
        ctx.lineTo(x + 0.5, centerY + amp);
      }
      ctx.stroke();
    };

    const half = cssH / 2;
    const centerTop = half / 2;
    const centerBottom = half + half / 2;

    ctx.strokeStyle = '#2a2a2a';
    ctx.beginPath();
    ctx.moveTo(0, centerTop + 0.5);
    ctx.lineTo(cssW, centerTop + 0.5);
    ctx.moveTo(0, centerBottom + 0.5);
    ctx.lineTo(cssW, centerBottom + 0.5);
    ctx.stroke();

    drawBars(l, centerTop, half, '#64b5f6');
    if (r) drawBars(r, centerBottom, half, '#9575cd');

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
          const x = Math.floor((t / durationSec) * cssW);
          ctx.moveTo(x + 0.5, 0);
          ctx.lineTo(x + 0.5, cssH);
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
          const x = Math.floor((t / durationSec) * cssW);
          ctx.moveTo(x + 0.5, 0);
          ctx.lineTo(x + 0.5, cssH);
        }
        ctx.stroke();
      }
      ctx.restore();
    }
  }, [peaks, peaksL, peaksR, beatLanes, barLanes, durationSec]);

  return <canvas ref={canvasRef} width={800} height={160} style={{ width: '100%', height: 160, background: '#1e1e1e' }} />;
};
