import { View, Text, StyleSheet, ScrollView, Image, TouchableOpacity } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { LogOut, Gamepad2, MapPin, Languages, ExternalLink } from "lucide-react-native";
import { LinearGradient } from "expo-linear-gradient";
import { colors, radius, spacing, activityLabel, statusColor } from "@/src/lib/theme";
import { useAuth } from "@/src/lib/auth";

export default function Profile() {
  const { user, signOut } = useAuth();
  if (!user) return null;

  const status = user.activity_status || "online";

  return (
    <SafeAreaView style={styles.root} edges={["top"]}>
      <ScrollView contentContainerStyle={{ paddingBottom: spacing.xxl }}>
        <View style={styles.hero}>
          <Image source={{ uri: user.profile_photo }} style={styles.heroImg} />
          <LinearGradient
            colors={["transparent", "rgba(5,5,5,0.95)"]}
            style={StyleSheet.absoluteFill}
          />
          <View style={styles.heroBody}>
            <View style={styles.statusRow}>
              <View style={[styles.statusDot, { backgroundColor: statusColor(status) }]} />
              <Text style={styles.statusLabel}>{activityLabel(status, user.last_active)}</Text>
            </View>
            <Text style={styles.name} testID="profile-username">{user.username}, {user.age}</Text>
            <View style={styles.metaRow}>
              <MapPin size={14} color={colors.textSecondary} />
              <Text style={styles.metaText}>{user.country}</Text>
              <Text style={styles.metaDot}>•</Text>
              <Languages size={14} color={colors.textSecondary} />
              <Text style={styles.metaText}>{(user.languages || []).join(", ")}</Text>
            </View>
          </View>
        </View>

        <View style={styles.statsRow}>
          <View style={styles.stat}>
            <Text style={styles.statValue}>{Math.max(0, 20 - (user.daily_likes_used || 0))}</Text>
            <Text style={styles.statLabel}>Likes left</Text>
          </View>
          <View style={styles.stat}>
            <Text style={styles.statValue}>{user.super_likes_remaining ?? 0}</Text>
            <Text style={styles.statLabel}>Super Likes</Text>
          </View>
          <View style={styles.stat}>
            <Text style={styles.statValue}>{(user.top_games || []).length}</Text>
            <Text style={styles.statLabel}>Games</Text>
          </View>
        </View>

        {user.bio ? (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>About</Text>
            <Text style={styles.bio} testID="profile-bio">{user.bio}</Text>
          </View>
        ) : null}

        <View style={styles.section}>
          <View style={styles.steamRow}>
            <View style={{ flex: 1 }}>
              <Text style={styles.sectionTitle}>Steam Library</Text>
              <Text style={styles.sectionSub}>Top played games</Text>
            </View>
            <View style={styles.steamBadge}>
              <Gamepad2 size={14} color={colors.neonBlue} />
              <Text style={styles.steamBadgeText}>STEAM</Text>
            </View>
          </View>
          {(user.top_games || []).length === 0 ? (
            <Text style={styles.empty}>No games added yet.</Text>
          ) : (
            <View style={{ gap: 8, marginTop: spacing.sm }}>
              {user.top_games.map((g: any, i: number) => (
                <View key={g.name} style={styles.gameRow} testID={`profile-game-${g.name}`}>
                  <View style={[styles.rank, i === 0 && { backgroundColor: colors.neonBlueSoft, borderColor: colors.neonBlue }]}>
                    <Text style={[styles.rankText, i === 0 && { color: colors.neonBlue }]}>{i + 1}</Text>
                  </View>
                  <Text style={styles.gameName}>{g.name}</Text>
                  <Text style={styles.gameHours}>{g.hours}h</Text>
                </View>
              ))}
            </View>
          )}
          {user.steam_profile_url ? (
            <View style={[styles.steamLinkRow]}>
              <ExternalLink size={14} color={colors.textSecondary} />
              <Text style={styles.steamLink} numberOfLines={1}>{user.steam_profile_url}</Text>
            </View>
          ) : null}
        </View>

        <TouchableOpacity testID="sign-out-btn" style={styles.signOut} onPress={signOut}>
          <LogOut size={18} color={colors.danger} />
          <Text style={styles.signOutText}>Sign out</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  hero: { height: 340, position: "relative" },
  heroImg: { width: "100%", height: "100%" },
  heroBody: { position: "absolute", left: 0, right: 0, bottom: 0, padding: spacing.lg, gap: 4 },
  statusRow: { flexDirection: "row", alignItems: "center", gap: 6 },
  statusDot: { width: 8, height: 8, borderRadius: 4 },
  statusLabel: { color: colors.textSecondary, fontSize: 12, fontWeight: "600" },
  name: { color: colors.textPrimary, fontSize: 28, fontWeight: "800" },
  metaRow: { flexDirection: "row", alignItems: "center", gap: 6, marginTop: 2 },
  metaText: { color: colors.textSecondary, fontSize: 13 },
  metaDot: { color: colors.textMuted, marginHorizontal: 4 },
  statsRow: { flexDirection: "row", gap: spacing.sm, marginHorizontal: spacing.lg, marginTop: spacing.lg },
  stat: { flex: 1, backgroundColor: colors.surface, padding: spacing.md, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border, alignItems: "center" },
  statValue: { color: colors.neonBlue, fontSize: 24, fontWeight: "800" },
  statLabel: { color: colors.textSecondary, fontSize: 11, fontWeight: "600", letterSpacing: 0.5, textTransform: "uppercase", marginTop: 4 },
  section: { padding: spacing.lg, gap: 6 },
  sectionTitle: { color: colors.textPrimary, fontSize: 18, fontWeight: "700" },
  sectionSub: { color: colors.textMuted, fontSize: 12 },
  bio: { color: colors.textPrimary, fontSize: 15, lineHeight: 22 },
  steamRow: { flexDirection: "row", alignItems: "center" },
  steamBadge: { flexDirection: "row", alignItems: "center", gap: 4, paddingHorizontal: 10, paddingVertical: 4, backgroundColor: colors.neonBlueSoft, borderWidth: 1, borderColor: "rgba(0,229,255,0.4)", borderRadius: radius.pill },
  steamBadgeText: { color: colors.neonBlue, fontSize: 10, fontWeight: "800", letterSpacing: 1 },
  gameRow: { flexDirection: "row", alignItems: "center", gap: spacing.md, padding: 12, backgroundColor: colors.surface, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border },
  rank: { width: 26, height: 26, borderRadius: 13, backgroundColor: colors.surfaceElev, alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: colors.border },
  rankText: { color: colors.textSecondary, fontSize: 12, fontWeight: "700" },
  gameName: { flex: 1, color: colors.textPrimary, fontSize: 15, fontWeight: "600" },
  gameHours: { color: colors.neonBlue, fontWeight: "700" },
  steamLinkRow: { flexDirection: "row", alignItems: "center", gap: 6, marginTop: spacing.sm },
  steamLink: { color: colors.textSecondary, fontSize: 12, flex: 1 },
  empty: { color: colors.textSecondary, fontSize: 14, marginTop: spacing.sm },
  signOut: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8, margin: spacing.lg, paddingVertical: 14, borderRadius: radius.pill, borderWidth: 1, borderColor: "rgba(239,68,68,0.4)", backgroundColor: "rgba(239,68,68,0.08)" },
  signOutText: { color: colors.danger, fontWeight: "700" },
});
