import { apiFetch, buildApiUrl } from "./client";
import { unwrapApiData } from "./envelope";
import type { CurrentUser } from "@/types/documents";

export async function signIn(
  username: string,
  password: string,
): Promise<CurrentUser> {
  const response = await apiFetch("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });

  return unwrapApiData<CurrentUser>(await response.json());
}

export async function signOut(): Promise<void> {
  await apiFetch("/auth/logout", { method: "POST" });
}

export async function fetchCurrentUser(): Promise<CurrentUser | null> {
  const response = await fetch(buildApiUrl("/auth/me"), {
    headers: { Accept: "application/json" },
    credentials: "include",
  });

  if (response.status === 401 || response.status === 403) {
    return null;
  }

  if (!response.ok) {
    throw new Error("Unable to load current user");
  }

  return unwrapApiData<CurrentUser>(await response.json());
}
