import { createContext, useContext } from "react";

import type { DashboardDataSource, DecisionClient } from "../data/source";
import type { ResolvedTheme, ThemePreference } from "../lib/theme";
import type { StreamEvent } from "../types";

export type AppMode = "static" | "replay" | "live";

export interface AppContextValue {
  mode: AppMode;
  setMode: (mode: AppMode) => void;
  theme: ThemePreference;
  resolvedTheme: ResolvedTheme;
  setTheme: (theme: ThemePreference) => void;
  source: DashboardDataSource;
  decisionClient: DecisionClient | null;
  streamEvents: StreamEvent[];
  streamStatus: "idle" | "open" | "error";
}

export const AppContext = createContext<AppContextValue | null>(null);

export function useApp(): AppContextValue {
  const value = useContext(AppContext);
  if (!value) {
    throw new Error("useApp must be used inside AppContext");
  }
  return value;
}

export const MODE_LABELS: Record<AppMode, string> = {
  static: "Static",
  replay: "Replay",
  live: "Live",
};

export const MODE_DESCRIPTIONS: Record<AppMode, string> = {
  static: "Bundled JSON, offline, read-only.",
  replay: "Reads the replay API; decisions are recorded and read-only.",
  live: "Reads the live API and streams agent actions; decisions write back.",
};
