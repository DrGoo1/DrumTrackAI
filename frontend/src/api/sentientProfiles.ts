import type { DrumGenerationConfig } from "../types/drumTrack";

const profileCache = new Map<string, Promise<Record<string, any> | null>>();

function resolveApiBases(): string[] {
  const envBase = (import.meta as any).env?.VITE_API_BASE as string | undefined;
  if (envBase) return [envBase];
  return [""];
}

async function fetchWithBases(path: string, init?: RequestInit): Promise<Response> {
  const bases = resolveApiBases();
  let lastErr: any = null;
  for (const base of bases) {
    try {
      const res = await fetch(`${base}${path}`, init);
      if (res.ok) return res;
      lastErr = new Error(`${res.status} ${res.statusText}`);
    } catch (err) {
      lastErr = err;
    }
  }
  throw lastErr || new Error("request failed");
}

export function getSelectedPublicDrummerId(config: DrumGenerationConfig | Record<string, any>): string {
  return String(
    (config as any)?.publicDrummerId || (config as any)?.drummer || (config as any)?.drummerId || ""
  ).trim();
}

export async function fetchSentientProfile(publicDrummerId: string): Promise<Record<string, any> | null> {
  const id = String(publicDrummerId || "").trim();
  if (!id) return null;
  if (!profileCache.has(id)) {
    profileCache.set(
      id,
      (async () => {
        try {
          const res = await fetchWithBases(`/api/sentient-profiles/${encodeURIComponent(id)}`);
          const data = await res.json();
          return data?.profile && typeof data.profile === "object" ? data.profile : null;
        } catch {
          return null;
        }
      })()
    );
  }
  return profileCache.get(id)!;
}

function hasRichSentientProfile(profile: any): boolean {
  return Boolean(
    profile &&
      typeof profile === "object" &&
      (Array.isArray(profile.profiles) ||
        profile.timing_profiles ||
        profile.dynamic_profiles ||
        profile.transition_model ||
        profile.instrument_timing_profiles ||
        profile.instrument_dynamic_profiles ||
        profile.phrase_library ||
        profile.phrase_memory)
  );
}

export async function attachSentientProfile(config: DrumGenerationConfig): Promise<DrumGenerationConfig> {
  const already = (config as any).drummer_profile || (config as any).sentientProfile;
  if (hasRichSentientProfile(already)) return config;

  const publicDrummerId = getSelectedPublicDrummerId(config);
  if (!publicDrummerId) return config;

  const fetched = await fetchSentientProfile(publicDrummerId);
  if (!hasRichSentientProfile(fetched)) return config;

  return {
    ...config,
    drummer_profile: fetched,
    sentientProfile: fetched,
  } as DrumGenerationConfig;
}
