// In modern Chrome, WebCodecs is available in Workers; we feature-detect.
// Fallback: signal the UI to use decodeAudioData.

export type DecodeReq = { id: string; fileType?: string; data: ArrayBuffer };
export type DecodeResp = { id: string; ok: boolean; pcm?: Float32Array; sampleRate?: number; error?: string };

// React Scripts compatible worker context
const ctx: Worker = self as any;

ctx.onmessage = async (e: MessageEvent) => {
  const { id, data } = e.data;
  try {
    const AudioDecoderCtor = (globalThis as any).AudioDecoder;
    if (typeof AudioDecoderCtor === "undefined") {
      ctx.postMessage({ id, ok: false, error: "no-webcodecs" } satisfies DecodeResp);
      return;
    }
    // Minimal WAV/MP3 handling requires container demuxing; in practice you'll
    // want a lightweight demuxer. Placeholder here: let the main thread fallback.
    ctx.postMessage({ id, ok: false, error: "need-demuxer" } satisfies DecodeResp);
  } catch (err: any) {
    ctx.postMessage({ id, ok: false, error: String(err) } satisfies DecodeResp);
  }
};
