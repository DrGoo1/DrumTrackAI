import React, { useEffect, useMemo, useRef, useState } from "react";
import type { DrumPlayerEngine } from "../../audio/drumPlayerEngine";
import { Tooltip } from "../Tooltip";

export type MonoChannel = {
  id: string;
  name: string;
  volume: number; // 0-100
  pan: number; // -50..50
  muted: boolean;
  solo: boolean;
  eq: boolean;
  sendOH: number; // 0-100
  sendRoom: number; // 0-100
};

export type StereoChannel = {
  id: string;
  name: string;
  volume: number; // 0-100
  pan: number; // -50..50
  muted: boolean;
  solo: boolean;
  eq: boolean;
  sendOH?: number; // 0-100
  sendRoom?: number; // 0-100
};

export type ConsoleMixerState = {
  monoChannels: MonoChannel[];
  stereoChannels: StereoChannel[];
  masterVolume: number;
};

const CHANNEL_ABBR: Record<string, string> = {
  kick: "K",
  kick_sub: "KS",
  snare_top: "ST",
  snare_bottom: "SB",
  tom1: "T1",
  tom2: "T2",
  tom3: "T3",
  tom4: "T4",
  tom5: "T5",
  hat: "HH",
  ride: "RD",
  crash: "CR",
  oh: "OH",
  room: "RM",
};

const CHANNEL_FULL: Record<string, string> = {
  kick: "Kick",
  kick_sub: "Kick Sub",
  snare_top: "Snare Top",
  snare_bottom: "Snare Bottom",
  tom1: "Tom 1",
  tom2: "Tom 2",
  tom3: "Tom 3",
  tom4: "Tom 4",
  tom5: "Tom 5",
  hat: "Hat",
  ride: "Ride",
  crash: "Crash",
  oh: "Overheads",
  room: "Room",
};

function clamp(v: number, min: number, max: number) {
  if (!Number.isFinite(v)) return min;
  return Math.max(min, Math.min(max, v));
}

function percentToGain01(percent: number) {
  return clamp(percent / 100, 0, 1.5);
}

function LedButton(props: { label: string; active: boolean; onClick: () => void }) {
  const { label, active, onClick } = props;
  return (
    <button
      onClick={onClick}
      className="relative px-3 py-2 rounded text-[10px] tracking-wider transition-all"
      style={{
        background: "linear-gradient(180deg, #2a2a2a, #1a1a1a)",
        boxShadow: "inset 0 2px 4px rgba(0, 0, 0, 0.6), 0 1px 0 rgba(255, 255, 255, 0.05)",
        border: "1px solid #0a0a0a",
        color: "#9ca3af",
        transform: active ? "translateY(1px)" : "translateY(0)",
      }}
    >
      <div className="flex items-center justify-center gap-1.5">
        <div
          className="w-2 h-2 rounded-full transition-all"
          style={{
            background: active
              ? "radial-gradient(circle, #4ade80, #16a34a)"
              : "radial-gradient(circle, #2a2a2a, #1a1a1a)",
            boxShadow: active
              ? "0 0 4px #4ade80, 0 0 8px #22c55e, inset 0 -1px 2px rgba(0, 0, 0, 0.5)"
              : "inset 0 1px 2px rgba(0, 0, 0, 0.8)",
            border: active ? "1px solid #86efac" : "1px solid #0a0a0a",
          }}
        />
        <span>{label}</span>
      </div>
      <div
        className="absolute inset-0 rounded pointer-events-none"
        style={{ background: "linear-gradient(180deg, rgba(255, 255, 255, 0.05) 0%, transparent 50%)" }}
      />
    </button>
  );
}

function MetallicButton(props: {
  label: string;
  active: boolean;
  onClick: () => void;
  color: "red" | "yellow";
}) {
  const { label, active, onClick, color } = props;
  const shadow = color === "red" ? "rgba(220, 38, 38, 0.5)" : "rgba(234, 179, 8, 0.5)";
  return (
    <button
      onClick={onClick}
      className="w-full px-2 py-2 rounded text-[10px] tracking-wider transition-all relative overflow-hidden flex items-center justify-center text-center leading-none"
      style={{
        background: active
          ? `linear-gradient(180deg, ${color === "red" ? "#dc2626" : "#eab308"}, ${
              color === "red" ? "#991b1b" : "#a16207"
            })`
          : "linear-gradient(180deg, #3a3a3a, #1a1a1a)",
        boxShadow: active
          ? `0 2px 8px ${shadow}, inset 0 1px 0 rgba(255, 255, 255, 0.2), inset 0 -1px 0 rgba(0, 0, 0, 0.5)`
          : "inset 0 2px 4px rgba(0, 0, 0, 0.6), 0 1px 0 rgba(255, 255, 255, 0.05)",
        color: active ? "#fff" : "#9ca3af",
        textShadow: active ? "0 1px 2px rgba(0, 0, 0, 0.5)" : "none",
        border: active ? "1px solid rgba(255, 255, 255, 0.1)" : "1px solid #0a0a0a",
        transform: active ? "translateY(1px)" : "translateY(0)",
      }}
    >
      {label}
      <div
        className="absolute inset-0 rounded"
        style={{ background: "linear-gradient(180deg, rgba(255, 255, 255, 0.1) 0%, transparent 50%)", pointerEvents: "none" }}
      />
    </button>
  );
}

function MetallicKnob(props: {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  size?: "small" | "medium" | "large";
}) {
  const { value, onChange, min = 0, max = 100, size = "medium" } = props;
  const [isDragging, setIsDragging] = useState(false);
  const startYRef = useRef(0);
  const startValueRef = useRef(0);

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    startYRef.current = e.clientY;
    startValueRef.current = value;
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging) return;
      const deltaY = startYRef.current - e.clientY;
      const sensitivity = size === "small" ? 0.5 : 0.8;
      const next = Math.round(startValueRef.current + deltaY * sensitivity);
      onChange(clamp(next, min, max));
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    if (isDragging) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
    }

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDragging, max, min, onChange, size]);

  const range = max - min;
  const normalizedValue = range === 0 ? 0 : (value - min) / range;
  const angle = (normalizedValue - 0.5) * 270;

  const sizeClasses: Record<string, string> = {
    small: "w-10 h-10",
    medium: "w-14 h-14",
    large: "w-16 h-16",
  };

  const indicatorSize: Record<string, string> = {
    small: "w-1 h-3",
    medium: "w-1.5 h-4",
    large: "w-2 h-5",
  };

  const origin = size === "small" ? "20px" : size === "medium" ? "28px" : "32px";

  return (
    <div
      className={`relative ${sizeClasses[size]} cursor-pointer rounded-full`}
      onMouseDown={handleMouseDown}
      style={{
        background: "radial-gradient(circle at 30% 30%, #4a4a4a, #2a2a2a 50%, #1a1a1a 70%, #0a0a0a)",
        boxShadow:
          "0 4px 12px rgba(0, 0, 0, 0.8), inset 0 -2px 4px rgba(0, 0, 0, 0.9), inset 0 2px 4px rgba(255, 255, 255, 0.1), inset -2px -2px 8px rgba(0, 0, 0, 0.6), inset 2px 2px 8px rgba(255, 255, 255, 0.05)",
      }}
    >
      <div
        className={`absolute ${indicatorSize[size]} bg-gradient-to-b from-orange-400 to-orange-600 rounded-full shadow-lg`}
        style={{
          top: "8%",
          left: "50%",
          transform: `translateX(-50%) rotate(${angle}deg)`,
          transformOrigin: `center ${origin}`,
          boxShadow: "0 0 4px rgba(255, 165, 0, 0.8), 0 0 8px rgba(255, 165, 0, 0.4)",
        }}
      />
      <div
        className="absolute top-1/2 left-1/2 w-1/3 h-1/3 -translate-x-1/2 -translate-y-1/2 rounded-full"
        style={{
          background: "radial-gradient(circle, #3a3a3a, #1a1a1a)",
          boxShadow: "inset 0 1px 2px rgba(0, 0, 0, 0.9)",
        }}
      />
      <div
        className="absolute inset-0 rounded-full"
        style={{ background: "linear-gradient(135deg, rgba(255, 255, 255, 0.1) 0%, transparent 50%)", pointerEvents: "none" }}
      />
    </div>
  );
}

function MetallicFader(props: { value: number; onChange: (value: number) => void }) {
  const { value, onChange } = props;
  const [isDragging, setIsDragging] = useState(false);
  const faderRef = useRef<HTMLDivElement>(null);
  const ZERO_POINT = 75;

  const updateValue = (clientY: number) => {
    if (!faderRef.current) return;
    const rect = faderRef.current.getBoundingClientRect();
    const percentage = 1 - (clientY - rect.top) / rect.height;
    const next = Math.round(clamp(percentage * 100, 0, 100));
    onChange(next);
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    updateValue(e.clientY);
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isDragging) updateValue(e.clientY);
    };
    const handleMouseUp = () => setIsDragging(false);

    if (isDragging) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
    }

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDragging]);

  return (
    <div
      ref={faderRef}
      className="relative w-8 h-40 cursor-pointer rounded-sm"
      onMouseDown={handleMouseDown}
      style={{
        background: "linear-gradient(90deg, #0a0a0a 0%, #1a1a1a 50%, #0a0a0a 100%)",
        boxShadow: "inset 0 0 10px rgba(0, 0, 0, 0.9), inset -2px 0 4px rgba(0, 0, 0, 0.5), inset 2px 0 4px rgba(0, 0, 0, 0.5)",
      }}
    >
      <div
        className="absolute left-0 right-0 h-px"
        style={{
          top: `${100 - ZERO_POINT}%`,
          background: "rgba(255, 255, 255, 0.25)",
          boxShadow: "0 0 6px rgba(255, 255, 255, 0.15)",
          pointerEvents: "none",
        }}
      />
      <div
        className="absolute -left-5 text-[9px] text-gray-300"
        style={{ top: `${100 - ZERO_POINT}%`, transform: "translateY(-50%)", pointerEvents: "none" }}
      >
        0
      </div>
      <div className="absolute inset-y-2 left-1/2 -translate-x-1/2 w-0.5 bg-black">
        {Array.from({ length: 11 }).map((_, i) => (
          <div
            key={i}
            className="absolute w-2 h-px bg-gray-600 left-1/2 -translate-x-1/2"
            style={{ top: `${i * 10}%` }}
          />
        ))}
      </div>
      <div
        className="absolute left-1/2 -translate-x-1/2 w-10 h-9 cursor-grab active:cursor-grabbing rounded-sm"
        style={{
          top: `${100 - value}%`,
          transform: "translate(-50%, -50%)",
          background: "linear-gradient(180deg, #5a5a5a 0%, #3a3a3a 40%, #2a2a2a 60%, #1a1a1a 100%)",
          boxShadow:
            "0 4px 8px rgba(0, 0, 0, 0.8), inset 0 1px 0 rgba(255, 255, 255, 0.3), inset 0 -1px 0 rgba(0, 0, 0, 0.8), inset 1px 0 0 rgba(255, 255, 255, 0.1), inset -1px 0 0 rgba(0, 0, 0, 0.5)",
          border: "1px solid #1a1a1a",
        }}
      >
        <div className="h-full flex flex-col justify-center items-center gap-1">
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="w-6 h-px rounded"
              style={{
                background: "linear-gradient(90deg, transparent, #1a1a1a 50%, transparent)",
                boxShadow: "0 1px 0 rgba(255, 255, 255, 0.05)",
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function VUMeter(props: { level: number }) {
  const { level } = props;
  const [animatedLevel, setAnimatedLevel] = useState(level);
  const [peakHold, setPeakHold] = useState(0);

  useEffect(() => {
    const interval = window.setInterval(() => {
      setAnimatedLevel((prev) => {
        const diff = level - prev;
        if (Math.abs(diff) < 0.5) return level;
        return prev + diff * 0.75;
      });
    }, 16);

    return () => window.clearInterval(interval);
  }, [level]);

  useEffect(() => {
    if (animatedLevel > peakHold) {
      setPeakHold(animatedLevel);
      window.setTimeout(() => {
        setPeakHold((prev) => Math.max(0, prev - 8));
      }, 700);
    }
  }, [animatedLevel, peakHold]);

  const segments = 12;
  const filledSegments = Math.round((animatedLevel / 100) * segments);
  const peakSegment = Math.round((peakHold / 100) * segments);

  const getSegmentColor = (index: number) => {
    const percentage = (index / segments) * 100;
    if (percentage > 83) return { bg: "#dc2626", glow: "rgba(220, 38, 38, 0.6)" };
    if (percentage > 70) return { bg: "#eab308", glow: "rgba(234, 179, 8, 0.6)" };
    return { bg: "#22c55e", glow: "rgba(34, 197, 94, 0.6)" };
  };

  return (
    <div
      className="flex flex-col-reverse gap-0.5 w-5 h-32 p-1 rounded-sm"
      style={{
        background: "linear-gradient(90deg, #0a0a0a 0%, #1a1a1a 50%, #0a0a0a 100%)",
        boxShadow: "inset 0 2px 4px rgba(0, 0, 0, 0.9), inset 0 -2px 4px rgba(0, 0, 0, 0.5)",
      }}
    >
      {Array.from({ length: segments }).map((_, index) => {
        const isFilled = index < filledSegments;
        const isPeak = index === peakSegment - 1 && !isFilled;
        const segmentColor = getSegmentColor(index);

        return (
          <div
            key={index}
            className="w-full h-full rounded-[1px] transition-all"
            style={{
              background: isFilled || isPeak
                ? `linear-gradient(90deg, ${segmentColor.bg}, ${segmentColor.bg}dd)`
                : "linear-gradient(90deg, #1a1a1a, #0f0f0f)",
              boxShadow: isFilled || isPeak
                ? `0 0 3px ${segmentColor.glow}, inset 0 1px 0 rgba(255, 255, 255, 0.3)`
                : "inset 0 1px 1px rgba(0, 0, 0, 0.8)",
              opacity: isFilled || isPeak ? 1 : 0.3,
            }}
          />
        );
      })}
    </div>
  );
}

function MonoChannelStrip(props: {
  channel: MonoChannel;
  level: number;
  onUpdate: (updates: Partial<MonoChannel>) => void;
}) {
  const { channel, level, onUpdate } = props;
  const headerText = CHANNEL_ABBR[channel.id] || channel.name;
  const headerTitle = CHANNEL_FULL[channel.id] || channel.name;
  return (
    <div
      className="relative overflow-hidden flex flex-col items-center w-32 py-4 px-3 rounded-lg"
      style={{
        background: "linear-gradient(180deg, #2a2a2a 0%, #1a1a1a 50%, #0f0f0f 100%)",
        boxShadow:
          "0 2px 8px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255, 255, 255, 0.05), inset 0 -1px 0 rgba(0, 0, 0, 0.8)",
      }}
    >
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: "linear-gradient(180deg, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0.02) 18%, transparent 55%)",
          mixBlendMode: "screen",
        }}
      />
      <div className="mb-3 w-full">
        <div
          className="w-full h-16 flex items-center justify-center text-gray-50 text-center px-2 py-1.5 rounded text-[11px] font-semibold tracking-tight leading-[1.1]"
          style={{
            background: "linear-gradient(180deg, #1a1a1a 0%, #0a0a0a 100%)",
            boxShadow: "inset 0 2px 4px rgba(0, 0, 0, 0.8), 0 1px 0 rgba(255, 255, 255, 0.05)",
            border: "1px solid #000",
          }}
        >
          <span
            className="block w-full px-0.5"
            style={{
              display: "-webkit-box",
              WebkitBoxOrient: "vertical" as any,
              WebkitLineClamp: 3,
              overflow: "hidden",
              textOverflow: "ellipsis",
              textShadow: "0 1px 1px rgba(0,0,0,0.9)",
            }}
          >
            <Tooltip content={headerTitle} placement="top" maxWidthClassName="w-48" wrapperClassName="w-full">
              <span className="block w-full">{headerText}</span>
            </Tooltip>
          </span>
        </div>
      </div>

      <div className="mb-3 flex flex-col items-center">
        <label className="text-gray-400 text-[10px] mb-1.5 tracking-wider">SEND OH</label>
        <MetallicKnob value={channel.sendOH} onChange={(v) => onUpdate({ sendOH: v })} size="small" />
      </div>

      <div className="mb-3 flex flex-col items-center">
        <label className="text-gray-400 text-[10px] mb-1.5 tracking-wider">SEND ROOM</label>
        <MetallicKnob value={channel.sendRoom} onChange={(v) => onUpdate({ sendRoom: v })} size="small" />
      </div>

      <div className="mb-3 flex flex-col items-center">
        <label className="text-gray-400 text-[10px] mb-1.5 tracking-wider">PAN</label>
        <MetallicKnob
          value={channel.pan}
          onChange={(v) => onUpdate({ pan: v })}
          min={-50}
          max={50}
          size="medium"
        />
        <div className="text-gray-400 text-[9px] mt-1">
          {channel.pan === 0 ? "C" : channel.pan < 0 ? `L${Math.abs(channel.pan)}` : `R${channel.pan}`}
        </div>
      </div>

      <div className="mb-3">
        <LedButton label="EQ" active={channel.eq} onClick={() => onUpdate({ eq: !channel.eq })} />
      </div>

      <div className="mb-3">
        <MetallicFader value={channel.volume} onChange={(v) => onUpdate({ volume: v })} />
      </div>

      <div className="mb-3">
        <VUMeter level={level} />
      </div>

      <div
        className="text-white text-[10px] mb-3 px-2 py-0.5 rounded"
        style={{
          background: "linear-gradient(180deg, #1a1a1a 0%, #0a0a0a 100%)",
          boxShadow: "inset 0 1px 3px rgba(0, 0, 0, 0.8)",
        }}
      >
        {channel.volume}
      </div>

      <div className="space-y-2 w-full">
        <MetallicButton label="SOLO" active={channel.solo} onClick={() => onUpdate({ solo: !channel.solo })} color="yellow" />
        <MetallicButton label="MUTE" active={channel.muted} onClick={() => onUpdate({ muted: !channel.muted })} color="red" />
      </div>
    </div>
  );
}

function StereoChannelStrip(props: {
  channel: StereoChannel;
  level: number;
  onUpdate: (updates: Partial<StereoChannel>) => void;
}) {
  const { channel, level, onUpdate } = props;
  const hasSends = channel.sendOH !== undefined && channel.sendRoom !== undefined;
  const headerText = CHANNEL_ABBR[channel.id] || channel.name;
  const headerTitle = CHANNEL_FULL[channel.id] || channel.name;

  return (
    <div
      className="relative overflow-hidden flex flex-col items-center w-32 py-4 px-3 rounded-lg"
      style={{
        background: "linear-gradient(180deg, #2a2a2a 0%, #1a1a1a 50%, #0f0f0f 100%)",
        boxShadow:
          "0 2px 8px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255, 255, 255, 0.05), inset 0 -1px 0 rgba(0, 0, 0, 0.8)",
      }}
    >
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: "linear-gradient(180deg, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0.02) 18%, transparent 55%)",
          mixBlendMode: "screen",
        }}
      />
      <div className="mb-3 w-full">
        <div
          className="relative w-full h-16 flex items-center justify-center text-gray-50 text-center px-2 py-1.5 rounded text-[11px] font-semibold tracking-tight leading-[1.1]"
          style={{
            background: "linear-gradient(180deg, #1a3a1a 0%, #0a1a0a 100%)",
            boxShadow: "inset 0 2px 4px rgba(0, 0, 0, 0.8), 0 1px 0 rgba(255, 255, 255, 0.05)",
            border: "1px solid #0a3a0a",
          }}
        >
          <span
            className="block w-full px-0.5"
            style={{
              display: "-webkit-box",
              WebkitBoxOrient: "vertical" as any,
              WebkitLineClamp: 3,
              overflow: "hidden",
              textOverflow: "ellipsis",
              textShadow: "0 1px 1px rgba(0,0,0,0.9)",
            }}
          >
            <Tooltip content={headerTitle} placement="top" maxWidthClassName="w-48" wrapperClassName="w-full">
              <span className="block w-full">{headerText}</span>
            </Tooltip>
          </span>
          <div className="absolute bottom-1 right-2 text-[8px] text-green-400 tracking-widest">ST</div>
        </div>
      </div>

      {hasSends && (
        <>
          <div className="mb-3 flex flex-col items-center">
            <label className="text-gray-400 text-[10px] mb-1.5 tracking-wider">SEND OH</label>
            <MetallicKnob value={channel.sendOH!} onChange={(v) => onUpdate({ sendOH: v })} size="small" />
          </div>

          <div className="mb-3 flex flex-col items-center">
            <label className="text-gray-400 text-[10px] mb-1.5 tracking-wider">SEND ROOM</label>
            <MetallicKnob value={channel.sendRoom!} onChange={(v) => onUpdate({ sendRoom: v })} size="small" />
          </div>
        </>
      )}

      <div className="mb-3 flex flex-col items-center">
        <label className="text-gray-400 text-[10px] mb-1.5 tracking-wider">PAN</label>
        <MetallicKnob
          value={channel.pan}
          onChange={(v) => onUpdate({ pan: v })}
          min={-50}
          max={50}
          size="medium"
        />
        <div className="text-gray-400 text-[9px] mt-1">
          {channel.pan === 0 ? "C" : channel.pan < 0 ? `L${Math.abs(channel.pan)}` : `R${channel.pan}`}
        </div>
      </div>

      <div className="mb-3">
        <LedButton label="EQ" active={channel.eq} onClick={() => onUpdate({ eq: !channel.eq })} />
      </div>

      <div className="mb-3">
        <MetallicFader value={channel.volume} onChange={(v) => onUpdate({ volume: v })} />
      </div>

      <div className="mb-3">
        <VUMeter level={level} />
      </div>

      <div
        className="text-white text-[10px] mb-3 px-2 py-0.5 rounded"
        style={{
          background: "linear-gradient(180deg, #1a1a1a 0%, #0a0a0a 100%)",
          boxShadow: "inset 0 1px 3px rgba(0, 0, 0, 0.8)",
        }}
      >
        {channel.volume}
      </div>

      <div className="space-y-2 w-full">
        <MetallicButton label="SOLO" active={channel.solo} onClick={() => onUpdate({ solo: !channel.solo })} color="yellow" />
        <MetallicButton label="MUTE" active={channel.muted} onClick={() => onUpdate({ muted: !channel.muted })} color="red" />
      </div>
    </div>
  );
}

function MasterSection(props: { masterVolume: number; onMasterVolumeChange: (value: number) => void; overallLevel: number }) {
  const { masterVolume, onMasterVolumeChange, overallLevel } = props;
  return (
    <div
      className="flex flex-col items-center w-36 py-4 px-4 rounded-lg"
      style={{
        background: "linear-gradient(180deg, #3a2a2a 0%, #2a1a1a 50%, #1a0f0f 100%)",
        boxShadow:
          "0 4px 12px rgba(0, 0, 0, 0.8), inset 0 1px 0 rgba(255, 255, 255, 0.05), inset 0 -1px 0 rgba(0, 0, 0, 0.8)",
        border: "2px solid #4a1a1a",
      }}
    >
      <div className="mb-4 w-full">
        <div
          className="w-full text-white text-center px-2 py-2 rounded tracking-widest"
          style={{
            background: "linear-gradient(180deg, #4a1a1a 0%, #2a0a0a 100%)",
            boxShadow: "inset 0 2px 4px rgba(0, 0, 0, 0.8), 0 1px 0 rgba(255, 255, 255, 0.05)",
            border: "1px solid #2a0a0a",
          }}
        >
          MASTER
        </div>
      </div>

      <div className="mb-4 flex gap-2 items-center">
        <div className="flex flex-col items-center gap-1">
          <VUMeter level={overallLevel} />
          <span className="text-gray-400 text-[8px] tracking-wider">L</span>
        </div>
        <div className="flex flex-col items-center gap-1">
          <VUMeter level={overallLevel * 0.95} />
          <span className="text-gray-400 text-[8px] tracking-wider">R</span>
        </div>
      </div>

      <div className="mb-4">
        <MetallicFader value={masterVolume} onChange={onMasterVolumeChange} />
      </div>

      <div
        className="text-white text-xs mb-2 px-3 py-1 rounded"
        style={{
          background: "linear-gradient(180deg, #1a1a1a 0%, #0a0a0a 100%)",
          boxShadow: "inset 0 1px 3px rgba(0, 0, 0, 0.8)",
          border: "1px solid #000",
        }}
      >
        {masterVolume}
      </div>

      <div className="text-gray-400 text-[9px] tracking-widest">MAIN OUT</div>
    </div>
  );
}

export default function ConsoleMixer(props?: {
  onStateChange?: (state: ConsoleMixerState) => void;
  drumEngine?: DrumPlayerEngine | null;
}) {
  const onStateChange = props?.onStateChange;
  const drumEngine = props?.drumEngine ?? null;

  const viewportRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const [fitScale, setFitScale] = useState(1);
  const [needsHScroll, setNeedsHScroll] = useState(false);

  const [monoChannels, setMonoChannels] = useState<MonoChannel[]>([
    { id: "kick", name: "Kick", volume: 78, pan: 0, muted: false, solo: false, eq: false, sendOH: 0, sendRoom: 15 },
    { id: "kick_sub", name: "Kick Sub", volume: 70, pan: 0, muted: false, solo: false, eq: false, sendOH: 0, sendRoom: 15 },
    { id: "snare_top", name: "Snare Top", volume: 72, pan: 0, muted: false, solo: false, eq: false, sendOH: 15, sendRoom: 25 },
    { id: "snare_bottom", name: "Snare Bottom", volume: 64, pan: 0, muted: false, solo: false, eq: false, sendOH: 10, sendRoom: 18 },
    { id: "hat", name: "Hat", volume: 62, pan: -15, muted: false, solo: false, eq: false, sendOH: 10, sendRoom: 16 },
    { id: "tom1", name: "Tom 1", volume: 66, pan: -20, muted: false, solo: false, eq: false, sendOH: 10, sendRoom: 22 },
    { id: "tom2", name: "Tom 2", volume: 66, pan: -10, muted: false, solo: false, eq: false, sendOH: 10, sendRoom: 22 },
    { id: "tom3", name: "Tom 3", volume: 66, pan: 10, muted: false, solo: false, eq: false, sendOH: 10, sendRoom: 22 },
    { id: "tom4", name: "Tom 4", volume: 66, pan: 20, muted: false, solo: false, eq: false, sendOH: 10, sendRoom: 22 },
    { id: "tom5", name: "Tom 5", volume: 64, pan: 30, muted: false, solo: false, eq: false, sendOH: 10, sendRoom: 22 },
    { id: "ride", name: "Ride", volume: 58, pan: 25, muted: false, solo: false, eq: false, sendOH: 20, sendRoom: 15 },
    { id: "crash", name: "Crash", volume: 56, pan: 15, muted: false, solo: false, eq: false, sendOH: 30, sendRoom: 12 },
  ]);

  const [stereoChannels, setStereoChannels] = useState<StereoChannel[]>([
    { id: "oh", name: "OH", volume: 70, pan: 0, muted: false, solo: false, eq: false },
    { id: "room", name: "Room", volume: 50, pan: 0, muted: false, solo: false, eq: false },
  ]);

  const [masterVolume, setMasterVolume] = useState(85);

  useEffect(() => {
    if (!onStateChange) return;
    onStateChange({ monoChannels, stereoChannels, masterVolume });
  }, [monoChannels, stereoChannels, masterVolume, onStateChange]);

  const updateMonoChannel = (id: string, updates: Partial<MonoChannel>) => {
    setMonoChannels((prev) => prev.map((ch) => (ch.id === id ? { ...ch, ...updates } : ch)));
  };

  const updateStereoChannel = (id: string, updates: Partial<StereoChannel>) => {
    setStereoChannels((prev) => prev.map((ch) => (ch.id === id ? { ...ch, ...updates } : ch)));
  };

  const hasSolo = useMemo(() => {
    return monoChannels.some((c) => c.solo) || stereoChannels.some((c) => c.solo);
  }, [monoChannels, stereoChannels]);

  const [overallLevel, setOverallLevel] = useState(0);
  const [monoLevels, setMonoLevels] = useState<Record<string, number>>({});
  const [busLevels, setBusLevels] = useState<Record<string, number>>({});

  useEffect(() => {
    if (!drumEngine) {
      setOverallLevel(0);
      setMonoLevels({});
      setBusLevels({});
      return;
    }
    const interval = window.setInterval(() => {
      try {
        setOverallLevel(clamp(drumEngine.getMasterLevel01() * 100, 0, 100));

        setMonoLevels((prev) => {
          const next: Record<string, number> = { ...prev };
          for (const ch of monoChannels) {
            try {
              next[ch.id] = clamp(drumEngine.getChannelLevel01(ch.id as any) * 100, 0, 100);
            } catch {
              next[ch.id] = 0;
            }
          }
          return next;
        });

        setBusLevels({
          oh: clamp(drumEngine.getBusLevel01("oh") * 100, 0, 100),
          room: clamp(drumEngine.getBusLevel01("room") * 100, 0, 100),
        });
      } catch {
        setOverallLevel(0);
        setMonoLevels({});
        setBusLevels({});
      }
    }, 40);
    return () => window.clearInterval(interval);
  }, [drumEngine, monoChannels]);

  useEffect(() => {
    if (!drumEngine) return;

    for (const ch of monoChannels) {
      drumEngine.setChannelParams(ch.id as any, {
        gain: (ch.volume / 100) * 1.5,
        pan: clamp(ch.pan / 50, -1, 1),
        mute: Boolean(ch.muted),
        solo: Boolean(ch.solo),
        sendOh: clamp((ch.sendOH ?? 0) / 100, 0, 1),
        sendRoom: clamp((ch.sendRoom ?? 0) / 100, 0, 1),
      });
    }

    const hasBusSolo = stereoChannels.some((c) => c.solo);
    for (const bus of stereoChannels) {
      const busGain = (bus.volume / 100) * 1.5;
      const shouldMute = Boolean(bus.muted) || (hasBusSolo && !bus.solo);
      drumEngine.setBusGain(bus.id as any, shouldMute ? 0 : busGain);
    }

    drumEngine.setMasterGain((masterVolume / 100) * 1.5);
  }, [drumEngine, monoChannels, stereoChannels, masterVolume]);

  useEffect(() => {
    const MIN_SCALE = 0.75;
    const update = () => {
      const viewport = viewportRef.current;
      const content = contentRef.current;
      if (!viewport || !content) return;

      const available = viewport.clientWidth;
      const natural = content.scrollWidth;
      if (!available || !natural) return;

      const ratio = available / natural;
      const next = Math.max(MIN_SCALE, Math.min(1, ratio));
      setFitScale((prev) => (Math.abs(prev - next) < 0.01 ? prev : next));
      setNeedsHScroll(ratio < MIN_SCALE);
    };

    update();
    const ro = new ResizeObserver(() => update());
    if (viewportRef.current) ro.observe(viewportRef.current);
    if (contentRef.current) ro.observe(contentRef.current);

    return () => {
      ro.disconnect();
    };
  }, [monoChannels.length, stereoChannels.length]);

  return (
    <div className="bg-slate-950 w-full min-w-0">
      <div className="p-3 overflow-hidden">
        <div
          ref={viewportRef}
          className={needsHScroll ? "overflow-x-auto overflow-y-hidden" : "overflow-hidden"}
        >
          <div
            ref={contentRef}
            className="relative flex flex-nowrap gap-1 p-5 rounded-2xl"
            style={{
              transform: `scale(${fitScale})`,
              transformOrigin: "left top",
              background: "linear-gradient(165deg, #3a3a3a 0%, #1a1a1a 50%, #0a0a0a 100%)",
              boxShadow:
                "0 30px 60px -15px rgba(0, 0, 0, 0.9), inset 0 1px 0 rgba(255, 255, 255, 0.1), inset 0 -1px 0 rgba(0, 0, 0, 0.5)",
            }}
          >
          <div className="absolute top-3 left-3 w-3 h-3 rounded-full bg-gradient-to-br from-gray-500 to-gray-700 shadow-inner" />
          <div className="absolute top-3 right-3 w-3 h-3 rounded-full bg-gradient-to-br from-gray-500 to-gray-700 shadow-inner" />
          <div className="absolute bottom-3 left-3 w-3 h-3 rounded-full bg-gradient-to-br from-gray-500 to-gray-700 shadow-inner" />
          <div className="absolute bottom-3 right-3 w-3 h-3 rounded-full bg-gradient-to-br from-gray-500 to-gray-700 shadow-inner" />

          {monoChannels.map((channel) => (
            <MonoChannelStrip
              key={channel.id}
              channel={channel}
              level={monoLevels[channel.id] ?? 0}
              onUpdate={(updates) => updateMonoChannel(channel.id, updates)}
            />
          ))}

          <div className="w-px bg-gradient-to-b from-transparent via-gray-600 to-transparent mx-2 my-4" />

          {stereoChannels.map((channel) => (
            <StereoChannelStrip
              key={channel.id}
              channel={channel}
              level={busLevels[channel.id] ?? 0}
              onUpdate={(updates) => updateStereoChannel(channel.id, updates)}
            />
          ))}

          <div className="w-px bg-gradient-to-b from-transparent via-gray-600 to-transparent mx-2 my-4" />

          <MasterSection masterVolume={masterVolume} onMasterVolumeChange={setMasterVolume} overallLevel={overallLevel} />
          </div>
        </div>
      </div>
    </div>
  );
}
