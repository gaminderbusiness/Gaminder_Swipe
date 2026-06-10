import React, { useEffect, useRef, useState } from "react";
import { View, Text, StyleSheet, Dimensions } from "react-native";
import { useRouter, useLocalSearchParams } from "expo-router";
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withRepeat,
  withTiming,
  withSequence,
  withDelay,
  Easing,
  cancelAnimation,
} from "react-native-reanimated";
import { Gamepad2 } from "lucide-react-native";
import { useTheme, spacing, type ColorPalette } from "@/src/lib/theme";
import { api } from "@/src/lib/api";

const { width: SCREEN_W, height: SCREEN_H } = Dimensions.get("window");

const PHRASES = (game?: string | null) => [
  "Searching for active players...",
  game ? `Finding gamers playing ${game}...` : "Finding active gamers...",
  "Building your match list...",
  "Looking for compatible teammates...",
];

function Ring({ delay, color, size }: { delay: number; color: string; size: number }) {
  const scale = useSharedValue(0.4);
  const opacity = useSharedValue(0.6);
  useEffect(() => {
    scale.value = withDelay(delay, withRepeat(withTiming(1.4, { duration: 2200, easing: Easing.out(Easing.ease) }), -1, false));
    opacity.value = withDelay(delay, withRepeat(withSequence(withTiming(0.5, { duration: 300 }), withTiming(0, { duration: 1900 })), -1, false));
    return () => { cancelAnimation(scale); cancelAnimation(opacity); };
  }, [delay, scale, opacity]);
  const style = useAnimatedStyle(() => ({ transform: [{ scale: scale.value }], opacity: opacity.value }));
  return <Animated.View style={[styles.ring, { width: size, height: size, borderRadius: size / 2, borderColor: color }, style]} pointerEvents="none" />;
}

function Particle({ i, color }: { i: number; color: string }) {
  const ty = useSharedValue(0);
  const op = useSharedValue(0);
  const left = (i * 53) % SCREEN_W;
  const baseTop = (i * 97) % SCREEN_H;
  useEffect(() => {
    const dur = 2600 + (i % 5) * 400;
    ty.value = withDelay(i * 180, withRepeat(withTiming(-60, { duration: dur, easing: Easing.inOut(Easing.ease) }), -1, true));
    op.value = withDelay(i * 180, withRepeat(withSequence(withTiming(0.7, { duration: dur / 2 }), withTiming(0.1, { duration: dur / 2 })), -1, true));
    return () => { cancelAnimation(ty); cancelAnimation(op); };
  }, [i, ty, op]);
  const style = useAnimatedStyle(() => ({ transform: [{ translateY: ty.value }], opacity: op.value }));
  return <Animated.View style={[styles.particle, { left, top: baseTop, backgroundColor: color }, style]} pointerEvents="none" />;
}

export default function Matchmaking() {
  const router = useRouter();
  const params = useLocalSearchParams<{ game?: string; target?: string }>();
  const { colors } = useTheme();
  const dynStyles = makeStyles(colors);

  const [game, setGame] = useState<string | null>(params.game || null);
  const [found, setFound] = useState(0);
  const [phraseIdx, setPhraseIdx] = useState(0);
  const targetRef = useRef<number>(params.target ? parseInt(params.target, 10) : 0);
  const navigatedRef = useRef(false);

  const corePulse = useSharedValue(1);

  useEffect(() => {
    corePulse.value = withRepeat(withSequence(
      withTiming(1.12, { duration: 700, easing: Easing.inOut(Easing.ease) }),
      withTiming(1, { duration: 700, easing: Easing.inOut(Easing.ease) }),
    ), -1, false);
    return () => cancelAnimation(corePulse);
  }, [corePulse]);

  // Fetch live data (focus game + pool) if not provided
  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const d = await api.homeActivity();
        if (!mounted) return;
        if (d.focus_game) setGame(d.focus_game);
        const t = Math.max(d.active_same_game_count || 0, Math.min(d.matchmaking_pool || 0, 48));
        targetRef.current = Math.max(t, 8);
      } catch {
        targetRef.current = Math.max(targetRef.current, 12);
      }
    })();
    return () => { mounted = false; };
  }, []);

  // Random 5-10s session; count-up + phrase cycle; then go to swipe
  useEffect(() => {
    const duration = 5000 + Math.floor(Math.random() * 5000);
    const start = Date.now();

    const countTimer = setInterval(() => {
      const elapsed = Date.now() - start;
      const ratio = Math.min(1, elapsed / (duration * 0.85));
      const target = targetRef.current || 12;
      setFound(Math.round(target * ratio));
    }, 120);

    const phraseTimer = setInterval(() => {
      setPhraseIdx((p) => (p + 1) % 4);
    }, 1600);

    const done = setTimeout(() => {
      if (navigatedRef.current) return;
      navigatedRef.current = true;
      setFound(targetRef.current || 12);
      router.replace("/(tabs)/swipe");
    }, duration);

    return () => { clearInterval(countTimer); clearInterval(phraseTimer); clearTimeout(done); };
  }, [router]);

  const coreStyle = useAnimatedStyle(() => ({ transform: [{ scale: corePulse.value }] }));
  const phrases = PHRASES(game);

  return (
    <View style={dynStyles.root} testID="matchmaking-screen">
      {Array.from({ length: 7 }).map((_, i) => (
        <Particle key={i} i={i} color={i % 2 === 0 ? colors.primary : colors.accent} />
      ))}

      <View style={styles.center}>
        <View style={styles.orbWrap}>
          <Ring delay={0} color={colors.primary} size={220} />
          <Ring delay={700} color={colors.accent} size={220} />
          <Ring delay={1400} color={colors.primary} size={220} />
          <Animated.View style={[dynStyles.core, coreStyle]}>
            <Gamepad2 size={44} color="#FFFFFF" />
          </Animated.View>
        </View>

        <Text style={dynStyles.title} testID="matchmaking-title">Matching You With Active Players</Text>
        <Text style={dynStyles.phrase} testID="matchmaking-phrase">{phrases[phraseIdx]}</Text>

        <View style={dynStyles.foundPill}>
          <Text style={dynStyles.foundLabel}>PLAYERS FOUND</Text>
          <Text style={dynStyles.foundCount} testID="players-found">{found}</Text>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: "center", justifyContent: "center", paddingHorizontal: spacing.lg },
  orbWrap: { width: 220, height: 220, alignItems: "center", justifyContent: "center", marginBottom: spacing.xl },
  ring: { position: "absolute", borderWidth: 2 },
  particle: { position: "absolute", width: 6, height: 6, borderRadius: 3 },
});

const makeStyles = (colors: ColorPalette) => StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg, overflow: "hidden" },
  core: { width: 96, height: 96, borderRadius: 48, backgroundColor: colors.primary, alignItems: "center", justifyContent: "center", shadowColor: colors.primary, shadowOpacity: 0.8, shadowRadius: 24, shadowOffset: { width: 0, height: 0 }, elevation: 12 },
  title: { color: colors.textPrimary, fontSize: 22, fontWeight: "800", textAlign: "center", letterSpacing: -0.3 },
  phrase: { color: colors.textSecondary, fontSize: 15, marginTop: 8, textAlign: "center", minHeight: 22 },
  foundPill: { marginTop: spacing.xl, alignItems: "center", paddingHorizontal: 28, paddingVertical: 14, borderRadius: 18, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.borderStrong },
  foundLabel: { color: colors.textMuted, fontSize: 11, fontWeight: "800", letterSpacing: 2 },
  foundCount: { color: colors.primary, fontSize: 40, fontWeight: "900", marginTop: 2 },
});
