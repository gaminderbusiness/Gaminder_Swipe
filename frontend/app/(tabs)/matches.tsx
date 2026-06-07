import { useEffect, useState, useCallback } from "react";
import { View, Text, StyleSheet, FlatList, Image, TouchableOpacity, ActivityIndicator, RefreshControl } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter, useFocusEffect } from "expo-router";
import { Heart } from "lucide-react-native";
import { colors, radius, spacing, activityLabel, statusColor } from "@/src/lib/theme";
import { api } from "@/src/lib/api";

export default function Matches() {
  const router = useRouter();
  const [matches, setMatches] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      const d = await api.matches();
      setMatches(d.matches || []);
    } catch (e) { /* ignore */ }
    finally { setLoading(false); setRefreshing(false); }
  }, []);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  return (
    <SafeAreaView style={styles.root} edges={["top"]}>
      <View style={styles.header}>
        <Text style={styles.h1}>Matches</Text>
        <Text style={styles.h1sub}>{matches.length} gaming {matches.length === 1 ? "buddy" : "buddies"}</Text>
      </View>

      {loading ? (
        <View style={{ flex: 1, justifyContent: "center" }}><ActivityIndicator color={colors.neonBlue} /></View>
      ) : matches.length === 0 ? (
        <View style={styles.empty} testID="matches-empty">
          <Heart size={48} color={colors.textMuted} />
          <Text style={styles.emptyTitle}>No matches yet</Text>
          <Text style={styles.emptyText}>Start swiping to find your gaming squad.</Text>
          <TouchableOpacity onPress={() => router.push("/(tabs)/swipe")} style={styles.cta}>
            <Text style={styles.ctaText}>Go to Swipe</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <FlatList
          data={matches}
          keyExtractor={(m) => m.match_id}
          contentContainerStyle={{ padding: spacing.lg, gap: spacing.sm }}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} tintColor={colors.neonBlue} />}
          renderItem={({ item }) => (
            <TouchableOpacity
              testID={`match-${item.user.username}`}
              style={styles.row}
              onPress={() => router.push(`/chat/${item.match_id}`)}
            >
              <View>
                <Image source={{ uri: item.user.profile_photo }} style={styles.avatar} />
                <View style={[styles.statusDot, { backgroundColor: statusColor(item.user.activity_status), borderColor: colors.surface }]} />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.name}>{item.user.username}</Text>
                <Text style={styles.preview} numberOfLines={1}>
                  {item.last_message || `${activityLabel(item.user.activity_status, item.user.last_active)} — say hi!`}
                </Text>
              </View>
            </TouchableOpacity>
          )}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  header: { paddingHorizontal: spacing.lg, paddingTop: spacing.sm, paddingBottom: spacing.md },
  h1: { color: colors.textPrimary, fontSize: 28, fontWeight: "800", letterSpacing: -0.5 },
  h1sub: { color: colors.textSecondary, fontSize: 13, marginTop: 2 },
  row: { flexDirection: "row", alignItems: "center", gap: spacing.md, backgroundColor: colors.surface, padding: spacing.md, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border },
  avatar: { width: 56, height: 56, borderRadius: 28, borderWidth: 1, borderColor: colors.borderStrong },
  statusDot: { position: "absolute", bottom: 0, right: 0, width: 14, height: 14, borderRadius: 7, borderWidth: 2 },
  name: { color: colors.textPrimary, fontSize: 16, fontWeight: "700" },
  preview: { color: colors.textSecondary, fontSize: 13, marginTop: 2 },
  empty: { flex: 1, alignItems: "center", justifyContent: "center", padding: spacing.xl, gap: 8 },
  emptyTitle: { color: colors.textPrimary, fontSize: 20, fontWeight: "700", marginTop: spacing.md },
  emptyText: { color: colors.textSecondary, textAlign: "center" },
  cta: { marginTop: spacing.md, backgroundColor: colors.purple, paddingVertical: 12, paddingHorizontal: 28, borderRadius: radius.pill },
  ctaText: { color: "#fff", fontWeight: "700" },
});
