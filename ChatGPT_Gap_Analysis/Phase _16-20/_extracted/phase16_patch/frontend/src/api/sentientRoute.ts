import type { DrumGenerationConfig, DrumGenerationResponse } from "../types/drumTrack";

function hasSentientProfile(config: DrumGenerationConfig | Record<string, any>): boolean {
  const profile = (config as any)?.drummer_profile ?? (config as any)?.drummerProfile ?? (config as any)?.sentientProfile;
  if (!profile || typeof profile !== 'object') return false;
  return Boolean(
    Array.isArray((profile as any).profiles) ||
    (profile as any).transition_model ||
    (profile as any).timing_profiles ||
    (profile as any).dynamic_profiles ||
    (profile as any).instrument_timing_profiles ||
    (profile as any).instrument_dynamic_profiles
  );
}

export function resolveDrumGenerationEndpoint(config: DrumGenerationConfig | Record<string, any>): string {
  return hasSentientProfile(config) ? '/api/generate-drums' : '/api/generate-drums';
}

// Existing callers already hit /api/generate-drums. This helper documents
// the default sentient route preference introduced in Phase 16 and gives
// a stable place for future client-side routing if multiple endpoints remain.
