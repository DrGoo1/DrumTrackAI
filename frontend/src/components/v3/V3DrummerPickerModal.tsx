import React, { useEffect, useMemo, useRef, useState } from "react";
import { useV3Store } from "../../state/v3/store";
import { resolveApiBaseNormalized } from "../../utils/apiBase";

type DrummerCard = {
  id: string;
  display_name: string;
  tagline?: string;
  genre_tags?: string[];
  style?: string;
  difficulty?: string;
  icon?: string;
  color?: string;
  description?: string;
};

type PresetItem = {
  preset_id?: string;
  presetId?: string;
  tier?: "song" | "flavor" | "utility";
};

function normalizeProfileType(d: DrummerCard | null | undefined): string {
  const raw =
    String((d as any)?.style || "").trim() ||
    String((d as any)?.styleGroup || "").trim() ||
    String((d as any)?.style_group || "").trim() ||
    String((d as any)?.profileType || "").trim() ||
    String((d as any)?.profile_type || "").trim();
  const s = raw.toLowerCase().replace(/[\/|,]+/g, " ");
  if (!s) return "";
  const normalized = s.replace(/\s+/g, "_").replace(/[^a-z0-9_\-]/g, "");
  const primary = normalized.split(/[_\-]+/g).filter(Boolean)[0] || "";
  return primary || normalized;
}

function pickDefaultPresetStack(items: PresetItem[]): Array<{ presetId: string; tier: "song" | "flavor" | "utility"; intensity: number }> {
  const usable = (items || [])
    .map((p) => {
      const id = String((p as any)?.preset_id || (p as any)?.presetId || "").trim();
      const tier = (String((p as any)?.tier || "flavor") as any) as "song" | "flavor" | "utility";
      return { id, tier };
    })
    .filter((p) => !!p.id);

  const byTier: Record<string, string[]> = { utility: [], flavor: [], song: [] };
  for (const p of usable) {
    if (!byTier[p.tier]) byTier[p.tier] = [];
    byTier[p.tier].push(p.id);
  }

  const pick1 = (tier: "song" | "flavor" | "utility") => (byTier[tier] && byTier[tier].length ? byTier[tier][0] : null);

  const stack: Array<{ presetId: string; tier: "song" | "flavor" | "utility"; intensity: number }> = [];
  const util = pick1("utility");
  const flavor = pick1("flavor");
  const song = pick1("song");

  if (util) stack.push({ presetId: util, tier: "utility", intensity: 70 });
  if (flavor) stack.push({ presetId: flavor, tier: "flavor", intensity: 70 });
  if (song) stack.push({ presetId: song, tier: "song", intensity: 70 });

  // Fallback: if tiers missing, take first 2 presets as flavor.
  if (!stack.length && usable.length) {
    stack.push({ presetId: usable[0].id, tier: "flavor", intensity: 70 });
    if (usable[1]) stack.push({ presetId: usable[1].id, tier: "flavor", intensity: 70 });
  }

  return stack;
}

export function V3DrummerPickerModal() {
  const open = useV3Store((s) => !!s.ui.drummerPickerOpen);
  const target = useV3Store((s) => s.ui.drummerPickerTarget);
  const setOpen = useV3Store((s) => s.setDrummerPickerOpen);
  const setTarget = useV3Store((s) => s.setDrummerPickerTarget);

  const globalDefaults = useV3Store((s) => s.globalDefaults);
  const setGlobalDefaults = useV3Store((s) => s.setGlobalDefaults);
  const setGlobalPresetStack = useV3Store((s) => s.setGlobalPresetStack);
  const upsertGlobalPreset = useV3Store((s) => s.upsertGlobalPreset);
  const setSectionOverrides = useV3Store((s) => s.setSectionOverrides);
  const upsertSectionPreset = useV3Store((s) => s.upsertSectionPreset);
  const bumpAutoGenerateNonce = useV3Store((s) => s.bumpAutoGenerateNonce);

  const [drummers, setDrummers] = useState<DrummerCard[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [presetsByProfile, setPresetsByProfile] = useState<Record<string, PresetItem[]>>({});
  const [presetLoadingByProfile, setPresetLoadingByProfile] = useState<Record<string, boolean>>({});
  const [presetErrorByProfile, setPresetErrorByProfile] = useState<Record<string, string>>({});

  const [pickedPresetByDrummerId, setPickedPresetByDrummerId] = useState<
    Record<string, { presetId: string; tier: "song" | "flavor" | "utility" }>
  >({});

  const fetchedProfilesRef = useRef<Set<string>>(new Set());
  const inflightProfilesRef = useRef<Set<string>>(new Set());

  const selectedDrummerId = String(globalDefaults.publicDrummerId || globalDefaults.drummer || "");

  const selectedDrummer = useMemo(() => {
    return drummers.find((d) => String(d.id) === selectedDrummerId) || null;
  }, [drummers, selectedDrummerId]);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    (async () => {
      try {
        setLoading(true);
        setError(null);
        const apiBase = resolveApiBaseNormalized();
        const url = apiBase ? `${apiBase}/api/drummers` : `/api/drummers`;
        const res = await fetch(url);
        if (!res.ok) throw new Error(`Failed to fetch drummers (${res.status})`);
        const data = await res.json();
        const list = Array.isArray(data?.drummers) ? data.drummers : [];
        if (!cancelled) setDrummers(list);
      } catch (e: any) {
        if (!cancelled) setError(e?.message || String(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    (async () => {
      const styles = Array.from(
        new Set(
          (drummers || [])
            .map((d) => normalizeProfileType(d))
            .map((s) => String(s || '').trim().toLowerCase())
            .filter((s) => !!s)
        )
      );

      for (const profileType of styles) {
        if (!profileType) continue;
        if (fetchedProfilesRef.current.has(profileType)) continue;
        if (inflightProfilesRef.current.has(profileType)) continue;
        inflightProfilesRef.current.add(profileType);

        try {
          setPresetLoadingByProfile((m) => ({ ...m, [profileType]: true }));
          setPresetErrorByProfile((m) => {
            const next = { ...m };
            delete next[profileType];
            return next;
          });
          const apiBase = resolveApiBaseNormalized();
          const url = apiBase
            ? `${apiBase}/api/drummer-presets?profileType=${encodeURIComponent(profileType)}`
            : `/api/drummer-presets?profileType=${encodeURIComponent(profileType)}`;
          console.debug("[V3DrummerPickerModal] fetch presets", { profileType, url });

          const controller = new AbortController();
          const timeoutId = window.setTimeout(() => controller.abort(), 5000);
          const res = await fetch(url, { signal: controller.signal });
          window.clearTimeout(timeoutId);
          if (!res.ok) throw new Error(`Failed to fetch presets (${res.status})`);
          const data = await res.json();
          const items = Array.isArray(data?.items) ? (data.items as PresetItem[]) : [];
          if (!cancelled) {
            setPresetsByProfile((m) => ({ ...m, [profileType]: items }));
          }
          fetchedProfilesRef.current.add(profileType);
        } catch (e: any) {
          if (!cancelled) {
            setPresetsByProfile((m) => ({ ...m, [profileType]: [] }));
            setPresetErrorByProfile((m) => ({ ...m, [profileType]: e?.message || String(e) }));
          }
        } finally {
          if (!cancelled) {
            setPresetLoadingByProfile((m) => ({ ...m, [profileType]: false }));
          }
          inflightProfilesRef.current.delete(profileType);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [drummers, open]);

  if (!open) return null;

  const close = () => {
    setOpen(false);
  };

  const applyDrummerOnly = (d: DrummerCard) => {
    const drummerId = String(d.id);
    const profileType = normalizeProfileType(d);
    if (target?.scope === "section") {
      setSectionOverrides(target.sectionId, { publicDrummerId: drummerId, drummer: drummerId });
    } else {
      setGlobalDefaults({ publicDrummerId: drummerId, drummer: drummerId, style: profileType || globalDefaults.style });
    }
  };

  const onSelectDrummer = async (d: DrummerCard) => {
    const drummerId = String(d.id);
    const profileType = normalizeProfileType(d);

    const pickedPreset = pickedPresetByDrummerId[drummerId] || null;
    const pickedPresetId = String(pickedPreset?.presetId || "").trim();
    const pickedPresetTier = (pickedPreset?.tier || "flavor") as "song" | "flavor" | "utility";

    if (target?.scope === "section") {
      setSectionOverrides(target.sectionId, { publicDrummerId: drummerId, drummer: drummerId });

      if (pickedPresetId) {
        upsertSectionPreset(target.sectionId, { presetId: pickedPresetId, tier: pickedPresetTier, intensity: 70 });
      }
    } else {
      setGlobalDefaults({ publicDrummerId: drummerId, drummer: drummerId, style: profileType || globalDefaults.style });

      // Best-effort: fetch presets for this drummer style and auto-apply a default stack.
      if (profileType && !pickedPresetId) {
        try {
          const apiBase = resolveApiBaseNormalized();
          const url = apiBase
            ? `${apiBase}/api/drummer-presets?profileType=${encodeURIComponent(profileType)}`
            : `/api/drummer-presets?profileType=${encodeURIComponent(profileType)}`;
          const res = await fetch(url);
          if (res.ok) {
            const data = await res.json();
            const items = Array.isArray(data?.items) ? (data.items as PresetItem[]) : [];
            const stack = pickDefaultPresetStack(items);
            setGlobalPresetStack(stack);
          }
        } catch {
          // ignore
        }
      }

      if (pickedPresetId) {
        upsertGlobalPreset({ presetId: pickedPresetId, tier: pickedPresetTier, intensity: 70 });
      }
    }

    // Close + trigger auto-generation.
    bumpAutoGenerateNonce();
    setOpen(false);
  };

  return (
    <div data-testid="v3.drummerPicker" className="fixed inset-0 z-[10000] flex items-center justify-center bg-black/70 p-4">
      <div className="w-full max-w-5xl max-h-[88vh] overflow-hidden rounded-xl border border-slate-700 bg-slate-950 shadow-2xl">
        <div className="flex items-start justify-between gap-4 border-b border-slate-800 p-4">
          <div>
            <div className="text-xl font-extrabold tracking-tight text-slate-100">Choose Your Drummer</div>
            <div className="mt-1 text-[11px] text-slate-400">Selecting a drummer sets the profile and applies a default preset stack.</div>
          </div>
          <button
            type="button"
            className="text-slate-400 hover:text-slate-100"
            onClick={() => {
              close();
              setTarget({ scope: "global" });
            }}
          >
            ✕
          </button>
        </div>

        <div className="p-4 overflow-y-auto max-h-[calc(88vh-120px)]">
          {loading && (
            <div className="text-[11px] text-slate-400">Loading…</div>
          )}
          {error && <div className="text-[11px] text-rose-300">{error}</div>}

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mt-2">
            {drummers.map((d) => {
              const selected = selectedDrummerId && String(d.id) === selectedDrummerId;
              const border = String((d as any)?.color || "rgba(148,163,184,0.35)");
              const profileType = normalizeProfileType(d);
              const presetItems = profileType ? presetsByProfile[profileType] || [] : [];
              const presetLoading = profileType ? !!presetLoadingByProfile[profileType] : false;
              const presetError = profileType ? String(presetErrorByProfile[profileType] || "") : "";
              const presetOptions = (presetItems || [])
                .map((p) => {
                  const id = String((p as any)?.preset_id || (p as any)?.presetId || '').trim();
                  const label = String((p as any)?.display_name || (p as any)?.name || id || '').trim();
                  const tier = String((p as any)?.tier || 'flavor') as any;
                  return { id, label: label || id, tier };
                })
                .filter((x) => !!x.id);

              const onPickPreset = (presetId: string) => {
                if (!presetId || presetId === "__none__") return;
                const found = presetOptions.find((x) => x.id === presetId);
                const item = {
                  presetId,
                  tier: ((found?.tier || 'flavor') as any) as 'song' | 'flavor' | 'utility',
                  intensity: 70,
                };
                if (target?.scope === 'section') {
                  upsertSectionPreset(target.sectionId, item);
                } else {
                  upsertGlobalPreset(item);
                }
              };

              return (
                <div
                  key={d.id}
                  className={
                    "text-left rounded-lg border bg-slate-900/40 hover:bg-slate-900/60 transition p-3 " +
                    (selected ? "border-cyan-400/60" : "border-slate-800")
                  }
                  style={{ borderLeftWidth: 4, borderLeftColor: border }}
                >
                  <div className="flex items-start gap-3">
                    <div className="text-2xl leading-none">{(d as any)?.icon || "🥁"}</div>
                    <div className="min-w-0">
                      <div className="text-sm font-semibold text-slate-100 truncate">{d.display_name || d.id}</div>
                      <div className="text-[11px] text-slate-400 mt-0.5 line-clamp-2">{String((d as any)?.tagline || "")}</div>
                    </div>
                  </div>

                  <div className="mt-2 flex flex-wrap gap-1">
                    {(Array.isArray((d as any)?.genre_tags) ? (d as any).genre_tags : []).slice(0, 4).map((t: string) => (
                      <span key={t} className="text-[10px] px-2 py-0.5 rounded-full border border-slate-700 bg-slate-950 text-slate-300">
                        {t}
                      </span>
                    ))}
                    {String((d as any)?.difficulty || "") ? (
                      <span className="text-[10px] px-2 py-0.5 rounded-full border border-slate-700 bg-slate-950 text-slate-300">
                        {String((d as any).difficulty)}
                      </span>
                    ) : null}
                  </div>

                  <div className="mt-2 text-[11px] text-slate-400">
                    {presetLoading ? "Loading presets…" : `Presets: ${presetOptions.length || 0}`}
                    {presetError ? <span className="text-rose-300"> • {presetError}</span> : null}
                  </div>

                  <div className="mt-3 flex items-center justify-between gap-2">
                    <button
                      type="button"
                      className="px-2.5 py-1 rounded bg-slate-800 border border-slate-700 text-[11px] text-slate-100 hover:bg-slate-700"
                      data-testid={`v3.drummerPicker.select.${String(d.id)}`}
                      onClick={() => void onSelectDrummer(d)}
                    >
                      Select
                    </button>

                    <select
                      className="min-w-[180px] bg-slate-950 border border-slate-700 rounded px-2 py-1 text-[11px] text-slate-100"
                      value={pickedPresetByDrummerId[String(d.id)]?.presetId || ""}
                      onClick={(e) => e.stopPropagation()}
                      onChange={(e) => {
                        e.stopPropagation();
                        const presetId = e.target.value;
                        const found = presetOptions.find((x) => x.id === presetId);
                        const tier = ((found?.tier || "flavor") as any) as "song" | "flavor" | "utility";
                        setPickedPresetByDrummerId((m) => ({ ...m, [String(d.id)]: { presetId, tier } }));
                      }}
                    >
                      <option value="">Add preset…</option>
                      {presetLoading ? <option value="__loading__">Loading…</option> : null}
                      {!presetLoading && !presetOptions.length ? <option value="__none__">No presets available</option> : null}
                      {presetOptions.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="flex items-center justify-between gap-2 border-t border-slate-800 p-4">
          <div className="text-[11px] text-slate-400">
            Target: {target?.scope === "section" ? `Section (${target.sectionId})` : "Global"}
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="px-3 py-1.5 rounded bg-slate-900 border border-slate-700 text-sm text-slate-200 hover:bg-slate-800"
              onClick={close}
            >
              Cancel
            </button>
            <button
              type="button"
              className="px-3 py-1.5 rounded bg-cyan-700/70 border border-cyan-600 text-sm text-slate-100 hover:bg-cyan-700"
              onClick={close}
            >
              Done
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
