// web-frontend/src/api/phase3.ts
import axios from "axios";

export const api = axios.create({
  baseURL: process.env.REACT_APP_API_BASE || "http://localhost:8000",
  withCredentials: false,
});

// Presigned PUT (used when it works)
export async function getUploadUrl(key: string): Promise<string> {
  const { data } = await api.post("/files/upload-url", { key });
  return data.url as string;
}

// Presigned GET (for downloads/waveform/debug)
export async function getDownloadUrl(key: string): Promise<string> {
  const { data } = await api.post("/files/download-url", { key });
  return data.url as string;
}

// Direct upload fallback (streams through backend)
export async function uploadViaBackend(key: string, file: File): Promise<void> {
  const form = new FormData();
  form.append("key", key);
  form.append("f", file, file.name);
  await api.post("/files/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
    maxBodyLength: Infinity,
  });
}

// Smart uploader: try presigned briefly, then fallback
export async function uploadFileSmart(file: File): Promise<string> {
  const safe = file.name.replace(/[^\w.-]+/g, "_");
  const key = `uploads/${Date.now()}-${safe}`;
  try {
    const url = await getUploadUrl(key);
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort("presigned-timeout"), 2000);
    const res = await fetch(url, { method: "PUT", body: file, signal: ctrl.signal });
    clearTimeout(timer);
    if (!res.ok) throw new Error(`presigned PUT failed: ${res.status}`);
    return key;
  } catch {
    await uploadViaBackend(key, file);
    return key;
  }
}
