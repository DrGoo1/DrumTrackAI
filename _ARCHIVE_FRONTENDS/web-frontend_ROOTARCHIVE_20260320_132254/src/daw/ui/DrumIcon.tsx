import React from "react"
import type { DrumKind } from "./drumKinds"

interface DrumIconProps {
  kind: DrumKind
  size?: number
  ghost?: boolean
  accent?: boolean
}

export const DrumIcon: React.FC<DrumIconProps> = ({
  kind,
  size = 14,
  ghost = false,
  accent = false,
}) => {
  const stroke = accent ? "#ff5555" : "#eeeeee"
  const fillBase = accent ? "#ff5555" : "#cccccc"
  const opacity = ghost ? 0.45 : 0.9

  const common = {
    width: size,
    height: size,
    viewBox: "0 0 16 16",
    style: { opacity },
  } as const

  switch (kind) {
    case "kick":
      return (
        <svg {...common}>
          <circle cx="8" cy="8" r="4.5" fill={fillBase} stroke={stroke} strokeWidth="1" />
        </svg>
      )
    case "snare":
      return (
        <svg {...common}>
          <polygon
            points="8,3 13,8 8,13 3,8"
            fill={fillBase}
            stroke={stroke}
            strokeWidth="1"
          />
        </svg>
      )
    case "tom":
      return (
        <svg {...common}>
          <polygon
            points="8,2.5 13.5,8 8,13.5 2.5,8"
            fill={fillBase}
            stroke={stroke}
            strokeWidth="0.8"
          />
        </svg>
      )
    case "hat_closed":
      return (
        <svg {...common}>
          <line x1="3" y1="8" x2="13" y2="8" stroke={stroke} strokeWidth="1.7" />
        </svg>
      )
    case "hat_open":
      return (
        <svg {...common}>
          <polyline
            points="3,11 8,5 13,11"
            fill="none"
            stroke={stroke}
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      )
    case "ride":
      return (
        <svg {...common}>
          <circle cx="8" cy="8" r="5.5" fill="none" stroke={stroke} strokeWidth="1.4" />
        </svg>
      )
    case "crash":
      return (
        <svg {...common}>
          <polygon
            points="8,3 13,13 3,13"
            fill={fillBase}
            stroke={stroke}
            strokeWidth="1"
          />
        </svg>
      )
    case "perc":
    default:
      return (
        <svg {...common}>
          <rect x="4" y="4" width="8" height="8" fill={fillBase} stroke={stroke} strokeWidth="1" />
        </svg>
      )
  }
}
