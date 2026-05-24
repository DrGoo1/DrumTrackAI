const LOCAL_API_PORT = "8000";
const CALIBRATION_API_BASE = "https://drumtrackai-calibration-api.onrender.com";

const normalizeApiBase = (value?: string | null): string => String(value || "").trim().replace(/\/+$/, "");

const isProductionFrontendHost = (hostname: string): boolean => {
  const hostLower = String(hostname || "").toLowerCase();
  return /(^|\.)netlify\.app$/.test(hostLower) || /(^|\.)drumtrackai\.net$/.test(hostLower);
};

/** Resolve the backend base URL, preferring explicit overrides and falling back to sensible defaults. */
export function resolveApiBase(): string {
  const explicitBase = normalizeApiBase(process.env.REACT_APP_API_BASE);

  if (typeof window !== "undefined") {
    const win = window as any;
    const hostLower = String(win?.location?.hostname || "localhost").toLowerCase();

    const runtimeBase = normalizeApiBase(win.__API_BASE__);
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
    const desiredPort = win.__API_PORT__ || process.env.REACT_APP_API_PORT || LOCAL_API_PORT;

    if (/^(localhost|127\.0\.0\.1)$/i.test(hostname)) {
      return `http://${hostname}:${desiredPort}`;
    }

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
