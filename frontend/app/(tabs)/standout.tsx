import { useEffect, useState, useCallback } from "react";
import { View, Text, StyleSheet, ScrollView, Image, TouchableOpacity, ActivityIndicator, RefreshControl } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Sparkles, Star } from "lucide-react-native";
import { useTheme, radius, spacing, activityLabel, statusColorFn, type ColorPalette } from "@/src/lib/theme";
import { api } from "@/src/lib/api";
import MatchModal from "@/src/components/MatchModal";

export default function Standout() {
  const { colors } = useTheme();
  const styles = makeStyles(colors);
  const [profiles, setProfiles] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [matchedUser, setMatchedUser] = useState<any>(null);
  const [matchId, setMatchId] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const d = await api.standout();
      setProfiles(d.profiles || []);
    } catch (e) { /* ignore */ }
    finally { setLoading(false); setRefreshing(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const onRefresh = () => { setRefreshing(true); load(); };

  const sendSuperLike = async (userId: string) => {
    try {
      const res = await api.swipe(userId, "superlike");
      setProfiles((p) => p.filter(x => x.id !== userId));
      if (res.matched && res.matched_user) {
        setMatchedUser(res.matched_user);
        setMatchId(res.match_id);
      }
    } catch (e) { /* ignore */ }
  };

  return (
    <SafeAreaView style={styles.root} edges={["top"]}>
      <View style={styles.header}>
        <Text style={styles.h1}>Standout</Text>
        <Text style={styles.h1sub}>Top compatibility matches & active gamers</Text>
      </View>

      {loading ? (
        <View style={{ flex: 1, justifyContent: "center" }}><ActivityIndicator color={colors.primary} /></View>
      ) : (
        <ScrollView
          contentContainerStyle={styles.list}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.primary} />}
        >
          {profiles.length === 0 ? (
            <Text style={styles.empty}>No standout profiles yet. Check back soon!</Text>
          ) : (
            profiles.map((p) => (
              <View key={p.id} style={styles.card} testID={`standout-${p.username}`}>
                <Image source={{ uri: p.profile_photo }} style={styles.img} />
                <View style={styles.matchBadge}>
                  <Sparkles size={12} color={colors.primary} />
                  <Text style={styles.matchText}>{p.match_percentage}%</Text>
                </View>
                <View style={styles.body}>
                  <View style={styles.statusRow}>
                    <View style={[styles.dot, { backgroundColor: statusColorFn(p.activity_status, colors) }]} />
                    <Text style={styles.status}>{activityLabel(p.activity_status, p.last_active)}</Text>
                  </View>
                  <Text style={styles.name}>{p.username}, {p.age}</Text>
                  <Text style={styles.meta}>{p.country} • {(p.languages || []).slice(0,2).join(", ")}</Text>
                  {p.shared_games && p.shared_games.length > 0 ? (
                    <View style={styles.tags}>
                      {p.shared_games.slice(0, 3).map((g: string) => (
                        <View key={g} style={styles.tag}><Text style={styles.tagText}>{g}</Text></View>
                      ))}
                    </View>
                  ) : null}
                  <TouchableOpacity testID={`super-${p.username}`} style={styles.superBtn} onPress={() => sendSuperLike(p.id)}>
                    <Star size={16} color={colors.accent} fill={colors.accent} />
                    <Text style={styles.superText}>Send Super Like</Text>
                  </TouchableOpacity>
                </View>
              </View>
            ))
          )}
        </ScrollView>
      )}

      <MatchModal visible={!!matchedUser} matchUser={matchedUser} matchId={matchId} onClose={() => { setMatchedUser(null); setMatchId(null); }} />
    </SafeAreaView>
  );
}

const makeStyles = (colors: ColorPalette) => StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  header: { paddingHorizontal: spacing.lg, paddingTop: spacing.sm, paddingBottom: spacing.md },
  h1: { color: colors.textPrimary, fontSize: 28, fontWeight: "800", letterSpacing: -0.5 },
  h1sub: { color: colors.textSecondary, fontSize: 13, marginTop: 2 },
  list: { padding: spacing.lg, gap: spacing.md, paddingBottom: spacing.xxl },
  empty: { color: colors.textSecondary, textAlign: "center", marginTop: spacing.xl },
  card: { backgroundColor: colors.surface, borderRadius: radius.lg, overflow: "hidden", borderWidth: 1, borderColor: colors.border },
  img: { width: "100%", height: 200 },
  matchBadge: { position: "absolute", top: 12, right: 12, flexDirection: "row", gap: 4, alignItems: "center", backgroundColor: colors.primarySoft, borderWidth: 1, borderColor: colors.primary, paddingHorizontal: 10, paddingVertical: 4, borderRadius: radius.pill },
  matchText: { color: colors.primary, fontSize: 12, fontWeight: "800" },
  body: { padding: spacing.md, gap: 6 },
  statusRow: { flexDirection: "row", alignItems: "center", gap: 6 },
  dot: { width: 8, height: 8, borderRadius: 4 },
  status: { color: colors.textSecondary, fontSize: 12, fontWeight: "600" },
  name: { color: colors.textPrimary, fontSize: 20, fontWeight: "700" },
  meta: { color: colors.textSecondary, fontSize: 13 },
  tags: { flexDirection: "row", flexWrap: "wrap", gap: 6, marginTop: 6 },
  tag: { backgroundColor: colors.primarySoft, borderWidth: 1, borderColor: colors.borderStrong, paddingHorizontal: 10, paddingVertical: 3, borderRadius: radius.sm },
  tagText: { color: colors.textPrimary, fontSize: 12, fontWeight: "600" },
  superBtn: { marginTop: spacing.sm, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6, paddingVertical: 10, backgroundColor: colors.accentSoft, borderWidth: 1, borderColor: colors.accent, borderRadius: radius.pill },
  superText: { color: colors.accent, fontWeight: "700" },
});
