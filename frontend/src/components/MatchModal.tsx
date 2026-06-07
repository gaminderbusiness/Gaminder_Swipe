import React from "react";
import { View, Text, StyleSheet, TouchableOpacity, Image, Modal } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { Sparkles, Heart } from "lucide-react-native";
import { useRouter } from "expo-router";
import { colors, radius, spacing } from "@/src/lib/theme";

export default function MatchModal({
  visible,
  matchUser,
  matchId,
  onClose,
}: {
  visible: boolean;
  matchUser: any;
  matchId: string | null;
  onClose: () => void;
}) {
  const router = useRouter();
  if (!matchUser) return null;

  return (
    <Modal transparent visible={visible} animationType="fade" onRequestClose={onClose}>
      <View style={styles.backdrop} testID="match-modal">
        <LinearGradient
          colors={["rgba(139,92,246,0.5)", "rgba(0,229,255,0.3)", "rgba(5,5,5,0.95)"]}
          style={StyleSheet.absoluteFill}
        />
        <View style={styles.card}>
          <View style={styles.badge}>
            <Sparkles size={18} color={colors.neonBlue} />
            <Text style={styles.badgeText}>IT&apos;S A MATCH</Text>
          </View>
          <Text style={styles.title}>You and {matchUser.username} liked each other!</Text>
          <View style={styles.imgRow}>
            <Image source={{ uri: matchUser.profile_photo }} style={styles.avatar} />
            <View style={styles.heartWrap}>
              <Heart size={28} color={colors.neonBlue} fill={colors.neonBlue} />
            </View>
          </View>
          <TouchableOpacity
            testID="match-go-chat"
            style={styles.primary}
            onPress={() => {
              onClose();
              if (matchId) router.push(`/chat/${matchId}`);
            }}
          >
            <Text style={styles.primaryText}>Send a Message</Text>
          </TouchableOpacity>
          <TouchableOpacity testID="match-keep-swiping" onPress={onClose}>
            <Text style={styles.secondaryText}>Keep Swiping</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: { flex: 1, alignItems: "center", justifyContent: "center", padding: spacing.lg },
  card: { width: "100%", padding: spacing.lg, alignItems: "center", gap: spacing.md },
  badge: { flexDirection: "row", alignItems: "center", gap: 6, backgroundColor: colors.neonBlueSoft, borderWidth: 1, borderColor: "rgba(0,229,255,0.5)", paddingHorizontal: 12, paddingVertical: 6, borderRadius: radius.pill },
  badgeText: { color: colors.neonBlue, fontSize: 11, fontWeight: "800", letterSpacing: 1 },
  title: { color: colors.textPrimary, fontSize: 26, fontWeight: "800", textAlign: "center", letterSpacing: -0.5 },
  imgRow: { flexDirection: "row", alignItems: "center", marginVertical: spacing.lg },
  avatar: { width: 160, height: 200, borderRadius: radius.lg, borderWidth: 2, borderColor: colors.neonBlue },
  heartWrap: { position: "absolute", right: -10, top: "50%", marginTop: -28, width: 56, height: 56, borderRadius: 28, backgroundColor: colors.surface, alignItems: "center", justifyContent: "center", borderWidth: 2, borderColor: colors.neonBlue },
  primary: { backgroundColor: colors.purple, paddingVertical: 14, paddingHorizontal: 32, borderRadius: radius.pill, marginTop: spacing.md, minWidth: "80%", alignItems: "center" },
  primaryText: { color: "#fff", fontWeight: "700", fontSize: 16 },
  secondaryText: { color: colors.textSecondary, marginTop: spacing.sm, fontSize: 14 },
});
