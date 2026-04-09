# Phase 18 — Sentient session cache, preload, and section-level overrides

Phase 18 makes sentient profile loading feel native in the app instead of opportunistic.

## What this phase adds

### Frontend
- `frontend/src/api/sentientProfileSession.ts`
- `frontend/src/utils/sentientUi.ts`

## What it does

### 1. Session cache and preload
Adds a persistent in-session cache for sentient drummer profiles so the app can:
- preload a profile when the drummer selection changes
- reuse the same artifact for repeated generation requests
- expose a simple status model: `idle`, `loading`, `ready`, `missing`, `error`

### 2. UI readiness hooks
Adds a lightweight subscription model so UI components can reflect profile readiness without repeatedly refetching.

### 3. Section-level drummer overrides
Adds `attachSentientProfilesWithOverrides(config)` which:
- loads the base drummer profile
- scans `sections` / `songSections`
- resolves per-section drummer overrides
- attaches the correct sentient profile to each overridden section as:
  - `section.sentientProfile`
  - `section.drummer_profile`

This lets later phases support arrangements where different sections intentionally carry different drummer identities.

## Recommended frontend integration

### Preload on drummer change
In the drummer picker effect:

```ts
import { preloadSentientProfile, getSentientProfileSessionState } from "../api/sentientProfileSession";

useEffect(() => {
  const id = selectedDrummer?.id;
  if (!id) return;
  void preloadSentientProfile(id);
}, [selectedDrummer?.id]);
```

### Surface readiness in UI

```ts
import { subscribeSentientProfileSession, getSentientProfileSessionState } from "../api/sentientProfileSession";
import { sentientProfileBadge } from "../utils/sentientUi";

const [sentientState, setSentientState] = useState(() => getSentientProfileSessionState(selectedDrummer?.id ?? ""));

useEffect(() => {
  const id = selectedDrummer?.id ?? "";
  setSentientState(getSentientProfileSessionState(id));
  const unsub = subscribeSentientProfileSession((entry) => {
    if (entry.drummerId === id) setSentientState(entry);
  });
  return unsub;
}, [selectedDrummer?.id]);

const badge = sentientProfileBadge(sentientState);
```

### Use override-aware request enrichment
Replace Phase 17 request enrichment:

```ts
import { attachSentientProfilesWithOverrides } from "./sentientProfileSession";

const enriched = await attachSentientProfilesWithOverrides(config);
```

## Why this matters

Phase 17 made sentient profile loading automatic.

Phase 18 makes it stable and app-friendly:
- less fetch churn
- explicit readiness state
- better UX around missing profiles
- future-safe for section-level drummer identities

## Result

After this phase, the sentient path is no longer just an invisible fetch. It becomes a managed session resource that the UI and generation pipeline can reason about directly.
