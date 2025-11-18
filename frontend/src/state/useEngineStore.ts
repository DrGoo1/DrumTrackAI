import { create } from "zustand";

type EngineState = {
  underruns: number;
  renderLatencyMs: number;
  setUnderruns: (n: number) => void;
  setRenderLatencyMs: (n: number) => void;
};

export const useEngineStore = create<EngineState>((set) => ({
  underruns: 0,
  renderLatencyMs: 0,
  setUnderruns: (n) => set({ underruns: n }),
  setRenderLatencyMs: (n) => set({ renderLatencyMs: n }),
}));
