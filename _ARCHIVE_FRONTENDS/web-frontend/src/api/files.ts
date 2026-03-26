// src/api/files.ts
import { api } from "./index";

/** 1) Ask backend for a MinIO presigned PUT URL */
export async function getPresigned(key: string) {
  const { data } = await api.post("/files/upload-url", { key });
  // backend returns { url: "http://127.0.0.1:9000/dtai-dev/..." }
  return data.url as string;
}

/** 2) Direct upload to backend (multipart) — no CORS issues */
export async function uploadDirect(file: File, key: string, onProgress?: (p:number)=>void) {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("key", key);
  const { data } = await api.post("/files/upload", fd, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: e => e.total && onProgress?.(e.loaded / e.total),
  });
  // backend returns { ok:true, key, httpUrl }
  return data;
}

/** 3) Smart uploader: try presigned PUT (MinIO), else fallback to direct POST */
export async function uploadFileSmart(file: File, key: string, onProgress?: (p:number)=>void) {
  try {
    const url = await getPresigned(key);
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 2000);
    const res = await fetch(url, { method: "PUT", body: file, signal: ctrl.signal });
    clearTimeout(t);
    if (!res.ok) throw new Error("presigned failed " + res.status);
    onProgress?.(1);
    return { ok: true, key, httpUrl: url.split("?")[0] };
  } catch {
    // <— Your 405 was here because a previous version tried PUT /files/upload
    return uploadDirect(file, key, onProgress);
  }
}

/** 4) Fetch waveform peaks from backend */
export async function fetchWaveform(key: string, maxPoints?: number) {
  const params: any = { key };
  if (maxPoints) params.max_points = maxPoints;
  const { data } = await api.get("/files/waveform", { params });
  // backend returns { sr:number, peaks:number[] }
  return data.peaks;
}

/** 5) Get download URL for a file */
export async function getDownloadUrl(key: string): Promise<string> {
  const { data } = await api.get("/files/download-url", { params: { key } });
  return data.url;
}
