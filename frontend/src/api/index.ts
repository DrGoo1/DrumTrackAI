// src/api/index.ts
import axios from "axios";
import { resolveApiBaseNormalized } from "../utils/apiBase";

const API_BASE = resolveApiBaseNormalized();

export const api = axios.create({ baseURL: API_BASE, withCredentials: false });

export async function ping() {
  const { data } = await api.get("/healthz"); // NOTE: no /api prefix
  return data;
}
