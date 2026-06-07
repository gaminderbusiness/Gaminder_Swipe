import { View, Text, StyleSheet, TouchableOpacity, Image } from "react-native";
import { useRouter } from "expo-router";
import { LinearGradient } from "expo-linear-gradient";
import { SafeAreaView } from "react-native-safe-area-context";
import { Gamepad2 } from "lucide-react-native";
import { colors, radius, spacing } from "@/src/lib/theme";

export default function Welcome() {
  const router = useRouter();

  return (
    <View style={styles.root}>
      <LinearGradient
        colors={["rgba(139,92,246,0.18)", "transparent"]}
        style={styles.glow}
        start={{ x: 0.5, y: 0 }}
        end={{ x: 0.5, y: 1 }}
      />
      <SafeAreaView style={styles.safe} edges={["top", "bottom"]}>
        <View style={styles.hero}>
          <View style={styles.logoWrap} testID="app-logo">
            <Gamepad2 size={42} color={colors.neonBlue} />
          </View>
          <Text style={styles.title}>Gaming Buddy</Text>
          <Text style={styles.subtitle}>Find your next squad. Match with gamers who play your games.</Text>
        </View>

        <Image
          source={{ uri: "https://images.pexels.com/photos/9071735/pexels-photo-9071735.jpeg" }}
          style={styles.heroImg}
          resizeMode="cover"
        />

        <View style={styles.actions}>
          <TouchableOpacity
            testID="signup-cta"
            style={styles.primaryBtn}
            onPress={() => router.push("/auth/signup")}
            activeOpacity={0.8}
          >
            <Text style={styles.primaryText}>Create Account</Text>
          </TouchableOpacity>
          <TouchableOpacity
            testID="login-cta"
            style={styles.secondaryBtn}
            onPress={() => router.push("/auth/login")}
            activeOpacity={0.8}
          >
            <Text style={styles.secondaryText}>I already have an account</Text>
          </TouchableOpacity>
          <Text style={styles.legal} testID="legal-text">
            By continuing, you agree to find gaming friends, not dates.
          </Text>
        </View>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  glow: { position: "absolute", top: 0, left: 0, right: 0, height: 400 },
  safe: { flex: 1, paddingHorizontal: spacing.lg, justifyContent: "space-between" },
  hero: { alignItems: "center", marginTop: spacing.xl },
  logoWrap: {
    width: 84, height: 84, borderRadius: radius.lg,
    backgroundColor: colors.neonBlueSoft,
    borderWidth: 1, borderColor: "rgba(0,229,255,0.4)",
    alignItems: "center", justifyContent: "center",
    marginBottom: spacing.lg,
  },
  title: { color: colors.textPrimary, fontSize: 36, fontWeight: "800", letterSpacing: -1 },
  subtitle: { color: colors.textSecondary, fontSize: 16, lineHeight: 22, textAlign: "center", marginTop: spacing.sm, paddingHorizontal: spacing.md },
  heroImg: { width: "100%", height: 280, borderRadius: radius.lg, opacity: 0.85 },
  actions: { gap: spacing.sm, marginBottom: spacing.md },
  primaryBtn: { backgroundColor: colors.purple, paddingVertical: 16, borderRadius: radius.pill, alignItems: "center" },
  primaryText: { color: "#fff", fontSize: 16, fontWeight: "700" },
  secondaryBtn: { backgroundColor: "rgba(255,255,255,0.05)", borderWidth: 1, borderColor: colors.borderStrong, paddingVertical: 14, borderRadius: radius.pill, alignItems: "center" },
  secondaryText: { color: colors.textPrimary, fontSize: 15, fontWeight: "600" },
  legal: { color: colors.textMuted, fontSize: 11, textAlign: "center", marginTop: spacing.sm },
});
