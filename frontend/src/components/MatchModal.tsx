import React from "react";
import { View, Text, StyleSheet, TouchableOpacity, Image, Modal } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { Sparkles, Heart } from "lucide-react-native";
import { useRouter } from "expo-router";
import { useTheme, radius, spacing, type ColorPalette } from "@/src/lib/theme";

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
  const { colors } = useTheme();
  const styles = makeStyles(colors);
  if (!matchUser) return null;

  return (
    <Modal transparent visible={visible} animationType="fade" onRequestClose={onClose}>
      <View style={styles.backdrop} testID="match-modal">
        <LinearGradient
          colors={["rgba(255,106,26,0.55)", "rgba(255,61,0,0.35)", colors.overlayBackdrop]}
          style={StyleSheet.absoluteFill}
        />
        <View style={styles.card}>
          <View style={styles.badge}>
            <Sparkles size={18} color={colors.primary} />
            <Text style={styles.badgeText}>IT&apos;S A MATCH</Text>
          </View>
          <Text style={styles.title}>You and {matchUser.username} liked each other!</Text>
          <View style={styles.imgRow}>
            <Image source={{ uri: matchUser.profile_photo }} style={styles.avatar} />
            <View style={styles.heartWrap}>
              <Heart size={28} color={colors.primary} fill={colors.primary} />
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

const makeStyles = (colors: ColorPalette) => StyleSheet.create({
  backdrop: { flex: 1, alignItems: "center", justifyContent: "center", padding: spacing.lg },
  card: { width: "100%", padding: spacing.lg, alignItems: "center", gap: spacing.md },
  badge: { flexDirection: "row", alignItems: "center", gap: 6, backgroundColor: colors.primarySoft, borderWidth: 1, borderColor: colors.primary, paddingHorizontal: 12, paddingVertical: 6, borderRadius: radius.pill },
  badgeText: { color: colors.primary, fontSize: 11, fontWeight: "800", letterSpacing: 1 },
  title: { color: "#FFFFFF", fontSize: 26, fontWeight: "800", textAlign: "center", letterSpacing: -0.5 },
  imgRow: { flexDirection: "row", alignItems: "center", marginVertical: spacing.lg },
  avatar: { width: 160, height: 200, borderRadius: radius.lg, borderWidth: 2, borderColor: colors.primary },
  heartWrap: { position: "absolute", right: -10, top: "50%", marginTop: -28, width: 56, height: 56, borderRadius: 28, backgroundColor: colors.surface, alignItems: "center", justifyContent: "center", borderWidth: 2, borderColor: colors.primary },
  primary: { backgroundColor: colors.primary, paddingVertical: 14, paddingHorizontal: 32, borderRadius: radius.pill, marginTop: spacing.md, minWidth: "80%", alignItems: "center" },
  primaryText: { color: "#FFFFFF", fontWeight: "700", fontSize: 16 },
  secondaryText: { color: "#E5DCD4", marginTop: spacing.sm, fontSize: 14 },
});
