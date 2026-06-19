const LOCAL_API_PORT = "8000";

export const CANONICAL_CALIBRATION_API_BASE = "https://drumtrackai-calibration-api.onrender.com";

const CALIBRATION_API_BASE = process.env.NODE_ENV === "development"
  ? `http://127.0.0.1:${LOCAL_API_PORT}`
  : CANONICAL_CALIBRATION_API_BASE;

const normalizeApiBase = (value?: string | null): string => String(value || "").trim().replace(/\/+$/, "");
const rewriteDeprecatedApiBase = (value?: string | null): string => {
  const normalized = normalizeApiBase(value);
  if (!normalized) {
    return "";
  }
  return normalized.replace(
    /^https?:\/\/drumtrackai-calibration-api2\.onrender\.com(?=\/|$)/i,
    CANONICAL_CALIBRATION_API_BASE,
  );
};

const isProductionFrontendHost = (hostname: string): boolean => {
  const hostLower = String(hostname || "").toLowerCase();
  return (
    /(^|\.)netlify\.app$/.test(hostLower)
    || /(^|\.)drumtrackai\.net$/.test(hostLower)
    || /(^|\.)drumtrackai\.com$/.test(hostLower)
  );
};

/** Resolve the backend base URL, preferring explicit overrides and falling back to sensible defaults. */
export function resolveApiBase(): string {
  const explicitBase = rewriteDeprecatedApiBase(process.env.REACT_APP_API_BASE);

  if (process.env.NODE_ENV === "development") {
    const envPort = process.env.REACT_APP_API_PORT || LOCAL_API_PORT;
    return `http://127.0.0.1:${envPort}`;
  }

  if (typeof window !== "undefined") {
    const win = window as any;
    const hostLower = String(win?.location?.hostname || "localhost").toLowerCase();
    const desiredPort = win.__API_PORT__ || process.env.REACT_APP_API_PORT || LOCAL_API_PORT;

    // In local development, always pin to local backend unless user is not on localhost.
    // This avoids accidentally calling stale remote APIs via injected runtime bases.
    if (/^(localhost|127\.0\.0\.1)$/i.test(hostLower)) {
      return `http://${hostLower}:${desiredPort}`;
    }

    const runtimeBase = rewriteDeprecatedApiBase(win.__API_BASE__);
    if (runtimeBase) {
      return runtimeBase;
    }

    if (explicitBase) {
      return explicitBase;
    }

    if (
      isProductionFrontendHost(hostLower)
    ) {
      return CALIBRATION_API_BASE;
    }

    const protocol = win.location?.protocol || "http:";
    const hostname = win.location?.hostname || "localhost";

    const portSegment = win.location?.port ? `:${win.location.port}` : "";
    return `${protocol}//${hostname}${portSegment}`;
  }

  if (explicitBase) {
    return explicitBase;
  }

  const envPort = process.env.REACT_APP_API_PORT || LOCAL_API_PORT;
  return `http://localhost:${envPort}`;
}

export const resolveApiBaseNormalized = () => normalizeApiBase(resolveApiBase());
