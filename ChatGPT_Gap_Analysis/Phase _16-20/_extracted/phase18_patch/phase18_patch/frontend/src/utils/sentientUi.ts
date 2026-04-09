import type { SentientProfileEntry } from "../api/sentientProfileSession";

export function sentientProfileBadge(entry: SentientProfileEntry | null | undefined): { label: string; tone: "neutral" | "good" | "warn" | "bad" } {
  switch (entry?.status) {
    case "loading":
      return { label: "Loading sentient profile…", tone: "neutral" };
    case "ready":
      return { label: "Sentient profile ready", tone: "good" };
    case "missing":
      return { label: "No sentient profile found", tone: "warn" };
    case "error":
      return { label: "Sentient profile failed to load", tone: "bad" };
    default:
      return { label: "Sentient profile idle", tone: "neutral" };
  }
}
