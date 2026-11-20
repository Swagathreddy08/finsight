export type AuthTokens = {
  access_token: string;
};

export const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

let accessToken: string | null = null;
let refreshInFlight: Promise<boolean> | null = null;

export function getAccessToken(): string | null {
  return accessToken;
}

export function storeAuthTokens(tokens: AuthTokens): void {
  accessToken = tokens.access_token;
}

export function clearAuthTokens(): void {
  accessToken = null;
}

function unauthorizedResponse(): Response {
  return new Response(JSON.stringify({ detail: "Not signed in" }), {
    status: 401,
    headers: { "Content-Type": "application/json" },
  });
}

export async function ensureAccessToken(): Promise<boolean> {
  if (accessToken) return true;
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      const response = await fetch(`${apiBaseUrl}/api/v1/auth/refresh`, {
        method: "POST",
        credentials: "include",
      });
      if (!response.ok) {
        clearAuthTokens();
        return false;
      }
      storeAuthTokens(await response.json() as AuthTokens);
      return true;
    })().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

export async function authenticatedFetch(
  input: RequestInfo | URL,
  init: RequestInit = {},
): Promise<Response> {
  if (!(await ensureAccessToken())) {
    return unauthorizedResponse();
  }

  const token = accessToken;
  if (!token) return unauthorizedResponse();
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(input, { ...init, headers });
  if (response.status !== 401) return response;
  clearAuthTokens();
  if (!(await ensureAccessToken())) return response;

  const refreshedToken = accessToken;
  if (!refreshedToken) return response;
  headers.set("Authorization", `Bearer ${refreshedToken}`);
  const retriedResponse = await fetch(input, { ...init, headers });
  if (retriedResponse.status === 401) clearAuthTokens();
  return retriedResponse;
}

export async function revokeSession(): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/api/v1/auth/logout`, {
    method: "POST",
    credentials: "include",
  });
  if (!response.ok) throw new Error("Could not revoke the current session.");
  clearAuthTokens();
}
