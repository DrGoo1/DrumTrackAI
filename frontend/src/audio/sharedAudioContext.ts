export type SharedAudioContextOptions = {
  latencyHint?: AudioContextLatencyCategory | number;
};

declare global {
  // eslint-disable-next-line no-var
  var __dtk_sharedAudioContext: AudioContext | undefined;
}

export function getSharedAudioContext(opts?: SharedAudioContextOptions): AudioContext {
  if (!globalThis.__dtk_sharedAudioContext) {
    const latencyHint = opts?.latencyHint ?? "interactive";
    globalThis.__dtk_sharedAudioContext = new AudioContext({ latencyHint });
  }
  return globalThis.__dtk_sharedAudioContext;
}

export async function resumeSharedAudioContext(): Promise<void> {
  const ctx = globalThis.__dtk_sharedAudioContext;
  if (!ctx) return;
  if (ctx.state === "suspended" || ctx.state === "interrupted") {
    await ctx.resume();
  }
}
