export function buildSentientDebugState(profile: any, selection: any) {
  return {
    drummer: profile?.drummer_id,
    families: profile?.preferredGrooveFamilies,
    selected: selection?.family,
  };
}
