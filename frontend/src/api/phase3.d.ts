// src/api/phase3.d.ts
export const api: any;
export function getUploadUrl(key: string): Promise<string>;
export function getDownloadUrl(key: string): Promise<string>;
export function uploadViaBackend(key: string, file: File): Promise<void>;
export function uploadFileSmart(file: File): Promise<string>;
