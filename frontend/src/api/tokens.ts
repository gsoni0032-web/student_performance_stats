/**
 * Token storage. The access token lives only in memory. The refresh token is kept in
 * sessionStorage so a page reload keeps you signed in, but closing the tab signs you out.
 */
const KEY = "pathway.refresh";
let accessToken: string | null = null;

function readRefresh(): string | null {
  try {
    return sessionStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export const tokens = {
  get access(): string | null {
    return accessToken;
  },
  get refresh(): string | null {
    return readRefresh();
  },
  set(access: string, refresh: string): void {
    accessToken = access;
    try {
      sessionStorage.setItem(KEY, refresh);
    } catch {
      /* without storage the session simply ends on reload */
    }
  },
  clear(): void {
    accessToken = null;
    try {
      sessionStorage.removeItem(KEY);
    } catch {
      /* nothing to clear */
    }
  },
};
