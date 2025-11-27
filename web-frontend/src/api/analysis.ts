import axios from 'axios'

const api = axios.create({ 
  baseURL: process.env.REACT_APP_API_BASE || 'http://localhost:8000' 
})

export async function fetchSongAnalytics(key: string) { 
  const { data } = await api.post('/analysis/song', { key })
  return data 
}

export async function fetchBassAnalysis(key: string) { 
  const { data } = await api.post('/analysis/bass', { key })
  return data 
}
