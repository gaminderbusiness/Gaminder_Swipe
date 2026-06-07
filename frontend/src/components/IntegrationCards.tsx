import React, { useState } from "react";
import { View, Text, StyleSheet, TouchableOpacity, TextInput, ActivityIndicator, ScrollView, Modal } from "react-native";
import * as WebBrowser from "expo-web-browser";
import * as Linking from "expo-linking";
import { Gamepad2, Sword, Plus, Trophy, X, ExternalLink } from "lucide-react-native";
import { colors, radius, spacing } from "@/src/lib/theme";
import { api } from "@/src/lib/api";

const RIOT_PLATFORMS = ["NA1", "EUW1", "EUN1", "KR", "JP1", "BR1", "LA1", "LA2", "OC1", "TR1", "RU"];

export function ConnectSteamCard({ user, onRefresh }: { user: any; onRefresh: () => void }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const link = async () => {
    setBusy(true);
    setErr(null);
    try {
      const redirectUri = Linking.createURL("steam-linked");
      const { auth_url } = await api.steamAuthUrl(redirectUri);
      const result = await WebBrowser.openAuthSessionAsync(auth_url, redirectUri);
      if (result.type === "success") {
        await onRefresh();
      }
    } catch (e: any) {
      setErr(e.message || "Failed to start Steam linking");
    } finally {
      setBusy(false);
    }
  };

  const unlink = async () => {
    setBusy(true);
    try {
      await api.steamUnlink();
      await onRefresh();
    } catch (e: any) {
      setErr(e.message || "Failed to unlink");
    } finally {
      setBusy(false);
    }
  };

  const linked = !!user?.steam_id;

  return (
    <View style={styles.card} testID="steam-connect-card">
      <View style={styles.header}>
        <View style={[styles.iconWrap, { backgroundColor: colors.neonBlueSoft, borderColor: "rgba(0,229,255,0.4)" }]}>
          <Gamepad2 size={20} color={colors.neonBlue} />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={styles.title}>Steam</Text>
          <Text style={styles.subtitle}>
            {linked ? user.steam_persona_name || "Linked" : "Connect to import your top games"}
          </Text>
        </View>
        {linked ? (
          <TouchableOpacity testID="steam-unlink-btn" onPress={unlink} style={styles.unlinkBtn} disabled={busy}>
            <Text style={styles.unlinkText}>Unlink</Text>
          </TouchableOpacity>
        ) : (
          <TouchableOpacity testID="steam-connect-btn" onPress={link} style={styles.connectBtn} disabled={busy}>
            {busy ? <ActivityIndicator size="small" color="#fff" /> : <Text style={styles.connectText}>Connect</Text>}
          </TouchableOpacity>
        )}
      </View>
      {linked && user.steam_profile_url ? (
        <View style={styles.linkRow}>
          <ExternalLink size={12} color={colors.textMuted} />
          <Text style={styles.linkText} numberOfLines={1}>{user.steam_profile_url}</Text>
        </View>
      ) : null}
      {err ? <Text style={styles.err}>{err}</Text> : null}
    </View>
  );
}

export function ConnectRiotCard({ user, onRefresh }: { user: any; onRefresh: () => void }) {
  const [modal, setModal] = useState(false);
  const [riotId, setRiotId] = useState("");
  const [platform, setPlatform] = useState("NA1");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const link = async () => {
    if (!riotId.includes("#")) {
      setErr("Riot ID must be in format Name#TAG"); return;
    }
    setBusy(true);
    setErr(null);
    try {
      await api.riotLink(riotId.trim(), platform);
      setModal(false);
      setRiotId("");
      await onRefresh();
    } catch (e: any) {
      setErr(e.message || "Failed to link Riot");
    } finally {
      setBusy(false);
    }
  };

  const unlink = async () => {
    setBusy(true);
    try {
      await api.riotUnlink();
      await onRefresh();
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  const linked = !!user?.riot_id;
  const lol = user?.lol_profile;

  return (
    <View style={styles.card} testID="riot-connect-card">
      <View style={styles.header}>
        <View style={[styles.iconWrap, { backgroundColor: "rgba(220,38,38,0.15)", borderColor: "rgba(220,38,38,0.4)" }]}>
          <Sword size={20} color="#EF4444" />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={styles.title}>Riot / League of Legends</Text>
          <Text style={styles.subtitle}>
            {linked ? `${user.riot_id} • ${user.riot_platform}` : "Show your rank & top champions"}
          </Text>
        </View>
        {linked ? (
          <TouchableOpacity testID="riot-unlink-btn" onPress={unlink} style={styles.unlinkBtn} disabled={busy}>
            <Text style={styles.unlinkText}>Unlink</Text>
          </TouchableOpacity>
        ) : (
          <TouchableOpacity testID="riot-connect-btn" onPress={() => setModal(true)} style={styles.connectBtn}>
            <Text style={styles.connectText}>Connect</Text>
          </TouchableOpacity>
        )}
      </View>

      {linked && lol ? (
        <View style={styles.lolBody}>
          <View style={styles.lolStatsRow}>
            <View style={styles.lolStat}>
              <Text style={styles.lolStatLabel}>Level</Text>
              <Text style={styles.lolStatVal}>{lol.summoner_level}</Text>
            </View>
            {lol.solo_rank ? (
              <View style={styles.lolStat}>
                <Text style={styles.lolStatLabel}>Solo/Duo</Text>
                <Text style={styles.lolStatVal}>{lol.solo_rank.tier} {lol.solo_rank.division}</Text>
                <Text style={styles.lolStatSub}>{lol.solo_rank.league_points} LP • {lol.solo_rank.wins}W/{lol.solo_rank.losses}L</Text>
              </View>
            ) : null}
            {lol.flex_rank ? (
              <View style={styles.lolStat}>
                <Text style={styles.lolStatLabel}>Flex</Text>
                <Text style={styles.lolStatVal}>{lol.flex_rank.tier} {lol.flex_rank.division}</Text>
                <Text style={styles.lolStatSub}>{lol.flex_rank.league_points} LP</Text>
              </View>
            ) : null}
          </View>
          {lol.top_champions && lol.top_champions.length > 0 ? (
            <View style={styles.champsRow}>
              <Text style={styles.champsLabel}>TOP CHAMPIONS</Text>
              <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 6, marginTop: 6 }}>
                {lol.top_champions.map((c: any) => (
                  <View key={c.champion_id} style={styles.champTag}>
                    <Trophy size={11} color={colors.purple} />
                    <Text style={styles.champTagText}>{c.champion_name}</Text>
                    <Text style={styles.champTagPts}>Lv {c.level}</Text>
                  </View>
                ))}
              </View>
            </View>
          ) : null}
        </View>
      ) : null}

      <Modal visible={modal} animationType="slide" transparent onRequestClose={() => setModal(false)}>
        <View style={styles.modalBackdrop}>
          <View style={styles.modalCard}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Connect Riot Account</Text>
              <TouchableOpacity onPress={() => setModal(false)} testID="riot-modal-close">
                <X size={22} color={colors.textPrimary} />
              </TouchableOpacity>
            </View>

            <Text style={styles.modalLabel}>Riot ID</Text>
            <TextInput
              testID="riot-id-input"
              value={riotId}
              onChangeText={setRiotId}
              placeholder="Faker#KR1"
              placeholderTextColor={colors.textMuted}
              autoCapitalize="none"
              style={styles.input}
            />

            <Text style={styles.modalLabel}>Platform / Region</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8 }}>
              {RIOT_PLATFORMS.map(p => (
                <TouchableOpacity
                  key={p}
                  testID={`riot-platform-${p}`}
                  onPress={() => setPlatform(p)}
                  style={[styles.chip, platform === p && styles.chipActive]}
                >
                  <Text style={[styles.chipText, platform === p && styles.chipTextActive]}>{p}</Text>
                </TouchableOpacity>
              ))}
            </ScrollView>

            {err ? <Text style={styles.err}>{err}</Text> : null}

            <TouchableOpacity testID="riot-link-submit" style={[styles.primary, busy && { opacity: 0.5 }]} onPress={link} disabled={busy}>
              {busy ? <ActivityIndicator color="#fff" /> : <Text style={styles.primaryText}>Link Account</Text>}
            </TouchableOpacity>
            <Text style={styles.helpText}>Dev API keys are rate-limited and expire daily. If it fails, the key may have expired.</Text>
          </View>
        </View>
      </Modal>

      {err && !modal ? <Text style={styles.err}>{err}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: colors.surface, borderRadius: radius.lg, padding: spacing.md, borderWidth: 1, borderColor: colors.border, gap: 8 },
  header: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  iconWrap: { width: 40, height: 40, borderRadius: radius.md, borderWidth: 1, alignItems: "center", justifyContent: "center" },
  title: { color: colors.textPrimary, fontSize: 16, fontWeight: "700" },
  subtitle: { color: colors.textSecondary, fontSize: 12, marginTop: 2 },
  connectBtn: { backgroundColor: colors.purple, paddingHorizontal: 16, paddingVertical: 8, borderRadius: radius.pill, minWidth: 90, alignItems: "center" },
  connectText: { color: "#fff", fontSize: 13, fontWeight: "700" },
  unlinkBtn: { paddingHorizontal: 12, paddingVertical: 8, borderRadius: radius.pill, borderWidth: 1, borderColor: colors.borderStrong },
  unlinkText: { color: colors.textSecondary, fontSize: 12, fontWeight: "600" },
  linkRow: { flexDirection: "row", alignItems: "center", gap: 4 },
  linkText: { color: colors.textMuted, fontSize: 11, flex: 1 },
  err: { color: colors.danger, fontSize: 12, marginTop: 4 },
  lolBody: { marginTop: 4 },
  lolStatsRow: { flexDirection: "row", gap: 8, marginTop: 8 },
  lolStat: { flex: 1, backgroundColor: colors.surfaceElev, borderWidth: 1, borderColor: colors.border, padding: 10, borderRadius: radius.md },
  lolStatLabel: { color: colors.textMuted, fontSize: 10, fontWeight: "800", letterSpacing: 0.5, textTransform: "uppercase" },
  lolStatVal: { color: colors.textPrimary, fontSize: 14, fontWeight: "700", marginTop: 2 },
  lolStatSub: { color: colors.textSecondary, fontSize: 10, marginTop: 2 },
  champsRow: { marginTop: spacing.sm },
  champsLabel: { color: colors.purple, fontSize: 10, fontWeight: "800", letterSpacing: 1 },
  champTag: { flexDirection: "row", alignItems: "center", gap: 4, backgroundColor: colors.purpleSoft, borderWidth: 1, borderColor: "rgba(139,92,246,0.5)", paddingHorizontal: 8, paddingVertical: 4, borderRadius: radius.sm },
  champTagText: { color: colors.textPrimary, fontSize: 11, fontWeight: "700" },
  champTagPts: { color: colors.textMuted, fontSize: 10 },
  modalBackdrop: { flex: 1, backgroundColor: "rgba(0,0,0,0.7)", justifyContent: "flex-end" },
  modalCard: { backgroundColor: colors.surface, padding: spacing.lg, borderTopLeftRadius: 24, borderTopRightRadius: 24, gap: spacing.sm },
  modalHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  modalTitle: { color: colors.textPrimary, fontSize: 20, fontWeight: "800" },
  modalLabel: { color: colors.textSecondary, fontSize: 12, fontWeight: "700", letterSpacing: 0.5, textTransform: "uppercase", marginTop: 8 },
  input: { backgroundColor: colors.surfaceElev, color: colors.textPrimary, padding: 14, borderRadius: radius.md, fontSize: 15, borderWidth: 1, borderColor: colors.border },
  chip: { backgroundColor: colors.surfaceElev, paddingHorizontal: 14, paddingVertical: 8, borderRadius: radius.pill, borderWidth: 1, borderColor: colors.border, flexShrink: 0 },
  chipActive: { backgroundColor: colors.purpleSoft, borderColor: colors.purple },
  chipText: { color: colors.textSecondary, fontSize: 13, fontWeight: "600" },
  chipTextActive: { color: colors.textPrimary },
  primary: { backgroundColor: colors.purple, padding: 14, borderRadius: radius.pill, alignItems: "center", marginTop: spacing.md },
  primaryText: { color: "#fff", fontWeight: "700", fontSize: 15 },
  helpText: { color: colors.textMuted, fontSize: 11, textAlign: "center", marginTop: 4, paddingBottom: spacing.md },
});
