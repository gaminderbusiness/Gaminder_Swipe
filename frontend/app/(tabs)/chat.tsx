import { useState, useCallback } from "react";
import { View, Text, StyleSheet, FlatList, Image, TouchableOpacity, ActivityIndicator } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter, useFocusEffect } from "expo-router";
import { MessageCircle } from "lucide-react-native";
import { useTheme, radius, spacing, statusColorFn, type ColorPalette } from "@/src/lib/theme";
import { api } from "@/src/lib/api";

export default function ChatList() {
  const router = useRouter();
  const { colors } = useTheme();
  const styles = makeStyles(colors);
  const [matches, setMatches] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const d = await api.matches();
      const sorted = (d.matches || []).slice().sort((a: any, b: any) => {
        const at = a.last_message_at || a.created_at;
        const bt = b.last_message_at || b.created_at;
        return new Date(bt).getTime() - new Date(at).getTime();
      });
      setMatches(sorted);
    } catch (e) { /* ignore */ }
    finally { setLoading(false); }
  }, []);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  return (
    <SafeAreaView style={styles.root} edges={["top"]}>
      <View style={styles.header}>
        <Text style={styles.h1}>Chat</Text>
        <Text style={styles.h1sub}>Talk to your gaming buddies</Text>
      </View>

      {loading ? (
        <View style={{ flex: 1, justifyContent: "center" }}><ActivityIndicator color={colors.primary} /></View>
      ) : matches.length === 0 ? (
        <View style={styles.empty} testID="chat-empty">
          <MessageCircle size={48} color={colors.textMuted} />
          <Text style={styles.emptyTitle}>No conversations yet</Text>
          <Text style={styles.emptyText}>Match with a player to start chatting.</Text>
        </View>
      ) : (
        <FlatList
          data={matches}
          keyExtractor={(m) => m.match_id}
          contentContainerStyle={{ padding: spacing.lg, gap: spacing.sm }}
          renderItem={({ item }) => (
            <TouchableOpacity
              testID={`chat-row-${item.user.username}`}
              style={styles.row}
              onPress={() => router.push(`/chat/${item.match_id}`)}
            >
              <View>
                <Image source={{ uri: item.user.profile_photo }} style={styles.avatar} />
                <View style={[styles.statusDot, { backgroundColor: statusColorFn(item.user.activity_status, colors), borderColor: colors.surface }]} />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.name}>{item.user.username}</Text>
                <Text style={styles.preview} numberOfLines={1}>
                  {item.last_message || "Say hi to start the chat"}
                </Text>
              </View>
              <Text style={styles.statusText}>{item.user.activity_status === "online" ? "Online" : ""}</Text>
            </TouchableOpacity>
          )}
        />
      )}
    </SafeAreaView>
  );
}

const makeStyles = (colors: ColorPalette) => StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  header: { paddingHorizontal: spacing.lg, paddingTop: spacing.sm, paddingBottom: spacing.md },
  h1: { color: colors.textPrimary, fontSize: 28, fontWeight: "800", letterSpacing: -0.5 },
  h1sub: { color: colors.textSecondary, fontSize: 13, marginTop: 2 },
  row: { flexDirection: "row", alignItems: "center", gap: spacing.md, backgroundColor: colors.surface, padding: spacing.md, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border },
  avatar: { width: 52, height: 52, borderRadius: 26, borderWidth: 1, borderColor: colors.borderStrong },
  statusDot: { position: "absolute", bottom: 0, right: 0, width: 12, height: 12, borderRadius: 6, borderWidth: 2 },
  name: { color: colors.textPrimary, fontSize: 16, fontWeight: "700" },
  preview: { color: colors.textSecondary, fontSize: 13, marginTop: 2 },
  statusText: { color: colors.online, fontSize: 11, fontWeight: "700" },
  empty: { flex: 1, alignItems: "center", justifyContent: "center", padding: spacing.xl, gap: 8 },
  emptyTitle: { color: colors.textPrimary, fontSize: 20, fontWeight: "700", marginTop: spacing.md },
  emptyText: { color: colors.textSecondary, textAlign: "center" },
});
