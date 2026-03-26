import React from "react"

interface KnobCircleProps {
  label: string
  value: number // 0..1
  onChange?: (v: number) => void
}

export const KnobCircle: React.FC<KnobCircleProps> = ({ label, value, onChange }) => {
  const clamped = Math.max(0, Math.min(1, value))
  const size = 44
  const radius = 18
  const barCount = 10
  const activeBars = Math.round(clamped * barCount)

  const bars: React.ReactElement[] = []
  for (let i = 0; i < barCount; i++) {
    const angle = (-120 + (240 * i) / (barCount - 1)) * (Math.PI / 180)
    const innerR = radius - 4
    const outerR = radius + 1
    const x1 = size / 2 + innerR * Math.cos(angle)
    const y1 = size / 2 + innerR * Math.sin(angle)
    const x2 = size / 2 + outerR * Math.cos(angle)
    const y2 = size / 2 + outerR * Math.sin(angle)
    const active = i < activeBars
    const color = active ? "#4ade80" : "#374151"

    bars.push(
      <line
        key={i}
        x1={x1}
        y1={y1}
        x2={x2}
        y2={y2}
        stroke={color}
        strokeWidth={1.5}
        strokeLinecap="round"
      />
    )
  }

  const handleClick = () => {
    if (!onChange) return
    // simple stepped increment; wrap around at 1.0
    const step = 0.1
    const next = clamped + step > 1 ? 0 : clamped + step
    onChange(Number(next.toFixed(2)))
  }

  return (
    <div
      className="flex flex-col items-center justify-center text-[10px] text-neutral-300 cursor-pointer select-none"
      onClick={handleClick}
    >
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="#020617"
          stroke="#4b5563"
          strokeWidth={1}
        />
        {bars}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={7}
          fill="#020617"
          stroke="#6b7280"
          strokeWidth={1}
        />
      </svg>
      <div className="mt-0.5 uppercase tracking-wide">{label}</div>
      <div className="text-[9px] text-emerald-300">{Math.round(clamped * 100)}%</div>
    </div>
  )
}
