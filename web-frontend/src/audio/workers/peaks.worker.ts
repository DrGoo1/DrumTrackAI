export type PeaksReq = { id: string; pcm: Float32Array; levels: number[] };
export type PeaksResp = { id: string; tiles: Record<string, { min: Float32Array; max: Float32Array }> };

// React Scripts compatible worker context
const ctx: Worker = self as any;

ctx.onmessage = (e: MessageEvent) => {
  const { id, pcm, levels } = e.data;
  const tiles: Record<string, { min: Float32Array; max: Float32Array }> = {};

  for (const dec of levels) {
    const step = dec; // e.g., 64 or 512 samples per point
    const len = Math.ceil(pcm.length / step);
    const min = new Float32Array(len);
    const max = new Float32Array(len);
    for (let i = 0; i < len; i++) {
      let lo = 1.0, hi = -1.0;
      const start = i * step;
      const end = Math.min(start + step, pcm.length);
      for (let j = start; j < end; j++) {
        const v = pcm[j];
        if (v < lo) lo = v;
        if (v > hi) hi = v;
      }
      min[i] = lo; max[i] = hi;
    }
    tiles[`1:${step}`] = { min, max };
  }
  postMessage({ id, tiles } as PeaksResp);
};
