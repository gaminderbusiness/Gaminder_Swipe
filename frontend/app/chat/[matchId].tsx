import { useEffect, useState, useRef, useCallback } from "react";
import { View, Text, StyleSheet, TextInput, TouchableOpacity, Image, FlatList, KeyboardAvoidingView, Platform, ActivityIndicator } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useLocalSearchParams, useRouter } from "expo-router";
import { ArrowLeft, Send } from "lucide-react-native";
import { colors, radius, spacing, activityLabel, statusColor } from "@/src/lib/theme";
import { api } from "@/src/lib/api";
import { useAuth } from "@/src/lib/auth";

export default function ChatScreen() {
  const router = useRouter();
  const { matchId } = useLocalSearchParams<{ matchId: string }>();
  const { user } = useAuth();
  const [messages, setMessages] = useState<any[]>([]);
  const [other, setOther] = useState<any>(null);
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const listRef = useRef<FlatList>(null);

  const load = useCallback(async (silent = false) => {
    if (!matchId) return;
    if (!silent) setLoading(true);
    try {
      const d = await api.getMessages(matchId);
      setMessages(d.messages || []);
      setOther(d.other_user || null);
    } catch (e) { /* ignore */ }
    finally { if (!silent) setLoading(false); }
  }, [matchId]);

  useEffect(() => { load(); }, [load]);

  // Poll every 3s
  useEffect(() => {
    const id = setInterval(() => load(true), 3000);
    return () => clearInterval(id);
  }, [load]);

  const send = async () => {
    if (!text.trim() || !matchId) return;
    setSending(true);
    const msg = text.trim();
    setText("");
    try {
      const m = await api.sendMessage(matchId, msg);
      setMessages((cur) => [...cur, m]);
      setTimeout(() => listRef.current?.scrollToEnd({ animated: true }), 50);
    } catch (e) { /* ignore */ }
    finally { setSending(false); }
  };

  return (
    <SafeAreaView style={styles.root} edges={["top", "bottom"]}>
      <View style={styles.header}>
        <TouchableOpacity testID="chat-back" onPress={() => router.back()} style={styles.back}>
          <ArrowLeft size={22} color={colors.textPrimary} />
        </TouchableOpacity>
        {other ? (
          <View style={styles.headerCenter}>
            <Image source={{ uri: other.profile_photo }} style={styles.avatar} />
            <View>
              <Text style={styles.name} testID="chat-other-name">{other.username}</Text>
              <View style={styles.statusRow}>
                <View style={[styles.dot, { backgroundColor: statusColor(other.activity_status) }]} />
                <Text style={styles.statusText}>{activityLabel(other.activity_status, other.last_active)}</Text>
              </View>
            </View>
          </View>
        ) : null}
      </View>

      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={{ flex: 1 }} keyboardVerticalOffset={Platform.OS === "ios" ? 0 : 0}>
        {loading ? (
          <View style={{ flex: 1, justifyContent: "center" }}><ActivityIndicator color={colors.neonBlue} /></View>
        ) : (
          <FlatList
            ref={listRef}
            data={messages}
            keyExtractor={(m) => m.id}
            contentContainerStyle={{ padding: spacing.md, gap: 6 }}
            renderItem={({ item }) => {
              const isMine = item.sender_id === user?.id;
              return (
                <View style={[styles.bubbleRow, isMine ? styles.bubbleRowMine : styles.bubbleRowTheirs]}>
                  <View style={[styles.bubble, isMine ? styles.bubbleMine : styles.bubbleTheirs]} testID={`msg-${item.id}`}>
                    <Text style={[styles.msgText, isMine && { color: "#fff" }]}>{item.text}</Text>
                  </View>
                </View>
              );
            }}
            onContentSizeChange={() => listRef.current?.scrollToEnd({ animated: false })}
            ListEmptyComponent={
              <View style={{ alignItems: "center", padding: spacing.xl }}>
                <Text style={{ color: colors.textSecondary }}>Say hi to {other?.username || "your buddy"}!</Text>
              </View>
            }
          />
        )}

        <View style={styles.inputBar}>
          <TextInput
            testID="chat-input"
            value={text}
            onChangeText={setText}
            placeholder="Type a message..."
            placeholderTextColor={colors.textMuted}
            style={styles.input}
            multiline
            maxLength={500}
          />
          <TouchableOpacity testID="send-btn" style={[styles.sendBtn, (!text.trim() || sending) && { opacity: 0.5 }]} onPress={send} disabled={!text.trim() || sending}>
            <Send size={20} color="#fff" />
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  header: { flexDirection: "row", alignItems: "center", padding: spacing.md, gap: spacing.md, borderBottomWidth: 1, borderBottomColor: colors.border },
  back: { width: 40, height: 40, borderRadius: 20, backgroundColor: colors.surface, alignItems: "center", justifyContent: "center" },
  headerCenter: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  avatar: { width: 40, height: 40, borderRadius: 20 },
  name: { color: colors.textPrimary, fontWeight: "700", fontSize: 15 },
  statusRow: { flexDirection: "row", alignItems: "center", gap: 4, marginTop: 2 },
  dot: { width: 6, height: 6, borderRadius: 3 },
  statusText: { color: colors.textSecondary, fontSize: 11 },
  bubbleRow: { flexDirection: "row" },
  bubbleRowMine: { justifyContent: "flex-end" },
  bubbleRowTheirs: { justifyContent: "flex-start" },
  bubble: { maxWidth: "78%", paddingHorizontal: 14, paddingVertical: 10, borderRadius: 18 },
  bubbleMine: { backgroundColor: colors.purple, borderBottomRightRadius: 4 },
  bubbleTheirs: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, borderBottomLeftRadius: 4 },
  msgText: { color: colors.textPrimary, fontSize: 15, lineHeight: 20 },
  inputBar: { flexDirection: "row", alignItems: "flex-end", gap: 8, padding: spacing.md, borderTopWidth: 1, borderTopColor: colors.border, backgroundColor: colors.bg },
  input: { flex: 1, color: colors.textPrimary, backgroundColor: colors.surface, paddingHorizontal: 14, paddingVertical: 10, borderRadius: radius.lg, fontSize: 15, maxHeight: 100, borderWidth: 1, borderColor: colors.border },
  sendBtn: { width: 44, height: 44, borderRadius: 22, backgroundColor: colors.neonBlue, alignItems: "center", justifyContent: "center" },
});
