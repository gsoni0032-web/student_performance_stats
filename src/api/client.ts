import { tokens } from "@/api/tokens";
import type { TokenPair } from "@/api/types";

const BASE = (import.meta.env.VITE_API_URL || "/api/v1").replace(/\/$/, "");

export interface FieldProblem {
  field: string;
  message: string;
}

/** A failed API call, with the server's machine-readable code and a message fit to show people. */
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly details: FieldProblem[] = [],
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type Query = Record<string, string | number | boolean | null | undefined>;

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  query?: Query;
  body?: unknown;
  form?: FormData;
  auth?: boolean;
}

let onSessionLost: (() => void) | null = null;
let refreshing: Promise<boolean> | null = null;

/** Register what should happen when the session cannot be renewed. */
export function setSessionLostHandler(handler: (() => void) | null): void {
  onSessionLost = handler;
}

function url(path: string, query?: Query): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== null && value !== "") params.set(key, String(value));
  }
  const text = params.toString();
  return `${BASE}${path}${text ? `?${text}` : ""}`;
}

/** Exchange the refresh token for a new pair. Concurrent callers share one request. */
export function refreshSession(): Promise<boolean> {
  const refresh = tokens.refresh;
  if (!refresh) return Promise.resolve(false);
  if (!refreshing) {
    refreshing = (async () => {
      try {
        const response = await fetch(url("/auth/refresh"), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refreshToken: refresh }),
        });
        if (!response.ok) {
          if (response.status === 401) tokens.clear();
          return false;
        }
        const pair = (await response.json()) as TokenPair;
        tokens.set(pair.accessToken, pair.refreshToken);
        return true;
      } catch {
        return false;
      } finally {
        refreshing = null;
      }
    })();
  }
  return refreshing;
}

async function toError(response: Response): Promise<ApiError> {
  try {
    const body = (await response.json()) as { error?: { code: string; message: string; details?: FieldProblem[] } };
    if (body.error) return new ApiError(response.status, body.error.code, body.error.message, body.error.details ?? []);
  } catch {
    /* not JSON */
  }
  return new ApiError(response.status, "http_error", `The server answered ${response.status}.`);
}

async function send(path: string, options: RequestOptions, retried: boolean): Promise<Response> {
  const headers: Record<string, string> = {};
  if (options.auth !== false && tokens.access) headers.Authorization = `Bearer ${tokens.access}`;
  let body: BodyInit | undefined;
  if (options.form) {
    body = options.form;
  } else if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.body);
  }
  let response: Response;
  try {
    response = await fetch(url(path, options.query), { method: options.method ?? "GET", headers, body });
  } catch {
    throw new ApiError(0, "network", "Can't reach the server. Check your connection and try again.");
  }
  if (response.status === 401 && options.auth !== false && !retried) {
    if (await refreshSession()) return send(path, options, true);
    tokens.clear();
    onSessionLost?.();
  }
  return response;
}

/** Call the API and return the parsed JSON (or undefined for 204). Throws `ApiError`. */
export async function api<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await send(path, options, false);
  if (!response.ok) throw await toError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

/** Download an authenticated file and hand it to the browser. */
export async function download(path: string, filename: string, query?: Query): Promise<void> {
  const response = await send(path, { query }, false);
  if (!response.ok) throw await toError(response);
  const link = document.createElement("a");
  const objectUrl = URL.createObjectURL(await response.blob());
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
}

/** Turn any thrown value into a sentence for a toast or an inline message. */
export function messageOf(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return "Something went wrong. Please try again.";
}
