import { PROMPT_TEMPLATES, PromptTemplate } from "../config/promptPresets";

export type PromptSectionIntent = {
  id: string;
  label: string;
  bars: number;
  tempo: number;
  meter: string;
  persona_id: string;
  style_pack: string;
  pattern_template: string;
  modifiers: string[];
  rawText: string;
  confidence: number;
};

export type PromptIntent = {
  prompt: string;
  sections: PromptSectionIntent[];
  keywords: string[];
  warnings: string[];
};

const SECTION_KEYWORDS = [
  "intro",
  "verse",
  "pre-chorus",
  "chorus",
  "hook",
  "bridge",
  "drop",
  "breakdown",
  "outro",
];

const MODIFIER_KEYWORDS: Array<{ label: string; patterns: string[] }> = [
  { label: "doubletime hats", patterns: ["doubletime", "double-time", "double time"] },
  { label: "triplet hats", patterns: ["triplet hat", "triplet hi-hat", "triplet hats"] },
  { label: "ghost notes", patterns: ["ghost note", "ghosted"] },
  { label: "brushes", patterns: ["brush", "brushes"] },
  { label: "anthemic", patterns: ["anthem", "anthemic"] },
  { label: "half-time", patterns: ["half time", "half-time"] },
  { label: "four on the floor", patterns: ["four on the floor", "4-on-the-floor"] },
  { label: "wide hats", patterns: ["wide hat", "open hat"] },
  { label: "808 kicks", patterns: ["808", "sub kick"] },
];

const TEMPO_WORD_PRESETS: Record<string, number> = {
  slow: 72,
  chill: 84,
  laid: 92,
  medium: 108,
  steady: 116,
  upbeat: 128,
  fast: 150,
  frantic: 172,
};

const DEFAULT_PERSONA = "neo_soul_guru";
const DEFAULT_STYLE = "neo_soul_pocket";

const SEGMENT_SPLIT_REGEX = /(?:\?|\.|\n|,|;|->|\band\b|\bthen\b)+/i;

function normalize(str: string) {
  return str.toLowerCase();
}

function pickTemplate(segment: string): PromptTemplate | undefined {
  const normalized = normalize(segment);
  return PROMPT_TEMPLATES.find((template) =>
    template.tokens.some((token) => normalized.includes(token)),
  );
}

function extractNumber(regex: RegExp, text: string): number | undefined {
  const match = text.match(regex);
  if (match && match[1]) {
    const value = parseInt(match[1], 10);
    if (!Number.isNaN(value)) {
      return value;
    }
  }
  return undefined;
}

function detectTempo(segment: string, templateTempo?: number): number {
  const normalized = normalize(segment);
  const numberTempo = extractNumber(/(\d{2,3})\s*(?:bpm|beats|tempo)?/i, segment);
  if (numberTempo) {
    return numberTempo;
  }

  for (const [token, tempo] of Object.entries(TEMPO_WORD_PRESETS)) {
    if (normalized.includes(token)) {
      return tempo;
    }
  }

  let tempo = templateTempo || 110;
  if (normalized.includes("half time") || normalized.includes("half-time")) {
    tempo = Math.max(60, Math.round((templateTempo || tempo) / 2));
  }
  if (normalized.includes("double time") || normalized.includes("double-time")) {
    tempo = Math.min(190, Math.round((templateTempo || tempo) * 2));
  }
  return tempo;
}

function detectBars(segment: string, fallback: number): number {
  return extractNumber(/(\d{1,2})\s*(?:bars?|measures?)/i, segment) || fallback;
}

function detectSectionLabel(segment: string, fallback: string): string {
  const normalized = normalize(segment);
  const match = SECTION_KEYWORDS.find((key) => normalized.includes(key));
  if (match) {
    if (match === "pre-chorus") {
      return "Pre-Chorus";
    }
    return match
      .split(" ")
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ");
  }
  return fallback;
}

function detectModifiers(segment: string, defaultModifiers: string[] = []): string[] {
  const normalized = normalize(segment);
  const modifiers = [...defaultModifiers];
  MODIFIER_KEYWORDS.forEach(({ label, patterns }) => {
    if (patterns.some((pattern) => normalized.includes(pattern))) {
      modifiers.push(label);
    }
  });
  return Array.from(new Set(modifiers));
}

export function parsePromptIntent(prompt: string): PromptIntent {
  const trimmed = prompt.trim();
  if (!trimmed) {
    return { prompt: "", sections: [], keywords: [], warnings: ["Describe a groove to get started."] };
  }

  const rawSegments = trimmed
    .split(SEGMENT_SPLIT_REGEX)
    .map((segment) => segment.trim())
    .filter(Boolean);

  const sections: PromptSectionIntent[] = [];
  const keywords = new Set<string>();
  const warnings: string[] = [];

  rawSegments.forEach((segment, idx) => {
    const template = pickTemplate(segment);
    const label = detectSectionLabel(segment, template?.defaultSectionLabel || `Section ${idx + 1}`);
    const bars = detectBars(segment, template?.defaultBars || 8);
    const tempo = detectTempo(segment, template?.defaultTempo);
    const modifiers = detectModifiers(segment, template?.defaultModifiers || []);

    if (template) {
      keywords.add(template.displayName);
    }
    SECTION_KEYWORDS.forEach((keyword) => {
      if (normalize(segment).includes(keyword)) {
        keywords.add(keyword.replace(/-/g, " "));
      }
    });

    sections.push({
      id: `${idx}-${template?.id || "custom"}`,
      label,
      bars,
      tempo,
      meter: template?.defaultMeter || "4/4",
      persona_id: template?.personaId || DEFAULT_PERSONA,
      style_pack: template?.stylePack || DEFAULT_STYLE,
      pattern_template: template?.patternTemplate || `custom_${idx + 1}`,
      modifiers,
      rawText: segment,
      confidence: template ? 0.9 : 0.5,
    });
  });

  if (!sections.length) {
    warnings.push("We could not detect any sections. Try adding words like 'chorus', 'bridge', or 'verse'.");
  }

  return {
    prompt: trimmed,
    sections,
    keywords: Array.from(keywords),
    warnings,
  };
}
