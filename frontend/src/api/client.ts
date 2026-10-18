import { extractErrorMessage } from "./envelope";

// A production build is served by the backend itself out of backend/static, so it talks
// to its own origin and `buildUrl` emits relative /api paths. The dev server runs on a
// different port from the API, so it needs the absolute origin. Setting VITE_BACKEND_URL
// overrides either default, for a deployment that splits the two across hosts.
//
// `??` rather than `||`: an explicitly empty VITE_BACKEND_URL has to mean "same origin",
// and `||` would quietly turn it back into localhost.
const defaultBackendUrl = import.meta.env.DEV ? "http://localhost:8000" : "";
const backendUrl = (import.meta.env.VITE_BACKEND_URL ?? defaultBackendUrl)
  .replace(/\/$/, "")
  .replace(/\/api$/, "");
const apiPrefix = "/api";

function buildUrl(input: string | URL | Request): string {
  const rawUrl =
    typeof input === "string"
      ? input
      : input instanceof URL
        ? input.toString()
        : input.url;

  if (/^https?:\/\//.test(rawUrl)) {
    return rawUrl;
  }

  const normalizedPath = rawUrl.startsWith("/") ? rawUrl : `/${rawUrl}`;
  const pathWithApi = normalizedPath.startsWith(apiPrefix)
    ? normalizedPath
    : `${apiPrefix}${normalizedPath}`;

  return backendUrl ? `${backendUrl}${pathWithApi}` : pathWithApi;
}

async function parseError(response: Response): Promise<Error> {
  const contentType = response.headers.get("content-type") || "";
  const message = contentType.includes("application/json")
    ? extractErrorMessage(await response.json(), response.statusText)
    : await response.text();

  return new Error(message || response.statusText || "Request failed");
}

export async function apiFetch(
  input: string | URL | Request,
  init: RequestInit = {},
): Promise<Response> {
  const headers = new Headers(init.headers);

  headers.set("Accept", "application/json");

  if (
    init.body &&
    !headers.has("Content-Type") &&
    !(init.body instanceof FormData)
  ) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(buildUrl(input), {
    ...init,
    headers,
    credentials: init.credentials ?? "include",
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return response;
}

export function buildApiUrl(pathname: string): string {
  return buildUrl(pathname);
}
