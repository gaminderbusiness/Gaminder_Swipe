import React, { useState } from "react";
import { View, Text, StyleSheet, TouchableOpacity, ActivityIndicator, Modal, Image } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import * as WebBrowser from "expo-web-browser";
import * as Linking from "expo-linking";
import { Gamepad2, HelpCircle, X, ShieldCheck, LogOut } from "lucide-react-native";
import { LinearGradient } from "expo-linear-gradient";
import { useTheme, radius, spacing, type ColorPalette } from "@/src/lib/theme";
import { useAuth } from "@/src/lib/auth";
import { api } from "@/src/lib/api";

const LOGO = require("@/assets/images/gaminder-logo-transparent.png");

export default function ConnectSteam() {
  const { refresh, signOut } = useAuth();
  const { colors } = useTheme();
  const styles = makeStyles(colors);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [help, setHelp] = useState(false);

  const connect = async () => {
    setBusy(true);
    setErr(null);
    try {
      const redirectUri = Linking.createURL("steam-linked");
      const { auth_url } = await api.steamAuthUrl(redirectUri);
      const result = await WebBrowser.openAuthSessionAsync(auth_url, redirectUri);
      if (result.type === "success") {
        await refresh(); // onboarding_complete becomes true -> RootNav routes to app
      } else {
        setErr("Steam connection was cancelled. Connecting Steam is required to continue.");
      }
    } catch (e: any) {
      setErr(e.message || "Failed to start Steam connection");
    } finally {
      setBusy(false);
    }
  };

  return (
    <SafeAreaView style={styles.root} edges={["top", "bottom"]} testID="connect-steam-screen">
      <View style={styles.body}>
        <View style={styles.logoBox}>
          <Image source={LOGO} style={styles.logo} resizeMode="contain" />
        </View>

        <Text style={styles.title}>Connect your Steam</Text>
        <Text style={styles.subtitle}>One last step to find your squad.</Text>

        <View style={styles.noticeCard}>
          <View style={styles.noticeHeader}>
            <ShieldCheck size={18} color={colors.primary} />
            <Text style={styles.noticeTitle}>Make your profile public</Text>
            <TouchableOpacity testID="steam-help-btn" onPress={() => setHelp(true)} hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}>
              <HelpCircle size={20} color={colors.textSecondary} />
            </TouchableOpacity>
          </View>
          <Text style={styles.noticeText}>
            Your Steam profile and Game Details must be Public for Gaminder to retrieve your gaming data and provide better matches.
          </Text>
        </View>

        <View style={{ flex: 1 }} />

        {err ? <Text style={styles.err} testID="steam-connect-error">{err}</Text> : null}

        <TouchableOpacity testID="onboarding-steam-connect-btn" style={[styles.connectBtn, busy && { opacity: 0.6 }]} onPress={connect} disabled={busy}>
          <LinearGradient colors={[colors.primary, colors.accent]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={styles.connectGrad}>
            {busy ? (
              <ActivityIndicator color="#FFFFFF" />
            ) : (
              <>
                <Gamepad2 size={20} color="#FFFFFF" />
                <Text style={styles.connectText}>Connect Steam</Text>
              </>
            )}
          </LinearGradient>
        </TouchableOpacity>

        <TouchableOpacity testID="onboarding-signout-btn" style={styles.signOut} onPress={signOut}>
          <LogOut size={16} color={colors.textMuted} />
          <Text style={styles.signOutText}>Cancel & sign out</Text>
        </TouchableOpacity>
      </View>

      <Modal visible={help} transparent animationType="fade" onRequestClose={() => setHelp(false)}>
        <View style={styles.modalBackdrop}>
          <View style={styles.modalCard} testID="steam-help-modal">
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>How to make Steam public</Text>
              <TouchableOpacity testID="steam-help-close" onPress={() => setHelp(false)}>
                <X size={22} color={colors.textPrimary} />
              </TouchableOpacity>
            </View>
            <View style={styles.gifPlaceholder} testID="steam-tutorial-gif-placeholder">
              <Gamepad2 size={40} color={colors.textMuted} />
              <Text style={styles.gifText}>Tutorial coming soon</Text>
              <Text style={styles.gifSub}>A step-by-step guide will appear here.</Text>
            </View>
            <Text style={styles.modalBody}>
              In Steam, open Profile → Edit Profile → Privacy Settings, then set “My profile” and “Game details” to Public.
            </Text>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const makeStyles = (colors: ColorPalette) => StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  body: { flex: 1, padding: spacing.lg, alignItems: "center" },
  logoBox: { width: 88, height: 88, borderRadius: radius.lg, backgroundColor: colors.logoBackdrop, borderWidth: 1, borderColor: colors.borderStrong, overflow: "hidden", marginTop: spacing.xl },
  logo: { width: "100%", height: "100%" },
  title: { color: colors.textPrimary, fontSize: 28, fontWeight: "800", marginTop: spacing.lg },
  subtitle: { color: colors.textSecondary, fontSize: 15, marginTop: 4 },
  noticeCard: { width: "100%", backgroundColor: colors.surface, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.borderStrong, padding: spacing.md, marginTop: spacing.xl, gap: 8 },
  noticeHeader: { flexDirection: "row", alignItems: "center", gap: 8 },
  noticeTitle: { color: colors.textPrimary, fontSize: 15, fontWeight: "700", flex: 1 },
  noticeText: { color: colors.textSecondary, fontSize: 14, lineHeight: 20 },
  err: { color: colors.danger, fontSize: 13, marginBottom: spacing.sm, textAlign: "center" },
  connectBtn: { width: "100%", borderRadius: radius.pill, overflow: "hidden" },
  connectGrad: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8, paddingVertical: 16 },
  connectText: { color: "#FFFFFF", fontSize: 16, fontWeight: "800" },
  signOut: { flexDirection: "row", alignItems: "center", gap: 6, paddingVertical: spacing.md },
  signOutText: { color: colors.textMuted, fontSize: 13, fontWeight: "600" },
  modalBackdrop: { flex: 1, backgroundColor: colors.overlayBackdrop, justifyContent: "center", padding: spacing.lg },
  modalCard: { backgroundColor: colors.surface, borderRadius: radius.lg, padding: spacing.lg, gap: spacing.md, borderWidth: 1, borderColor: colors.border },
  modalHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  modalTitle: { color: colors.textPrimary, fontSize: 18, fontWeight: "800" },
  gifPlaceholder: { height: 160, borderRadius: radius.md, borderWidth: 1, borderColor: colors.borderStrong, borderStyle: "dashed", backgroundColor: colors.surfaceElev, alignItems: "center", justifyContent: "center", gap: 6 },
  gifText: { color: colors.textSecondary, fontSize: 14, fontWeight: "700" },
  gifSub: { color: colors.textMuted, fontSize: 12 },
  modalBody: { color: colors.textSecondary, fontSize: 13, lineHeight: 19 },
});
