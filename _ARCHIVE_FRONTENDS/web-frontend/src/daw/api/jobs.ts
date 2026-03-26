import { api } from './api'

export async function presignedGet(key: string): Promise<string> {
  const { data } = await api.post('/files/download-url', { key })
  return data.url as string
}

export async function loadMarkersForTrack(trackId: string, jobId: string) {
  const { useDawStore } = await import('../state/dawStore')
  const { parsePredsCsv } = await import('../utils/parsePreds')
  
  try {
    const key = `jobs/${jobId}/preds.csv`
    const url = await presignedGet(key)
    const text = await (await fetch(url)).text()
    const rows = parsePredsCsv(text)
    const markers = rows.map(r => ({ 
      t: r.time_s, 
      cls: (r.cls as any) || 'other', 
      conf: r.confidence, 
      dur: r.duration_s 
    }))
    useDawStore.getState().setTrackMarkers(trackId, markers)
  } catch (error) {
    console.error('Failed to load markers for track:', error)
  }
}
