import { create } from "zustand";

type TransportState = {
  playing: boolean;
  bpm: number;
  currentTime: number;  // seconds (engine clock)
  setPlaying: (v: boolean) => void;
  setBpm: (v: number) => void;
  setCurrentTime: (t: number) => void;
};

export const useTransportStore = create<TransportState>((set) => ({
  playing: false,
  bpm: 120,
  currentTime: 0,
  setPlaying: (v) => set({ playing: v }),
  setBpm: (v) => set({ bpm: v }),
  setCurrentTime: (t) => set({ currentTime: t }),
}));
