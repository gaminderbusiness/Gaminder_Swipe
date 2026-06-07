export const colors = {
  bg: "#050505",
  surface: "#0F0F13",
  surfaceElev: "#16161C",
  border: "rgba(255,255,255,0.06)",
  borderStrong: "rgba(255,255,255,0.12)",
  neonBlue: "#00E5FF",
  purple: "#8B5CF6",
  purpleSoft: "rgba(139,92,246,0.15)",
  neonBlueSoft: "rgba(0,229,255,0.12)",
  textPrimary: "#F8FAFC",
  textSecondary: "#94A3B8",
  textMuted: "#52525B",
  online: "#10B981",
  away: "#FBBF24",
  offline: "#3F3F46",
  pass: "#EC4899",
  like: "#00E5FF",
  superlike: "#8B5CF6",
  danger: "#EF4444",
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

export const statusColor = (status: string) => {
  if (status === "online") return colors.online;
  if (status === "away") return colors.away;
  return colors.offline;
};
