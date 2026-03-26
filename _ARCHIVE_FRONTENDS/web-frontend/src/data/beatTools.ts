import { Mic, Drum, Music3 } from "lucide-react";

export type BeatTool = {
  id: string;
  label: string;
  description: string;
  accent: string;
  icon: typeof Mic;
  cta: string;
};

export const beatTools: BeatTool[] = [
  {
    id: "sketch",
    label: "BeatSketch",
    description: "Type or tap combinations to preview grooves instantly—perfect for lyricists and arrangers.",
    accent: "from-amber-400 via-amber-300 to-rose-300",
    icon: Mic,
    cta: "/beat-prompt?surface=text",
  },
  {
    id: "pad",
    label: "BeatPad",
    description: "Tap neon pads with multi-touch velocity tracking to block out kick, snare, and hat ideas.",
    accent: "from-sky-400 via-cyan-400 to-emerald-400",
    icon: Drum,
    cta: "/beat-sketch?mode=pads",
  },
  {
    id: "sing",
    label: "BeatSing",
    description: "Hum or sing rhythms and let DrumTracKAI interpret them into clean drum hits.",
    accent: "from-violet-400 via-purple-500 to-fuchsia-500",
    icon: Music3,
    cta: "/beat-sketch?mode=sing",
  },
];
