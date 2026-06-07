import { storage } from "@/src/utils/storage";

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

let cachedToken: string | null = null;

export async function getToken(): Promise<string | null> {
  if (cachedToken) return cachedToken;
  const t = await storage.secureGet<string>("auth_token", "");
  cachedToken = t && typeof t === "string" && t.length > 0 ? t : null;
  return cachedToken;
}

export async function setToken(token: string | null) {
  cachedToken = token;
  if (token) {
    await storage.secureSet("auth_token", token);
  } else {
    await storage.secureRemove("auth_token");
  }
}

async function request(path: string, opts: RequestInit = {}) {
  const token = await getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(opts.headers as Record<string, string> | undefined),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API}${path}`, { ...opts, headers });
  const isJSON = res.headers.get("content-type")?.includes("application/json");
  const body = isJSON ? await res.json() : await res.text();
  if (!res.ok) {
    const detail = typeof body === "object" && body?.detail ? body.detail : `Request failed (${res.status})`;
    throw new Error(detail);
  }
  return body;
}

export const api = {
  signup: (data: any) => request("/auth/signup", { method: "POST", body: JSON.stringify(data) }),
  login: (data: any) => request("/auth/login", { method: "POST", body: JSON.stringify(data) }),
  me: () => request("/auth/me"),
  updateProfile: (data: any) => request("/profile/me", { method: "PUT", body: JSON.stringify(data) }),
  swipeFeed: () => request("/swipe/feed"),
  swipe: (target_user_id: string, action: "like" | "pass" | "superlike") =>
    request("/swipe", { method: "POST", body: JSON.stringify({ target_user_id, action }) }),
  standout: () => request("/standout"),
  matches: () => request("/matches"),
  getMessages: (matchId: string) => request(`/messages/${matchId}`),
  sendMessage: (matchId: string, text: string) =>
    request(`/messages/${matchId}`, { method: "POST", body: JSON.stringify({ text }) }),
};
