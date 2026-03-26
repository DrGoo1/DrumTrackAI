const LOCAL_API_PORT = "8000";

/** Resolve the backend base URL, preferring explicit overrides and falling back to sensible defaults. */
export function resolveApiBase(): string {
  if (typeof window !== "undefined") {
    const win = window as any;
    if (win.__API_BASE__) {
      return String(win.__API_BASE__);
    }
    const explicitBase = process.env.REACT_APP_API_BASE;
    if (explicitBase) {
      return explicitBase;
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
    return envBase;
  }
  const envPort = process.env.REACT_APP_API_PORT || LOCAL_API_PORT;
  return `http://localhost:${envPort}`;
}

export const resolveApiBaseNormalized = () => resolveApiBase().replace(/\/$/, "");
