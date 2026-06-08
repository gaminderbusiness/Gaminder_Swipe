import { View, Text, StyleSheet, ActivityIndicator } from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useEffect } from "react";
import { CheckCircle2, XCircle } from "lucide-react-native";
import { useTheme, radius, spacing, type ColorPalette } from "@/src/lib/theme";

export default function SteamLinked() {
  const params = useLocalSearchParams<{ status?: string; profile_private?: string }>();
  const router = useRouter();
  const { colors } = useTheme();
  const styles = makeStyles(colors);

  useEffect(() => {
    const t = setTimeout(() => router.replace("/(tabs)/profile"), 2200);
    return () => clearTimeout(t);
  }, [router]);

  if (!params.status) {
    return (
      <View style={styles.root}>
        <ActivityIndicator color={colors.primary} />
        <Text style={styles.text}>Linking Steam...</Text>
      </View>
    );
  }

  const success = params.status === "success";
  const isPrivate = params.profile_private === "1";

  return (
    <View style={styles.root} testID="steam-linked-screen">
      {success ? (
        <CheckCircle2 size={64} color={colors.primary} />
      ) : (
        <XCircle size={64} color={colors.danger} />
      )}
      <Text style={styles.title}>{success ? "Steam Linked!" : "Linking Failed"}</Text>
      {success && isPrivate ? (
        <Text style={styles.text}>
          Your Steam game library appears to be private. Set Game Details to Public in Steam privacy settings to display your top games.
        </Text>
      ) : success ? (
        <Text style={styles.text}>Your top games are now showing on your profile.</Text>
      ) : (
        <Text style={styles.text}>Please try again from your profile.</Text>
      )}
    </View>
  );
}

const makeStyles = (colors: ColorPalette) => StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg, alignItems: "center", justifyContent: "center", padding: spacing.xl, gap: spacing.md },
  title: { color: colors.textPrimary, fontSize: 24, fontWeight: "800" },
  text: { color: colors.textSecondary, fontSize: 14, textAlign: "center", lineHeight: 20 },
});
