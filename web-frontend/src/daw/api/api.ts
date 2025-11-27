// Simple API client for DAW backend
const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000'

export const api = {
  async get(path: string) {
    const response = await fetch(`${API_BASE}${path}`)
    if (!response.ok) throw new Error(`GET ${path} failed: ${response.statusText}`)
    return { data: await response.json() }
  },

  async post(path: string, body?: any) {
    const response = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined
    })
    if (!response.ok) throw new Error(`POST ${path} failed: ${response.statusText}`)
    return { data: await response.json() }
  },

  async put(path: string, body?: any) {
    const response = await fetch(`${API_BASE}${path}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined
    })
    if (!response.ok) throw new Error(`PUT ${path} failed: ${response.statusText}`)
    return { data: await response.json() }
  }
}
