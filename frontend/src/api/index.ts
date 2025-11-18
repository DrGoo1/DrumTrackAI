// src/api/index.ts
import axios from "axios";

const API_BASE =
  (window as any).__API_BASE__?.replace(/\/$/, "") ||
  (process.env.REACT_APP_API_BASE || "http://localhost:8000").replace(/\/$/, "");

export const api = axios.create({ baseURL: API_BASE, withCredentials: false });

export async function ping() {
  const { data } = await api.get("/healthz"); // NOTE: no /api prefix
  return data;
}
