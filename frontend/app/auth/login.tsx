import { useState } from "react";
import { View, Text, StyleSheet, TextInput, TouchableOpacity, ScrollView, KeyboardAvoidingView, Platform, Image } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { ArrowLeft } from "lucide-react-native";
import { useTheme, radius, spacing, type ColorPalette } from "@/src/lib/theme";
import { useAuth } from "@/src/lib/auth";

const LOGO = require("@/assets/images/gaminder-logo-transparent.png");

export default function Login() {
  const router = useRouter();
  const { signIn } = useAuth();
  const { colors } = useTheme();
  const styles = makeStyles(colors);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const submit = async () => {
    setErr(null);
    setLoading(true);
    try {
      await signIn(email.trim(), password);
    } catch (e: any) {
      setErr(e.message || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.root} edges={["top", "bottom"]}>
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          <TouchableOpacity onPress={() => router.back()} style={styles.back} testID="back-btn">
            <ArrowLeft size={22} color={colors.textPrimary} />
          </TouchableOpacity>
          <View style={styles.logoRow}>
            <View style={styles.logoBox}>
              <Image source={LOGO} style={styles.logoImg} resizeMode="contain" />
            </View>
          </View>
          <Text style={styles.title}>Welcome back</Text>
          <Text style={styles.subtitle}>Sign in to find your gaming squad.</Text>

          <View style={styles.field}>
            <Text style={styles.label}>Email</Text>
            <TextInput
              testID="login-email-input"
              value={email}
              onChangeText={setEmail}
              autoCapitalize="none"
              keyboardType="email-address"
              placeholder="you@gaming.gg"
              placeholderTextColor={colors.textMuted}
              style={styles.input}
            />
          </View>
          <View style={styles.field}>
            <Text style={styles.label}>Password</Text>
            <TextInput
              testID="login-password-input"
              value={password}
              onChangeText={setPassword}
              secureTextEntry
              placeholder="••••••••"
              placeholderTextColor={colors.textMuted}
              style={styles.input}
            />
          </View>

          {err ? <Text style={styles.err} testID="login-error">{err}</Text> : null}

          <TouchableOpacity
            testID="login-submit-button"
            style={[styles.primary, loading && { opacity: 0.6 }]}
            onPress={submit}
            disabled={loading}
          >
            <Text style={styles.primaryText}>{loading ? "Signing in..." : "Sign In"}</Text>
          </TouchableOpacity>

          <TouchableOpacity onPress={() => router.replace("/auth/signup")} testID="goto-signup">
            <Text style={styles.linkText}>New here? Create an account</Text>
          </TouchableOpacity>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const makeStyles = (colors: ColorPalette) => StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  scroll: { padding: spacing.lg, gap: spacing.md },
  back: { width: 40, height: 40, borderRadius: radius.pill, backgroundColor: colors.surface, alignItems: "center", justifyContent: "center" },
  logoRow: { alignItems: "center", marginTop: spacing.md },
  logoBox: { width: 80, height: 80, borderRadius: radius.lg, backgroundColor: colors.logoBackdrop, borderWidth: 2, borderColor: colors.primary, overflow: "hidden" },
  logoImg: { width: "100%", height: "100%" },
  title: { color: colors.textPrimary, fontSize: 32, fontWeight: "800", marginTop: spacing.md, textAlign: "center" },
  subtitle: { color: colors.textSecondary, fontSize: 15, textAlign: "center" },
  field: { gap: 6 },
  label: { color: colors.textSecondary, fontSize: 12, fontWeight: "600", letterSpacing: 0.5, textTransform: "uppercase" },
  input: { backgroundColor: colors.surface, color: colors.textPrimary, padding: 14, borderRadius: radius.md, fontSize: 16, borderWidth: 1, borderColor: colors.border },
  primary: { backgroundColor: colors.primary, padding: 16, borderRadius: radius.pill, alignItems: "center", marginTop: spacing.sm },
  primaryText: { color: "#FFFFFF", fontSize: 16, fontWeight: "700" },
  linkText: { color: colors.primary, textAlign: "center", marginTop: spacing.md, fontWeight: "600" },
  err: { color: colors.danger, fontSize: 13 },
});
