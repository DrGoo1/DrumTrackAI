export type PromptTemplate = {
  id: string;
  displayName: string;
  tokens: string[];
  defaultSectionLabel: string;
  defaultBars: number;
  defaultTempo: number;
  defaultMeter: string;
  personaId: string;
  stylePack: string;
  patternTemplate: string;
  defaultModifiers?: string[];
};

export const PROMPT_TEMPLATES: PromptTemplate[] = [
  {
    id: "pop_punk_chorus",
    displayName: "Pop-Punk Anthem",
    tokens: ["pop punk", "pop-punk", "punk rock"],
    defaultSectionLabel: "Chorus",
    defaultBars: 8,
    defaultTempo: 170,
    defaultMeter: "4/4",
    personaId: "arena_rock_captain",
    stylePack: "pop_punk_energy",
    patternTemplate: "chorus_pop_punk",
    defaultModifiers: ["doubletime hats"],
  },
  {
    id: "pop_punk_verse",
    displayName: "Pop-Punk Verse",
    tokens: ["punk verse", "emo verse"],
    defaultSectionLabel: "Verse",
    defaultBars: 8,
    defaultTempo: 160,
    defaultMeter: "4/4",
    personaId: "arena_rock_captain",
    stylePack: "pop_punk_energy",
    patternTemplate: "verse_pop_punk",
  },
  {
    id: "motown_68_ballad",
    displayName: "Motown 6/8",
    tokens: ["motown", "6/8", "six eight", "soul ballad"],
    defaultSectionLabel: "Chorus",
    defaultBars: 8,
    defaultTempo: 92,
    defaultMeter: "6/8",
    personaId: "neo_soul_guru",
    stylePack: "neo_soul_pocket",
    patternTemplate: "motown_ballad",
    defaultModifiers: ["brushes"],
  },
  {
    id: "neo_soul_pocket",
    displayName: "Neo-Soul Pocket",
    tokens: ["neo soul", "r&b pocket", "dilla"],
    defaultSectionLabel: "Verse",
    defaultBars: 8,
    defaultTempo: 94,
    defaultMeter: "4/4",
    personaId: "neo_soul_guru",
    stylePack: "neo_soul_pocket",
    patternTemplate: "neo_soul_verse",
    defaultModifiers: ["laid back", "ghost notes"],
  },
  {
    id: "trap_verse",
    displayName: "Trap Verse",
    tokens: ["trap", "808", "triplet hats"],
    defaultSectionLabel: "Verse",
    defaultBars: 8,
    defaultTempo: 142,
    defaultMeter: "4/4",
    personaId: "alt_glitch_curator",
    stylePack: "alt_glitch_half_time",
    patternTemplate: "verse_trap",
    defaultModifiers: ["triplet hats", "808 kicks"],
  },
  {
    id: "alt_halftime",
    displayName: "Alt Halftime",
    tokens: ["halftime", "alt bridge", "heavy bridge"],
    defaultSectionLabel: "Bridge",
    defaultBars: 4,
    defaultTempo: 85,
    defaultMeter: "4/4",
    personaId: "alt_glitch_curator",
    stylePack: "alt_glitch_half_time",
    patternTemplate: "bridge_halftime",
    defaultModifiers: ["wide hats"],
  },
  {
    id: "disco_floor",
    displayName: "Disco Floor",
    tokens: ["disco", "four on the floor", "70s dance"],
    defaultSectionLabel: "Chorus",
    defaultBars: 8,
    defaultTempo: 124,
    defaultMeter: "4/4",
    personaId: "arena_rock_captain",
    stylePack: "disco_floor",
    patternTemplate: "chorus_disco",
    defaultModifiers: ["four on the floor"],
  },
  {
    id: "dnb_roll",
    displayName: "Drum-n-Bass",
    tokens: ["drum and bass", "dnb", "jungle"],
    defaultSectionLabel: "Drop",
    defaultBars: 8,
    defaultTempo: 172,
    defaultMeter: "4/4",
    personaId: "alt_glitch_curator",
    stylePack: "dnb_rolls",
    patternTemplate: "drop_dnb",
  },
];

export const PROMPT_SUGGESTIONS = [
  "Pop-punk chorus with doubletime hats",
  "Motown 6/8 ballad with brushes",
  "Trap verse with 808 kicks and triplet hats",
  "Disco four-on-the-floor pre-chorus",
  "Neo-soul verse with laid back ghost notes",
  "Halftime bridge that drops into an anthemic chorus",
];
