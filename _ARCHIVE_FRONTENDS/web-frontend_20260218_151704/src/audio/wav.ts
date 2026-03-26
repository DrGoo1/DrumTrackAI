export function encodeWavFromAudioBuffer(buffer: AudioBuffer): Blob {
  const numChannels = buffer.numberOfChannels;
  const sampleRate = buffer.sampleRate;
  const length = buffer.length;

  const bytesPerSample = 2;
  const blockAlign = numChannels * bytesPerSample;
  const byteRate = sampleRate * blockAlign;
  const dataSize = length * blockAlign;

  const out = new ArrayBuffer(44 + dataSize);
  const view = new DataView(out);

  let offset = 0;
  const writeString = (s: string) => {
    for (let i = 0; i < s.length; i++) view.setUint8(offset + i, s.charCodeAt(i));
    offset += s.length;
  };

  writeString('RIFF');
  view.setUint32(offset, 36 + dataSize, true);
  offset += 4;
  writeString('WAVE');

  writeString('fmt ');
  view.setUint32(offset, 16, true);
  offset += 4;
  view.setUint16(offset, 1, true);
  offset += 2;
  view.setUint16(offset, numChannels, true);
  offset += 2;
  view.setUint32(offset, sampleRate, true);
  offset += 4;
  view.setUint32(offset, byteRate, true);
  offset += 4;
  view.setUint16(offset, blockAlign, true);
  offset += 2;
  view.setUint16(offset, 16, true);
  offset += 2;

  writeString('data');
  view.setUint32(offset, dataSize, true);
  offset += 4;

  const channels: Float32Array[] = [];
  for (let c = 0; c < numChannels; c++) channels.push(buffer.getChannelData(c));

  for (let i = 0; i < length; i++) {
    for (let c = 0; c < numChannels; c++) {
      const x = Math.max(-1, Math.min(1, channels[c][i] ?? 0));
      const s = x < 0 ? x * 0x8000 : x * 0x7fff;
      view.setInt16(offset, Math.round(s), true);
      offset += 2;
    }
  }

  return new Blob([out], { type: 'audio/wav' });
}

export async function renderEuclideanClicksToWav(
  events: Array<{ timeBeats: number; isAccent: boolean }>,
  tempo: number,
  opts?: { sampleRate?: number; clickGain?: number }
): Promise<Blob> {
  const sampleRate = opts?.sampleRate ?? 44100;
  const clickGain = opts?.clickGain ?? 0.22;

  const secPerBeat = 60 / Math.max(tempo, 1);
  const lastBeat = events.reduce((m, e) => Math.max(m, e.timeBeats), 0);
  const durationSec = Math.max(0.25, lastBeat * secPerBeat + 0.5);
  const length = Math.ceil(durationSec * sampleRate);

  const ctx = new OfflineAudioContext(2, length, sampleRate);
  const master = ctx.createGain();
  master.gain.value = 1;
  master.connect(ctx.destination);

  for (const ev of events) {
    const t0 = Math.max(0, ev.timeBeats * secPerBeat);

    const osc = ctx.createOscillator();
    const env = ctx.createGain();

    osc.type = 'sine';
    osc.frequency.value = ev.isAccent ? 1500 : 900;

    const dur = 0.03;
    const g = clickGain;

    env.gain.setValueAtTime(0.0001, t0);
    env.gain.exponentialRampToValueAtTime(g, t0 + 0.001);
    env.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);

    osc.connect(env);
    env.connect(master);

    osc.start(t0);
    osc.stop(t0 + dur + 0.01);
  }

  const rendered = await ctx.startRendering();
  return encodeWavFromAudioBuffer(rendered);
}
