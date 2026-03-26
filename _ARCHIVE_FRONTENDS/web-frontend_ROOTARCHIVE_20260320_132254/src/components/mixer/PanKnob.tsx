import React, { useState } from 'react'

export default function PanKnob({ value, onChange, size = 44 }: { value: number; onChange: (v: number) => void; size?: number }) {
  const [drag, setDrag] = useState<{ y: number, v: number } | null>(null)
  const min = -1, max = 1, r = size / 2
  const a0 = -140 * Math.PI / 180, a1 = 140 * Math.PI / 180
  const norm = (v: number) => (v - min) / (max - min)
  const den = (n: number) => min + n * (max - min)
  const ang = (v: number) => a0 + norm(v) * (a1 - a0)
  
  const onDown = (e: React.PointerEvent) => { 
    (e.target as Element).setPointerCapture(e.pointerId); 
    setDrag({ y: e.clientY, v: value }) 
  }
  const onMove = (e: React.PointerEvent) => { 
    if (!drag) return; 
    const dy = drag.y - e.clientY; 
    const n0 = norm(drag.v); 
    const n1 = Math.min(1, Math.max(0, n0 + dy * 0.003)); 
    onChange(den(n1)) 
  }
  const onUp = () => setDrag(null)
  
  const a = ang(value), cx = r, cy = r
  
  return (
    <svg width={size} height={size} onPointerDown={onDown} onPointerMove={onMove} onPointerUp={onUp} className="cursor-ns-resize select-none">
      <defs>
        <linearGradient id="k" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#cbd5e1" />
          <stop offset="100%" stopColor="#64748b" />
        </linearGradient>
      </defs>
      <circle cx={cx} cy={cy} r={r - 1} fill="url(#k)" stroke="#0f172a" />
      <circle cx={cx} cy={cy} r={r - 6} fill="#0b1220" />
      <path d={`M ${cx + (r - 8) * Math.cos(a0)} ${cy + (r - 8) * Math.sin(a0)} A ${r - 8} ${r - 8} 0 1 1 ${cx + (r - 8) * Math.cos(a1)} ${cy + (r - 8) * Math.sin(a1)}`} fill="none" stroke="#334155" strokeWidth={3} />
      <line x1={cx} y1={cy} x2={cx + (r - 10) * Math.cos(a)} y2={cy + (r - 10) * Math.sin(a)} stroke="#10b981" strokeWidth={3} strokeLinecap="round" />
    </svg>
  )
}
