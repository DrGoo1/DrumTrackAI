# Phase 17 — Frontend sentient profile loading

Phase 17 wires the **frontend payload builder** so drummer/persona selection loads and sends the exported sentient profile artifact automatically.

## What this phase adds

### Backend
- `backend/backend/drummerbrain/sentient_profile_registry.py`
- `GET /api/sentient-profiles/{publicDrummerId}` helper integration point
- focused registry tests

### Frontend
- `frontend/src/api/sentientProfiles.ts`
- `attachSentientProfile(config)` helper

## Why this phase matters

Phase 16 made the backend default route smart enough to use the sentient path **if** a rich sentient drummer profile is present.

Phase 17 solves the missing upstream step:

1. user picks a drummer/persona
2. frontend resolves the exported sentient profile artifact for that drummer
3. frontend attaches the artifact to the generation request
4. existing `/api/generate-drums` now automatically routes through the sentient path

## Expected request flow

```text
frontend drummer selection
  -> publicDrummerId
  -> GET /api/sentient-profiles/{id}
  -> attach profile to request as drummer_profile / sentientProfile
  -> POST /api/generate-drums
  -> Phase 16 detection routes to /v1/render_sentient_take
```

## Minimal frontend integration

### In `src/api/api.ts`

Before POSTing `/api/generate-drums`, enrich the config:

```ts
import { attachSentientProfile } from "./sentientProfiles";

export async function generateDrums(config: DrumGenerationConfig): Promise<DrumGenerationResponse> {
  const enriched = await attachSentientProfile(config);
  const res = await fetchWithBases(`/api/generate-drums`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(enriched),
  });
  if (!res.ok) throw new Error("Drum generation failed");
  return res.json();
}
```

### In `WebDAWApp.tsx`

Because that component currently performs a direct `fetch`, apply the same enrichment there:

```ts
import { attachSentientProfile } from "../api/sentientProfiles";

let payload: DrumGenerationConfig = {
  ...config,
  publicDrummerId: selectedDrummer?.id ?? config.publicDrummerId ?? config.drummer,
  drummerPersona: selectedDrummer ?? config.drummerPersona,
};

payload = await attachSentientProfile(payload);
```

## Minimal backend route integration

Add this to the FastAPI app that serves generation requests:

```py
from backend.backend.drummerbrain.sentient_profile_registry import build_sentient_profile_response

@app.get("/api/sentient-profiles/{drummer_id}")
def api_get_sentient_profile(drummer_id: str):
    return build_sentient_profile_response(drummer_id)
```

## Result

After this phase, the user only needs to pick the drummer. The app now has a clean path to send the correct sentient artifact automatically.
