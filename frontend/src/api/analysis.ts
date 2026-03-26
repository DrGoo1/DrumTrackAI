import axios from 'axios'
import { resolveApiBase } from '../utils/apiBase'

const api = axios.create({ 
  baseURL: resolveApiBase() 
})

export async function fetchSongAnalytics(key: string) { 
  const { data } = await api.post('/analysis/song', { key })
  return data 
}

export async function fetchBassAnalysis(key: string) { 
  const { data } = await api.post('/analysis/bass', { key })
  return data 
}
