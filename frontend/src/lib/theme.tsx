import React, { createContext, useContext, useEffect, useState, useCallback, useMemo } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";

export type ThemeMode = "dark" | "light";

export type ColorPalette = {
  bg: string;
  surface: string;
  surfaceElev: string;
  border: string;
  borderStrong: string;
  primary: string;           // brand orange (Gaminder fire)
  primarySoft: string;
  primaryDeep: string;
  accent: string;            // warm yellow-orange highlight
  accentSoft: string;
  textPrimary: string;
  textSecondary: string;
  textMuted: string;
  inverseText: string;
  online: string;
  away: string;
  offline: string;
  pass: string;
  like: string;
  superlike: string;
  danger: string;
  // logo backdrop (white on light, black on dark per user request)
  logoBackdrop: string;
  overlayBackdrop: string;   // for modals / scrim
};

const DARK: ColorPalette = {
  bg: "#050505",
  surface: "#15100D",
  surfaceElev: "#1F1815",
  border: "rgba(255,106,26,0.10)",
  borderStrong: "rgba(255,106,26,0.25)",
  primary: "#FF6A1A",
  primarySoft: "rgba(255,106,26,0.15)",
  primaryDeep: "#FF3D00",
  accent: "#FFAA33",
  accentSoft: "rgba(255,170,51,0.18)",
  textPrimary: "#F8F2EE",
  textSecondary: "#B5A89F",
  textMuted: "#6E625B",
  inverseText: "#15100D",
  online: "#10B981",
  away: "#FBBF24",
  offline: "#3F3F46",
  pass: "#EC4899",
  like: "#FF6A1A",
  superlike: "#FFAA33",
  danger: "#EF4444",
  logoBackdrop: "#050505",
  overlayBackdrop: "rgba(5,5,5,0.85)",
};

const LIGHT: ColorPalette = {
  bg: "#FFF8F2",
  surface: "#FFFFFF",
  surfaceElev: "#FBF1E8",
  border: "rgba(255,106,26,0.18)",
  borderStrong: "rgba(255,106,26,0.40)",
  primary: "#E65A0F",
  primarySoft: "rgba(230,90,15,0.10)",
  primaryDeep: "#C73E00",
  accent: "#E68A00",
  accentSoft: "rgba(230,138,0,0.14)",
  textPrimary: "#1A100A",
  textSecondary: "#5C4C42",
  textMuted: "#A89890",
  inverseText: "#FFFFFF",
  online: "#059669",
  away: "#D97706",
  offline: "#B5A89F",
  pass: "#DB2777",
  like: "#E65A0F",
  superlike: "#D97706",
  danger: "#DC2626",
  logoBackdrop: "#FFFFFF",
  overlayBackdrop: "rgba(26,16,10,0.75)",
};

export const radius = { sm: 8, md: 12, lg: 24, pill: 9999 };
export const spacing = { xs: 4, sm: 8, md: 16, lg: 24, xl: 32, xxl: 48 };

export const activityLabel = (status: string, lastActiveISO?: string | null) => {
  if (status === "online") return "Online Now";
  if (!lastActiveISO) return "Offline";
  try {
    const diff = Date.now() - new Date(lastActiveISO).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 60) return `Active ${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `Active ${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    return `Active ${days}d ago`;
  } catch {
    return "Offline";
  }
};

type ThemeCtx = {
  mode: ThemeMode;
  colors: ColorPalette;
  toggle: () => void;
  setMode: (m: ThemeMode) => void;
};

const Ctx = createContext<ThemeCtx | null>(null);
const STORAGE_KEY = "gaminder_theme_mode";

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [mode, setModeState] = useState<ThemeMode>("dark");

  useEffect(() => {
    (async () => {
      try {
        const saved = await AsyncStorage.getItem(STORAGE_KEY);
        if (saved === "light" || saved === "dark") setModeState(saved);
      } catch {}
    })();
  }, []);

  const setMode = useCallback(async (m: ThemeMode) => {
    setModeState(m);
    try { await AsyncStorage.setItem(STORAGE_KEY, m); } catch {}
  }, []);

  const toggle = useCallback(() => {
    setMode(mode === "dark" ? "light" : "dark");
  }, [mode, setMode]);

  const value = useMemo<ThemeCtx>(() => ({
    mode,
    colors: mode === "dark" ? DARK : LIGHT,
    toggle,
    setMode,
  }), [mode, toggle, setMode]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useTheme(): ThemeCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useTheme must be used inside ThemeProvider");
  return ctx;
}

// Backward-compat helper: status colors via current theme
export const statusColorFn = (status: string, c: ColorPalette) => {
  if (status === "online") return c.online;
  if (status === "away") return c.away;
  return c.offline;
};
