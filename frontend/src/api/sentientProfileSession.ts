import type { DrumGenerationConfig } from "../types/drumTrack";
import {
  attachSentientProfile,
  fetchSentientProfile,
  getSelectedPublicDrummerId,
} from "./sentientProfiles";

// Inline status type unions at usage sites to avoid standalone aliases that CI lints misinterpret

export type SentientProfileEntry = {
  drummerId: string;
  status: "idle" | "loading" | "ready" | "missing" | "error";
  profile: { [key: string]: any } | null;
  loadedAt?: number;
  error?: string;
};

const sessionCache = new Map<string, SentientProfileEntry>();
const inflight = new Map<string, Promise<SentientProfileEntry>>();

type SessionListener = (entry: SentientProfileEntry) => void;
const listeners = new Set<SessionListener>();

function notify(entry: SentientProfileEntry): void {
  listeners.forEach((listener) => {
    try {
      listener(entry);
    } catch {
      // ignore listener errors
    }
  });
}

function setEntry(entry: SentientProfileEntry): SentientProfileEntry {
  sessionCache.set(entry.drummerId, entry);
  notify(entry);
  return entry;
}

export function subscribeSentientProfileSession(listener: SessionListener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getSentientProfileSessionState(drummerId: string): SentientProfileEntry {
  const id = String(drummerId || "").trim();
  if (!id) return { drummerId: "", status: "idle", profile: null };
  return sessionCache.get(id) || { drummerId: id, status: "idle", profile: null };
}

export async function preloadSentientProfile(drummerId: string): Promise<SentientProfileEntry> {
  const id = String(drummerId || "").trim();
  if (!id) return { drummerId: "", status: "idle", profile: null };

  const existing = sessionCache.get(id);
  if (existing && (existing.status === "ready" || existing.status === "missing")) {
    return existing;
  }
  if (inflight.has(id)) return inflight.get(id)!;

  setEntry({ drummerId: id, status: "loading", profile: existing?.profile || null });

  const job = (async (): Promise<SentientProfileEntry> => {
    try {
      const profile = await fetchSentientProfile(id);
      const entry = setEntry({
        drummerId: id,
        status: profile ? "ready" : "missing",
        profile,
        loadedAt: Date.now(),
      });
      return entry;
    } catch (err: any) {
      const entry = setEntry({
        drummerId: id,
        status: "error",
        profile: null,
        loadedAt: Date.now(),
        error: err?.message || "sentient profile preload failed",
      });
      return entry;
    } finally {
      inflight.delete(id);
    }
  })();

  inflight.set(id, job);
  return job;
}

export async function preloadSentientProfiles(
  ids: Array<string | null | undefined>
): Promise<SentientProfileEntry[]> {
  const unique = Array.from(
    new Set(ids.map((v) => String(v || "").trim()).filter(Boolean))
  );
  return Promise.all(unique.map((id) => preloadSentientProfile(id)));
}

function clone<T>(value: T): T {
  return value == null ? value : JSON.parse(JSON.stringify(value));
}

function resolveSectionDrummerId(section: any, fallback: string): string {
  return String(
    section?.publicDrummerId ||
      section?.drummerId ||
      section?.drummer ||
      section?.personaId ||
      fallback ||
      ""
  ).trim();
}

export async function attachSentientProfilesWithOverrides(
  config: DrumGenerationConfig & Record<string, any>
): Promise<DrumGenerationConfig> {
  const enriched = await attachSentientProfile(config as DrumGenerationConfig);
  const baseDrummerId = getSelectedPublicDrummerId(enriched as any);

  const sections = Array.isArray((enriched as any).sections)
    ? clone((enriched as any).sections)
    : Array.isArray((enriched as any).songSections)
      ? clone((enriched as any).songSections)
      : null;

  if (!sections?.length) return enriched as DrumGenerationConfig;

  const sectionIds: string[] = Array.from(
    new Set(
      sections
        .map((section: any) => resolveSectionDrummerId(section, baseDrummerId))
        .filter((id: string) => Boolean(id))
    )
  );
  await preloadSentientProfiles(sectionIds);

  let changed = false;
  for (const section of sections) {
    const sectionDrummerId = resolveSectionDrummerId(section, baseDrummerId);
    if (!sectionDrummerId || sectionDrummerId === baseDrummerId) continue;
    const entry = getSentientProfileSessionState(sectionDrummerId);
    if (entry.status !== "ready" || !entry.profile) continue;
    section.sentientProfile = entry.profile;
    section.drummer_profile = entry.profile;
    section.publicDrummerId = sectionDrummerId;
    changed = true;
  }

  if (!changed) return enriched as DrumGenerationConfig;
  return {
    ...(enriched as any),
    sections,
    songSections: Array.isArray((enriched as any).songSections)
      ? sections
      : (enriched as any).songSections,
  } as DrumGenerationConfig;
}
