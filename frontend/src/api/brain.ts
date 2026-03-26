import { BrainElementDefinition, DrumBrainConfig, FALLBACK_BRAIN_ELEMENTS } from "../types/brain";
import { getApiBases } from "./api";

export type BrainConfigPatch = Partial<DrumBrainConfig>;

async function fetchWithBases(path: string, init?: RequestInit): Promise<Response> {
  const bases = getApiBases();
  let lastError: Error | null = null;
  for (const base of bases) {
    try {
      const response = await fetch(`${base}${path}`, init);
      if (response.ok) {
        return response;
      }
      lastError = new Error(`${response.status} ${response.statusText}`);
    } catch (error) {
      lastError = error as Error;
    }
  }
  throw lastError ?? new Error("Request failed");
}

export async function fetchBrainElements(style?: string): Promise<BrainElementDefinition[]> {
  try {
    const searchParams = new URLSearchParams();
    if (style) {
      searchParams.set("style", style);
    }
    const suffix = searchParams.toString() ? `?${searchParams.toString()}` : "";
    const response = await fetchWithBases(`/dcsm/brain-elements${suffix}`);
    return (await response.json()) as BrainElementDefinition[];
  } catch (error) {
    console.warn("Falling back to static brain element definitions", error);
    return FALLBACK_BRAIN_ELEMENTS;
  }
}

export async function fetchBrainConfig(sectionId: string): Promise<DrumBrainConfig> {
  const response = await fetchWithBases(`/dcsm/brain-config/${encodeURIComponent(sectionId)}`);
  return (await response.json()) as DrumBrainConfig;
}

export async function patchBrainConfig(
  sectionId: string,
  patch: BrainConfigPatch,
): Promise<DrumBrainConfig> {
  const response = await fetchWithBases(`/dcsm/brain-config/${encodeURIComponent(sectionId)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
  return (await response.json()) as DrumBrainConfig;
}
