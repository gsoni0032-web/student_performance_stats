import { useEffect } from "react";

/** Set the browser tab title so screen reader users hear where they are after navigating. */
export function useDocumentTitle(title: string): void {
  useEffect(() => {
    document.title = `${title} · Pathway`;
  }, [title]);
}
