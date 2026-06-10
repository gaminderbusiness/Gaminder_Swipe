import { useState } from "react";
import { View, Text, StyleSheet, TextInput, TouchableOpacity, ScrollView, KeyboardAvoidingView, Platform } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { ArrowLeft, Plus, X } from "lucide-react-native";
import { useTheme, radius, spacing, type ColorPalette } from "@/src/lib/theme";
import { useAuth } from "@/src/lib/auth";

const COUNTRIES = ["USA", "UK", "Canada", "Germany", "France", "Japan", "Brazil", "Australia", "India", "Sweden", "Mexico", "Netherlands", "South Korea", "Russia", "China", "Turkey", "Other"];
const LANG_OPTIONS = ["English", "Spanish", "French", "German", "Portuguese", "Japanese", "Korean", "Mandarin", "Russian", "Italian", "Dutch", "Swedish", "Turkish"];
const SUGGESTED_GAMES = ["Valorant", "CS2", "League of Legends", "Dota 2", "Apex Legends", "Fortnite", "Overwatch 2", "Rocket League", "Rust", "Minecraft", "Destiny 2", "Elden Ring", "Final Fantasy XIV", "World of Warcraft", "Genshin Impact"];
const PLAYTIME_SLOTS = ["00:00-03:00", "03:00-06:00", "06:00-09:00", "09:00-12:00", "12:00-15:00", "15:00-18:00", "18:00-21:00", "21:00-00:00"];

export default function Signup() {
  const router = useRouter();
  const { signUp } = useAuth();
  const { colors } = useTheme();
  const styles = makeStyles(colors);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [username, setUsername] = useState("");
  const [age, setAge] = useState("");
  const [country, setCountry] = useState("USA");
  const [city, setCity] = useState("");
  const [languages, setLanguages] = useState<string[]>(["English"]);
  const [bio, setBio] = useState("");
  const [recentGames, setRecentGames] = useState<string[]>([]);
  const [slots, setSlots] = useState<string[]>([]);
  const [games, setGames] = useState<{ name: string; hours: number }[]>([]);
  const [gameInput, setGameInput] = useState("");
  const [hoursInput, setHoursInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const toggleLang = (l: string) => {
    setLanguages((cur) => cur.includes(l) ? cur.filter(x => x !== l) : [...cur, l]);
  };

  const toggleRecent = (g: string) => {
    setRecentGames((cur) => cur.includes(g) ? cur.filter(x => x !== g) : (cur.length >= 3 ? cur : [...cur, g]));
  };

  const toggleSlot = (s: string) => {
    setSlots((cur) => cur.includes(s) ? cur.filter(x => x !== s) : (cur.length >= 2 ? cur : [...cur, s]));
  };

  const addGame = (name?: string) => {
    const n = (name ?? gameInput).trim();
    const h = parseInt(hoursInput || "0", 10);
    if (!n) return;
    if (games.find(g => g.name.toLowerCase() === n.toLowerCase())) return;
    setGames([...games, { name: n, hours: isNaN(h) ? 0 : h }]);
    setGameInput("");
    setHoursInput("");
  };

  const removeGame = (name: string) => setGames(games.filter(g => g.name !== name));

  const submit = async () => {
    setErr(null);
    if (!email || !password || !username || !age) {
      setErr("Please fill all required fields"); return;
    }
    const ageN = parseInt(age, 10);
    if (isNaN(ageN) || ageN < 13 || ageN > 99) {
      setErr("Enter a valid age (13-99)"); return;
    }
    if (recentGames.length === 0) {
      setErr("Pick at least 1 recently played game"); return;
    }
    if (slots.length === 0) {
      setErr("Pick at least 1 gaming time slot"); return;
    }
    setLoading(true);
    try {
      const photoSeed = encodeURIComponent(username);
      await signUp({
        email: email.trim(),
        password,
        username: username.trim(),
        age: ageN,
        country,
        city: city.trim(),
        languages,
        bio,
        profile_photo: `https://api.dicebear.com/7.x/adventurer/png?seed=${photoSeed}&backgroundColor=ff6a1a`,
        top_games: games,
        recently_played_games: recentGames,
        playtime_slots: slots,
      });
    } catch (e: any) {
      setErr(e.message || "Signup failed");
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
          <Text style={styles.title}>Create profile</Text>
          <Text style={styles.subtitle}>Tell us about your gaming style.</Text>

          <View style={styles.field}>
            <Text style={styles.label}>Email *</Text>
            <TextInput testID="signup-email" value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" placeholder="you@gaming.gg" placeholderTextColor={colors.textMuted} style={styles.input} />
          </View>
          <View style={styles.field}>
            <Text style={styles.label}>Password *</Text>
            <TextInput testID="signup-password" value={password} onChangeText={setPassword} secureTextEntry placeholder="At least 6 chars" placeholderTextColor={colors.textMuted} style={styles.input} />
          </View>
          <View style={styles.field}>
            <Text style={styles.label}>Username *</Text>
            <TextInput testID="signup-username" value={username} onChangeText={setUsername} autoCapitalize="none" placeholder="GamerTag" placeholderTextColor={colors.textMuted} style={styles.input} />
          </View>
          <View style={[styles.field, { flexDirection: "row", gap: spacing.md }]}>
            <View style={{ flex: 1 }}>
              <Text style={styles.label}>Age *</Text>
              <TextInput testID="signup-age" value={age} onChangeText={setAge} keyboardType="number-pad" placeholder="22" placeholderTextColor={colors.textMuted} style={styles.input} />
            </View>
          </View>

          <View style={styles.field}>
            <Text style={styles.label}>Country</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8, paddingVertical: 4 }}>
              {COUNTRIES.map(c => (
                <TouchableOpacity key={c} testID={`country-${c}`} onPress={() => setCountry(c)} style={[styles.chip, country === c && styles.chipActive]}>
                  <Text style={[styles.chipText, country === c && styles.chipTextActive]}>{c}</Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
          </View>

          <View style={styles.field}>
            <Text style={styles.label}>City</Text>
            <TextInput testID="signup-city" value={city} onChangeText={setCity} placeholder="Los Angeles" placeholderTextColor={colors.textMuted} style={styles.input} />
          </View>

          <View style={styles.field}>
            <Text style={styles.label}>Recently Played Games * (max 3)</Text>
            <Text style={styles.helper}>What games have you been playing recently? These heavily affect your matches.</Text>
            <View style={styles.wrap}>
              {SUGGESTED_GAMES.map(g => {
                const sel = recentGames.includes(g);
                const disabled = !sel && recentGames.length >= 3;
                return (
                  <TouchableOpacity key={g} testID={`recent-${g}`} onPress={() => toggleRecent(g)} disabled={disabled} style={[styles.chip, sel && styles.chipActive, disabled && { opacity: 0.4 }]}>
                    <Text style={[styles.chipText, sel && styles.chipTextActive]}>{g}</Text>
                  </TouchableOpacity>
                );
              })}
            </View>
            <Text style={styles.counter}>{recentGames.length}/3 selected</Text>
          </View>

          <View style={styles.field}>
            <Text style={styles.label}>Gaming Schedule * (max 2)</Text>
            <Text style={styles.helper}>When do you usually play?</Text>
            <View style={styles.wrap}>
              {PLAYTIME_SLOTS.map(s => {
                const sel = slots.includes(s);
                const disabled = !sel && slots.length >= 2;
                return (
                  <TouchableOpacity key={s} testID={`slot-${s}`} onPress={() => toggleSlot(s)} disabled={disabled} style={[styles.chip, sel && styles.chipActive, disabled && { opacity: 0.4 }]}>
                    <Text style={[styles.chipText, sel && styles.chipTextActive]}>{s}</Text>
                  </TouchableOpacity>
                );
              })}
            </View>
            <Text style={styles.counter}>{slots.length}/2 selected</Text>
          </View>

          <View style={styles.field}>
            <Text style={styles.label}>Languages</Text>
            <View style={styles.wrap}>
              {LANG_OPTIONS.map(l => (
                <TouchableOpacity key={l} testID={`lang-${l}`} onPress={() => toggleLang(l)} style={[styles.chip, languages.includes(l) && styles.chipActive]}>
                  <Text style={[styles.chipText, languages.includes(l) && styles.chipTextActive]}>{l}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>

          <View style={styles.field}>
            <Text style={styles.label}>Bio</Text>
            <TextInput testID="signup-bio" value={bio} onChangeText={setBio} multiline placeholder="Looking for chill Valorant teammates..." placeholderTextColor={colors.textMuted} style={[styles.input, { minHeight: 80, textAlignVertical: "top" }]} />
          </View>

          <View style={styles.field}>
            <Text style={styles.label}>Top Games</Text>
            <View style={{ flexDirection: "row", gap: 8 }}>
              <TextInput testID="game-name-input" value={gameInput} onChangeText={setGameInput} placeholder="Game name" placeholderTextColor={colors.textMuted} style={[styles.input, { flex: 2 }]} />
              <TextInput testID="game-hours-input" value={hoursInput} onChangeText={setHoursInput} keyboardType="number-pad" placeholder="Hours" placeholderTextColor={colors.textMuted} style={[styles.input, { flex: 1 }]} />
              <TouchableOpacity testID="add-game-btn" onPress={() => addGame()} style={styles.addBtn}>
                <Plus size={20} color={colors.primary} />
              </TouchableOpacity>
            </View>
            <View style={[styles.wrap, { marginTop: 8 }]}>
              {SUGGESTED_GAMES.filter(g => !games.find(x => x.name === g)).slice(0, 8).map(g => (
                <TouchableOpacity key={g} testID={`suggest-${g}`} onPress={() => addGame(g)} style={styles.suggestChip}>
                  <Text style={styles.suggestChipText}>+ {g}</Text>
                </TouchableOpacity>
              ))}
            </View>
            <View style={{ marginTop: spacing.sm, gap: 6 }}>
              {games.map(g => (
                <View key={g.name} style={styles.gameRow} testID={`game-row-${g.name}`}>
                  <Text style={styles.gameName}>{g.name}</Text>
                  <Text style={styles.gameHours}>{g.hours}h</Text>
                  <TouchableOpacity onPress={() => removeGame(g.name)} testID={`remove-${g.name}`}>
                    <X size={18} color={colors.textMuted} />
                  </TouchableOpacity>
                </View>
              ))}
            </View>
          </View>

          {err ? <Text style={styles.err} testID="signup-error">{err}</Text> : null}

          <TouchableOpacity testID="signup-submit-button" style={[styles.primary, loading && { opacity: 0.6 }]} onPress={submit} disabled={loading}>
            <Text style={styles.primaryText}>{loading ? "Creating..." : "Create Account"}</Text>
          </TouchableOpacity>

          <TouchableOpacity onPress={() => router.replace("/auth/login")} testID="goto-login">
            <Text style={styles.linkText}>Already have an account? Sign in</Text>
          </TouchableOpacity>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const makeStyles = (colors: ColorPalette) => StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  scroll: { padding: spacing.lg, gap: spacing.md, paddingBottom: spacing.xxl },
  back: { width: 40, height: 40, borderRadius: radius.pill, backgroundColor: colors.surface, alignItems: "center", justifyContent: "center" },
  title: { color: colors.textPrimary, fontSize: 32, fontWeight: "800", marginTop: spacing.md },
  subtitle: { color: colors.textSecondary, fontSize: 15 },
  field: { gap: 6 },
  label: { color: colors.textSecondary, fontSize: 12, fontWeight: "600", letterSpacing: 0.5, textTransform: "uppercase" },
  helper: { color: colors.textMuted, fontSize: 12, lineHeight: 16 },
  counter: { color: colors.textMuted, fontSize: 11, fontWeight: "700", marginTop: 2 },
  input: { backgroundColor: colors.surface, color: colors.textPrimary, padding: 14, borderRadius: radius.md, fontSize: 16, borderWidth: 1, borderColor: colors.border },
  chip: { backgroundColor: colors.surface, paddingHorizontal: 14, paddingVertical: 8, borderRadius: radius.pill, borderWidth: 1, borderColor: colors.border, flexShrink: 0 },
  chipActive: { backgroundColor: colors.primarySoft, borderColor: colors.primary },
  chipText: { color: colors.textSecondary, fontSize: 13, fontWeight: "600" },
  chipTextActive: { color: colors.primary },
  wrap: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  addBtn: { width: 52, height: 52, borderRadius: radius.md, backgroundColor: colors.primarySoft, borderWidth: 1, borderColor: colors.borderStrong, alignItems: "center", justifyContent: "center" },
  suggestChip: { backgroundColor: "transparent", borderWidth: 1, borderColor: colors.borderStrong, borderStyle: "dashed", paddingHorizontal: 12, paddingVertical: 6, borderRadius: radius.pill },
  suggestChipText: { color: colors.textSecondary, fontSize: 12, fontWeight: "600" },
  gameRow: { flexDirection: "row", alignItems: "center", gap: spacing.md, backgroundColor: colors.surface, padding: 12, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border },
  gameName: { color: colors.textPrimary, fontSize: 14, fontWeight: "600", flex: 1 },
  gameHours: { color: colors.primary, fontSize: 13, fontWeight: "700" },
  primary: { backgroundColor: colors.primary, padding: 16, borderRadius: radius.pill, alignItems: "center", marginTop: spacing.sm },
  primaryText: { color: "#FFFFFF", fontSize: 16, fontWeight: "700" },
  linkText: { color: colors.primary, textAlign: "center", marginTop: spacing.md, fontWeight: "600" },
  err: { color: colors.danger, fontSize: 13 },
});
