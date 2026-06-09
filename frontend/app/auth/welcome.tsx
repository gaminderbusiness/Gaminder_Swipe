import { View, Text, StyleSheet, TouchableOpacity, Image } from "react-native";
import { useRouter } from "expo-router";
import { LinearGradient } from "expo-linear-gradient";
import { SafeAreaView } from "react-native-safe-area-context";
import { useTheme, radius, spacing, type ColorPalette } from "@/src/lib/theme";

const LOGO = require("@/assets/images/gaminder-logo-transparent.png");

export default function Welcome() {
  const router = useRouter();
  const { colors } = useTheme();
  const styles = makeStyles(colors);

  return (
    <View style={styles.root}>
      <LinearGradient
        colors={[colors.primarySoft, "transparent"]}
        style={styles.glow}
        start={{ x: 0.5, y: 0 }}
        end={{ x: 0.5, y: 1 }}
      />
      <SafeAreaView style={styles.safe} edges={["top", "bottom"]}>
        <View style={styles.hero}>
          <View style={styles.logoWrap} testID="app-logo">
            <Image source={LOGO} style={styles.logoImg} resizeMode="contain" />
          </View>
          <Text style={styles.title}>Gaminder</Text>
          <Text style={styles.subtitle}>Find your next squad. Match with gamers who play your games.</Text>
        </View>

        <Image
          source={{ uri: "https://images.pexels.com/photos/9071735/pexels-photo-9071735.jpeg" }}
          style={styles.heroImg}
          resizeMode="cover"
        />

        <View style={styles.actions}>
          <TouchableOpacity
            testID="login-cta"
            style={styles.primaryBtn}
            onPress={() => router.push("/auth/login")}
            activeOpacity={0.85}
          >
            <Text style={styles.primaryText}>Sign In</Text>
          </TouchableOpacity>
          <TouchableOpacity
            testID="signup-cta"
            style={styles.secondaryBtn}
            onPress={() => router.push("/auth/signup")}
            activeOpacity={0.8}
          >
            <Text style={styles.secondaryText}>Create New Account</Text>
          </TouchableOpacity>
          <Text style={styles.legal} testID="legal-text">
            By continuing, you agree to find gaming friends, not dates.
          </Text>
        </View>
      </SafeAreaView>
    </View>
  );
}

const makeStyles = (colors: ColorPalette) => StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  glow: { position: "absolute", top: 0, left: 0, right: 0, height: 400 },
  safe: { flex: 1, paddingHorizontal: spacing.lg, justifyContent: "space-between" },
  hero: { alignItems: "center", marginTop: spacing.xl },
  logoWrap: {
    width: 120, height: 120, borderRadius: radius.lg,
    backgroundColor: colors.logoBackdrop,
    borderWidth: 2, borderColor: colors.primary,
    alignItems: "center", justifyContent: "center",
    marginBottom: spacing.lg,
    overflow: "hidden",
  },
  logoImg: { width: "100%", height: "100%" },
  title: { color: colors.textPrimary, fontSize: 40, fontWeight: "900", letterSpacing: -1 },
  subtitle: { color: colors.textSecondary, fontSize: 16, lineHeight: 22, textAlign: "center", marginTop: spacing.sm, paddingHorizontal: spacing.md },
  heroImg: { width: "100%", height: 240, borderRadius: radius.lg, opacity: 0.85 },
  actions: { gap: spacing.sm, marginBottom: spacing.md },
  primaryBtn: { backgroundColor: colors.primary, paddingVertical: 16, borderRadius: radius.pill, alignItems: "center" },
  primaryText: { color: colors.inverseText === "#FFFFFF" ? "#FFFFFF" : "#FFFFFF", fontSize: 16, fontWeight: "700" },
  secondaryBtn: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.borderStrong, paddingVertical: 14, borderRadius: radius.pill, alignItems: "center" },
  secondaryText: { color: colors.textPrimary, fontSize: 15, fontWeight: "600" },
  legal: { color: colors.textMuted, fontSize: 11, textAlign: "center", marginTop: spacing.sm },
});
