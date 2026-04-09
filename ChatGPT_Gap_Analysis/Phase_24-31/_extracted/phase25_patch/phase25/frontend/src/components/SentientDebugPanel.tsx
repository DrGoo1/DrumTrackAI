import React from "react";

export default function SentientDebugPanel({ profile, selection }: any) {
  if (!profile) return null;

  return (
    <div style={{padding:12, border:"1px solid #333"}}>
      <h3>Sentient Debug</h3>
      <div>Drummer: {profile.drummer_id || "unknown"}</div>
      <div>Preferred Families: {(profile.preferredGrooveFamilies||[]).join(", ")}</div>
      <div>Selected Family: {selection?.family}</div>
    </div>
  );
}
