import { useCallback, useState } from "react";

import { applyTheme, readTheme, type ThemeChoice } from "@/lib/theme";

export function useTheme(): [ThemeChoice, (choice: ThemeChoice) => void] {
  const [choice, setChoice] = useState<ThemeChoice>(readTheme);
  const update = useCallback((next: ThemeChoice) => {
    applyTheme(next);
    setChoice(next);
  }, []);
  return [choice, update];
}
