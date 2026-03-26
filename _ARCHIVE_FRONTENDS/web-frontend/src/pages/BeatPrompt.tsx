import React, { useMemo, useState } from "react";
import {
  BeatboxTranslateResponse,
  BeatPromptSectionPayload,
  renderBeatPrompt,
} from "../services/api";
import { parsePromptIntent } from "../utils/promptParser";
import { PROMPT_SUGGESTIONS } from "../config/promptPresets";

const CTA_COPY = [
  "Describe the groove, we handle the drummer",
  "Mobile-first prompts with instant MIDI",
  "Jamstix personas locked in automatically",
];

const STATUS_LABELS: Record<"idle" | "loading" | "success" | "error", string> = {
  idle: "Ready",
  loading: "Generating",
  success: "Rendered",
  error: "Needs Attention",
};

function sectionToPayload(section: ReturnType<typeof parsePromptIntent>["sections"][number]): BeatPromptSectionPayload {
  return {
    label: section.label,
    bars: section.bars,
    tempo: section.tempo,
    meter: section.meter,
    persona_id: section.persona_id,
    style_pack: section.style_pack,
    pattern_template: section.pattern_template,
    modifiers: section.modifiers,
  };
}

export default function BeatPromptPage() {
  const [prompt, setPrompt] = useState("Pop-punk chorus with doubletime hats and a halftime bridge");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BeatboxTranslateResponse | null>(null);
  const [lastPayload, setLastPayload] = useState<BeatPromptSectionPayload[] | null>(null);

  const parsed = useMemo(() => parsePromptIntent(prompt), [prompt]);
  const generationDisabled = !parsed.sections.length || status === "loading";
  const midiHref = result?.preview_midi ? `data:audio/midi;base64,${result.preview_midi}` : undefined;

  const handleSuggestionClick = (suggestion: string) => {
    setPrompt(suggestion);
    setResult(null);
    setError(null);
    setStatus("idle");
  };

  const handleGenerate = async () => {
    if (!parsed.sections.length) {
      setError("Add at least one identifiable section before generating.");
      setStatus("error");
      return;
    }

    try {
      setStatus("loading");
      setError(null);
      const payload = parsed.sections.map(sectionToPayload);
      const response = await renderBeatPrompt({ prompt: parsed.prompt, sections: payload });
      setResult(response);
      setLastPayload(payload);
      setStatus("success");
    } catch (err) {
      setStatus("error");
      setError((err as Error).message || "Prompt rendering failed");
    }
  };

  const activeTimeline = (result as BeatboxTranslateResponse & { sections?: BeatPromptSectionPayload[] })?.sections || lastPayload || parsed.sections.map(sectionToPayload);

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-black text-slate-100">
      <div className="max-w-6xl mx-auto py-12 px-4 space-y-10">
        <header className="rounded-3xl border border-white/10 bg-gradient-to-r from-sky-900/60 via-indigo-900/40 to-purple-900/40 p-8 shadow-xl">
          <p className="text-xs uppercase tracking-[0.4em] text-sky-200">BeatPrompt</p>
          <h1 className="mt-3 text-4xl font-bold text-white">Type a vibe, get a groove</h1>
          <p className="mt-3 text-slate-200 max-w-3xl">
            Craft a plain-language request like “pop-punk chorus with doubletime hats” and DrumTracKAI instantly maps it
            to personas, templates, and Jamstix-ready MIDI that plays back on any phone.
          </p>
          <div className="mt-4 flex flex-wrap gap-3 text-xs font-semibold tracking-wide text-slate-300">
            {CTA_COPY.map((line) => (
              <span key={line} className="rounded-full border border-white/15 px-3 py-1 bg-white/5">
                {line}
              </span>
            ))}
          </div>
        </header>

        <section className="grid gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
          <div className="rounded-3xl border border-white/10 bg-white/5 backdrop-blur-xl p-6 space-y-6">
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Starter Prompts</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {PROMPT_SUGGESTIONS.map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => handleSuggestionClick(suggestion)}
                    className="rounded-full border border-white/15 px-3 py-1 text-xs text-slate-200 hover:bg-white/10"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-semibold text-white">Describe the groove</label>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                rows={4}
                className="mt-2 w-full rounded-3xl border border-white/15 bg-black/40 px-4 py-3 text-base text-slate-100 focus:outline-none focus:ring-2 focus:ring-sky-400"
                placeholder="Pop punk chorus, halftime bridge, trap verse"
              />
              <p className="mt-2 text-xs text-slate-400">Mobile tip: short phrases split by commas or new lines work best.</p>
            </div>

            {parsed.keywords.length > 0 && (
              <div>
                <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Detected Motifs</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {parsed.keywords.map((keyword) => (
                    <span key={keyword} className="rounded-full bg-slate-900/60 px-3 py-1 text-xs text-slate-200 border border-slate-700/60">
                      {keyword}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {!!parsed.warnings.length && (
              <div className="rounded-2xl border border-yellow-500/40 bg-yellow-500/10 px-4 py-3 text-sm text-yellow-100">
                {parsed.warnings.join(" ")}
              </div>
            )}

            <div className="space-y-3">
              <div className="flex items-center justify-between text-sm text-slate-300">
                <span>Interpreted Sections</span>
                <span>{parsed.sections.length} planned</span>
              </div>

              {parsed.sections.length === 0 && (
                <div className="rounded-2xl border border-dashed border-white/15 p-4 text-sm text-slate-400">
                  Add section keywords (chorus, bridge, verse) plus genres to see them here.
                </div>
              )}

              {parsed.sections.length > 0 && (
                <ul className="space-y-3">
                  {parsed.sections.map((section, idx) => (
                    <li key={section.id} className="rounded-2xl border border-white/15 bg-black/30 p-4">
                      <div className="flex items-center justify-between text-sm font-semibold text-white">
                        <span>
                          {idx + 1}. {section.label}
                        </span>
                        <span className="text-xs text-slate-400">{section.meter}</span>
                      </div>
                      <p className="mt-2 text-xs text-slate-400">{section.rawText}</p>
                      <div className="mt-3 grid gap-2 text-xs text-slate-300 sm:grid-cols-2">
                        <span>BPM · {section.tempo}</span>
                        <span>Bars · {section.bars}</span>
                        <span>Persona · {section.persona_id}</span>
                        <span>Style · {section.style_pack}</span>
                      </div>
                      {section.modifiers.length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-2 text-[11px]">
                          {section.modifiers.map((modifier) => (
                            <span key={modifier} className="rounded-full bg-white/10 px-2 py-0.5 text-slate-200">
                              {modifier}
                            </span>
                          ))}
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          <div className="rounded-3xl border border-white/10 bg-gradient-to-b from-slate-900/80 to-black/70 p-6 space-y-6">
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Status</p>
              <div className="mt-2 flex items-center justify-between">
                <span className="text-lg font-semibold text-white">{STATUS_LABELS[status]}</span>
                <span className="text-xs text-slate-400">BeatPrompt pipeline</span>
              </div>
              {error && <p className="mt-2 text-sm text-red-200">{error}</p>}
            </div>

            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Timeline</p>
              <div className="mt-3 space-y-2">
                {activeTimeline.length === 0 && (
                  <p className="text-sm text-slate-400">Sections will appear after parsing.</p>
                )}
                {activeTimeline.map((section, idx) => (
                  <div key={`${section.label}-${idx}`} className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-semibold text-white">{section.label}</span>
                      <span className="text-xs text-slate-400">{section.bars} bars</span>
                    </div>
                    <div className="mt-1 flex flex-wrap gap-3 text-xs text-slate-300">
                      <span>{section.tempo} BPM</span>
                      <span>{section.persona_id}</span>
                      {section.modifiers?.length ? <span>{section.modifiers.join(" · ")}</span> : null}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <button
              onClick={handleGenerate}
              disabled={generationDisabled}
              className="w-full rounded-3xl bg-gradient-to-r from-sky-500 to-indigo-500 px-4 py-3 font-semibold tracking-wide disabled:opacity-30"
            >
              {status === "loading" ? "Generating Groove…" : "Generate Groove"}
            </button>

            <p className="text-xs text-slate-400">
              We send the parsed sections to `/api/beatprompt/render`, which returns the same payload as Beat Sketch, so you
              get MIDI previews, Jamstix enrichment, and persona fidelity automatically.
            </p>
          </div>
        </section>

        {result && (
          <section className="rounded-3xl border border-white/10 bg-gradient-to-br from-slate-900/80 via-black/80 to-purple-950/60 p-6 space-y-4 shadow-2xl">
            <div className="flex flex-wrap items-center gap-4 text-sm text-slate-200">
              <span>
                Tempo: <strong>{result.tempo.toFixed(1)} BPM</strong>
              </span>
              <span>
                Hits generated: <strong>{result.hits.length}</strong>
              </span>
              {result.summary && (
                <span>
                  {Object.entries(result.summary)
                    .map(([k, v]) => `${k}: ${v}`)
                    .join(" · ")}
                </span>
              )}
              {midiHref && (
                <a href={midiHref} download="beatprompt.mid" className="text-sky-300 underline">
                  Download MIDI
                </a>
              )}
            </div>

            <div className="max-h-64 overflow-auto rounded-2xl border border-white/10 bg-black/30 text-sm">
              <table className="w-full text-left">
                <thead className="bg-white/5 text-xs uppercase tracking-wide text-slate-400">
                  <tr>
                    <th className="px-3 py-2">Hit</th>
                    <th className="px-3 py-2">Beat</th>
                    <th className="px-3 py-2">Time (s)</th>
                    <th className="px-3 py-2">Velocity</th>
                    <th className="px-3 py-2">Conf.</th>
                  </tr>
                </thead>
                <tbody>
                  {result.hits.map((hit, idx) => (
                    <tr key={`${hit.instrument}-${idx}`} className="odd:bg-white/5">
                      <td className="px-3 py-2 capitalize">{hit.instrument}</td>
                      <td className="px-3 py-2">{hit.beat_position.toFixed(3)}</td>
                      <td className="px-3 py-2">{hit.time.toFixed(3)}</td>
                      <td className="px-3 py-2">{hit.velocity}</td>
                      <td className="px-3 py-2">{hit.confidence.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
