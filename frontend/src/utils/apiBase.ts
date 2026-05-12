const LOCAL_API_PORT = "8000";

/** Resolve the backend base URL, preferring explicit overrides and falling back to sensible defaults. */
export function resolveApiBase(): string {
  if (typeof window !== "undefined") {
    const win = window as any;
    const hostLower = String(win?.location?.hostname || "localhost").toLowerCase();
    if (hostLower.endsWith("netlify.app") || hostLower === "drumtrackai.netlify.app") {
      return "https://drumtrackai-calibration-api2.onrender.com";
    }
    // Prefer explicit environment variable configured at build-time (e.g., Netlify UI)
    const explicitBase = process.env.REACT_APP_API_BASE;
    if (explicitBase) {
      return explicitBase;
    }
    // Then allow a runtime override via window.__API_BASE__ if provided
    if (win.__API_BASE__) {
      return String(win.__API_BASE__);
    }
    const protocol = win.location?.protocol || "http:";
    const hostname = win.location?.hostname || "localhost";
    const desiredPort = win.__API_PORT__ || process.env.REACT_APP_API_PORT || LOCAL_API_PORT;

    if (/^(localhost|127\.0\.0\.1)$/i.test(hostname)) {
      void protocol;
      void desiredPort;
      return "";
    }
    const portSegment = win.location?.port ? `:${win.location.port}` : "";
    return `${protocol}//${hostname}${portSegment}`;
  }
  const envBase = process.env.REACT_APP_API_BASE;
  if (envBase) {
    const lower = envBase.toLowerCase();
    if (lower.includes('netlify.app')) {
      return 'https://drumtrackai-calibration-api2.onrender.com';
    }
    return envBase;
  }
  const envPort = process.env.REACT_APP_API_PORT || LOCAL_API_PORT;
  return `http://localhost:${envPort}`;
}

export const resolveApiBaseNormalized = () => resolveApiBase().replace(/\/$/, "");
