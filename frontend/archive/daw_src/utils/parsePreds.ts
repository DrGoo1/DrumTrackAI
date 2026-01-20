export type PredRow = { 
  time_s: number; 
  cls: string; 
  velocity?: number; 
  duration_s?: number; 
  confidence?: number 
}

export function parsePredsCsv(text: string): PredRow[] {
  const [header, ...rows] = text.trim().split(/\r?\n/)
  const cols = header.split(',').map(s => s.trim())
  const idx = (k: string) => cols.indexOf(k)
  const ti = idx('time_s')
  const ci = idx('class')
  const vi = idx('velocity')
  const di = idx('duration_s')
  const fi = idx('confidence')
  
  return rows.map(r => {
    const c = r.split(',')
    return {
      time_s: Number(c[ti] || 0),
      cls: (c[ci] || 'other').toLowerCase(),
      velocity: vi >= 0 ? Number(c[vi]) : undefined,
      duration_s: di >= 0 ? Number(c[di]) : undefined,
      confidence: fi >= 0 ? Number(c[fi]) : undefined,
    }
  }).filter(x => !Number.isNaN(x.time_s))
}
