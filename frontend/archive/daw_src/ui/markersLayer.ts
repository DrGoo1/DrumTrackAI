import type { Marker } from '../state/dawStore'

const COLORS: Record<string, string> = { 
  kick: '#ef4444', 
  snare: '#3b82f6', 
  hh: '#f59e0b', 
  other: '#a3a3a3' 
}

export function drawMarkers(
  g: CanvasRenderingContext2D, 
  markers: Marker[], 
  pxPerSecond: number, 
  yTop: number, 
  yBottom: number
) {
  const h = yBottom - yTop
  for (const m of markers) {
    const x = Math.round(m.t * pxPerSecond) + 0.5
    g.strokeStyle = COLORS[m.cls] || COLORS.other
    g.beginPath()
    g.moveTo(x, yTop)
    g.lineTo(x, yBottom)
    g.stroke()
    
    // Optional: draw small head for high confidence
    if ((m.conf ?? 1) > 0.85) { 
      g.fillStyle = g.strokeStyle
      g.fillRect(x - 2, yTop, 4, 4) 
    }
  }
}

export function getMarkerColor(cls: string): string {
  return COLORS[cls] || COLORS.other
}
