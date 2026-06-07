import React, { useEffect, useState, useCallback } from "react";
import { View, Text, StyleSheet, TouchableOpacity, Image, Dimensions, ActivityIndicator } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { LinearGradient } from "expo-linear-gradient";
import { GestureDetector, Gesture } from "react-native-gesture-handler";
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
  withTiming,
  runOnJS,
  interpolate,
  Extrapolation,
} from "react-native-reanimated";
import { Sparkles, X, Heart, Star, Gamepad2, MapPin } from "lucide-react-native";
import { colors, radius, spacing, activityLabel, statusColor } from "@/src/lib/theme";
import { api } from "@/src/lib/api";
import MatchModal from "@/src/components/MatchModal";

const { width: SCREEN_W, height: SCREEN_H } = Dimensions.get("window");
const SWIPE_THRESHOLD = SCREEN_W * 0.28;
const CARD_WIDTH = SCREEN_W - spacing.lg * 2;
const CARD_HEIGHT = SCREEN_H * 0.62;

type Card = any;

export default function SwipeScreen() {
  const [cards, setCards] = useState<Card[]>([]);
  const [loading, setLoading] = useState(true);
  const [dailyLikes, setDailyLikes] = useState(0);
  const [superLikes, setSuperLikes] = useState(1);
  const [matchedUser, setMatchedUser] = useState<any>(null);
  const [matchId, setMatchId] = useState<string | null>(null);

  const translateX = useSharedValue(0);
  const translateY = useSharedValue(0);

  const loadFeed = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.swipeFeed();
      setCards(data.cards || []);
      setDailyLikes(data.daily_likes_used || 0);
      setSuperLikes(data.super_likes_remaining || 0);
    } catch (e) {
      // noop
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadFeed(); }, [loadFeed]);

  const current = cards[0];
  const next = cards[1];

  const advance = useCallback(() => {
    setCards((c) => c.slice(1));
    translateX.value = 0;
    translateY.value = 0;
  }, [translateX, translateY]);

  const doSwipe = useCallback(async (action: "like" | "pass" | "superlike", targetId: string) => {
    try {
      const res = await api.swipe(targetId, action);
      if (action === "like") setDailyLikes((n) => n + 1);
      if (action === "superlike") setSuperLikes((n) => Math.max(0, n - 1));
      if (res.matched && res.matched_user) {
        setMatchedUser(res.matched_user);
        setMatchId(res.match_id);
      }
    } catch (e: any) {
      // could show toast
    }
  }, []);

  const triggerAction = useCallback((action: "like" | "pass" | "superlike") => {
    if (!current) return;
    const targetId = current.id;
    if (action === "like") {
      translateX.value = withTiming(SCREEN_W * 1.5, { duration: 280 }, () => runOnJS(advance)());
    } else if (action === "pass") {
      translateX.value = withTiming(-SCREEN_W * 1.5, { duration: 280 }, () => runOnJS(advance)());
    } else {
      translateY.value = withTiming(-SCREEN_H, { duration: 320 }, () => runOnJS(advance)());
    }
    doSwipe(action, targetId);
  }, [current, translateX, translateY, doSwipe, advance]);

  const pan = Gesture.Pan()
    .onUpdate((e) => {
      translateX.value = e.translationX;
      translateY.value = e.translationY;
    })
    .onEnd((e) => {
      if (Math.abs(e.translationX) > SWIPE_THRESHOLD) {
        const dir = e.translationX > 0 ? 1 : -1;
        const action = dir > 0 ? "like" : "pass";
        translateX.value = withTiming(dir * SCREEN_W * 1.5, { duration: 240 }, () => runOnJS(advance)());
        if (current) runOnJS(doSwipe)(action, current.id);
      } else if (e.translationY < -SWIPE_THRESHOLD * 1.5 && superLikes > 0) {
        translateY.value = withTiming(-SCREEN_H, { duration: 300 }, () => runOnJS(advance)());
        if (current) runOnJS(doSwipe)("superlike", current.id);
      } else {
        translateX.value = withSpring(0);
        translateY.value = withSpring(0);
      }
    });

  const cardStyle = useAnimatedStyle(() => {
    const rotate = interpolate(translateX.value, [-SCREEN_W, 0, SCREEN_W], [-12, 0, 12], Extrapolation.CLAMP);
    return {
      transform: [
        { translateX: translateX.value },
        { translateY: translateY.value },
        { rotate: `${rotate}deg` },
      ],
    };
  });

  const likeOverlayStyle = useAnimatedStyle(() => ({
    opacity: interpolate(translateX.value, [0, SWIPE_THRESHOLD], [0, 1], Extrapolation.CLAMP),
  }));
  const passOverlayStyle = useAnimatedStyle(() => ({
    opacity: interpolate(translateX.value, [-SWIPE_THRESHOLD, 0], [1, 0], Extrapolation.CLAMP),
  }));
  const superOverlayStyle = useAnimatedStyle(() => ({
    opacity: interpolate(translateY.value, [-SWIPE_THRESHOLD * 1.5, 0], [1, 0], Extrapolation.CLAMP),
  }));

  return (
    <SafeAreaView style={styles.root} edges={["top"]}>
      <View style={styles.header}>
        <View>
          <Text style={styles.h1}>Discover</Text>
          <Text style={styles.h1sub}>Find your gaming squad</Text>
        </View>
        <View style={styles.counters}>
          <View style={styles.counterPill} testID="like-counter">
            <Heart size={14} color={colors.neonBlue} />
            <Text style={styles.counterText}>{Math.max(0, 20 - dailyLikes)}/20</Text>
          </View>
          <View style={styles.counterPillPurple} testID="superlike-counter">
            <Star size={14} color={colors.purple} fill={colors.purple} />
            <Text style={[styles.counterText, { color: colors.purple }]}>{superLikes}</Text>
          </View>
        </View>
      </View>

      <View style={styles.deck}>
        {loading ? (
          <View style={styles.empty}><ActivityIndicator color={colors.neonBlue} /></View>
        ) : !current ? (
          <View style={styles.empty} testID="empty-deck">
            <Gamepad2 size={56} color={colors.textMuted} />
            <Text style={styles.emptyTitle}>No more players</Text>
            <Text style={styles.emptyText}>Check back soon — new gamers join all the time.</Text>
            <TouchableOpacity testID="refresh-feed" onPress={loadFeed} style={styles.refreshBtn}>
              <Text style={styles.refreshBtnText}>Refresh</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <>
            {next ? <CardView card={next} stacked /> : null}
            <GestureDetector gesture={pan}>
              <Animated.View style={[styles.card, cardStyle]} testID="swipe-card">
                <CardInner card={current} />
                <Animated.View style={[styles.overlay, styles.likeOverlay, likeOverlayStyle]}>
                  <Text style={styles.overlayText}>LIKE</Text>
                </Animated.View>
                <Animated.View style={[styles.overlay, styles.passOverlay, passOverlayStyle]}>
                  <Text style={[styles.overlayText, { color: colors.pass }]}>PASS</Text>
                </Animated.View>
                <Animated.View style={[styles.overlayCenter, superOverlayStyle]}>
                  <Text style={[styles.overlayText, { color: colors.purple, fontSize: 48 }]}>SUPER</Text>
                </Animated.View>
              </Animated.View>
            </GestureDetector>
          </>
        )}
      </View>

      {current ? (
        <View style={styles.actions}>
          <TouchableOpacity testID="pass-btn" style={[styles.actionBtn, styles.passBtn]} onPress={() => triggerAction("pass")}>
            <X size={28} color={colors.pass} />
          </TouchableOpacity>
          <TouchableOpacity testID="superlike-btn" style={[styles.actionBtn, styles.superBtn]} onPress={() => superLikes > 0 && triggerAction("superlike")}>
            <Star size={26} color={colors.purple} fill={superLikes > 0 ? colors.purple : "transparent"} />
          </TouchableOpacity>
          <TouchableOpacity testID="like-btn" style={[styles.actionBtn, styles.likeBtn]} onPress={() => triggerAction("like")}>
            <Heart size={28} color={colors.neonBlue} />
          </TouchableOpacity>
        </View>
      ) : null}

      <MatchModal
        visible={!!matchedUser}
        matchUser={matchedUser}
        matchId={matchId}
        onClose={() => { setMatchedUser(null); setMatchId(null); }}
      />
    </SafeAreaView>
  );
}

function CardView({ card, stacked }: { card: Card; stacked?: boolean }) {
  return (
    <View style={[styles.card, stacked && { transform: [{ scale: 0.94 }, { translateY: 12 }], opacity: 0.6, position: "absolute" }]}>
      <CardInner card={card} />
    </View>
  );
}

function CardInner({ card }: { card: Card }) {
  return (
    <View style={styles.cardInner}>
      <Image source={{ uri: card.profile_photo }} style={styles.cardImg} />
      <LinearGradient
        colors={["transparent", "rgba(5,5,5,0.4)", "rgba(5,5,5,0.95)"]}
        style={styles.cardGradient}
        locations={[0, 0.5, 1]}
      />
      <View style={styles.matchPctBadge} testID="match-pct">
        <Sparkles size={14} color={colors.neonBlue} />
        <Text style={styles.matchPctText}>{card.match_percentage}% Match</Text>
      </View>
      <View style={styles.cardBody}>
        <View style={styles.statusRow}>
          <View style={[styles.statusDot, { backgroundColor: statusColor(card.activity_status) }]} />
          <Text style={styles.statusLabel}>{activityLabel(card.activity_status, card.last_active)}</Text>
        </View>
        <Text style={styles.cardName} testID={`card-name-${card.username}`}>{card.username}, {card.age}</Text>
        <View style={styles.locRow}>
          <MapPin size={14} color={colors.textSecondary} />
          <Text style={styles.locText}>{card.country}</Text>
          <Text style={styles.locDot}>•</Text>
          <Text style={styles.locText}>{(card.languages || []).join(", ")}</Text>
        </View>
        {card.bio ? <Text style={styles.bio} numberOfLines={2}>{card.bio}</Text> : null}
        {card.shared_games && card.shared_games.length > 0 ? (
          <View style={styles.sharedRow}>
            <Text style={styles.sharedLabel}>SHARED GAMES</Text>
            <View style={styles.tagsRow}>
              {card.shared_games.slice(0, 4).map((g: string) => (
                <View key={g} style={styles.gameTag}>
                  <Text style={styles.gameTagText}>{g}</Text>
                </View>
              ))}
            </View>
          </View>
        ) : (
          <View style={styles.sharedRow}>
            <Text style={styles.sharedLabel}>PLAYS</Text>
            <View style={styles.tagsRow}>
              {(card.top_games || []).slice(0, 3).map((g: any) => (
                <View key={g.name} style={styles.gameTag}>
                  <Text style={styles.gameTagText}>{g.name}</Text>
                </View>
              ))}
            </View>
          </View>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  header: { paddingHorizontal: spacing.lg, paddingTop: spacing.sm, paddingBottom: spacing.md, flexDirection: "row", justifyContent: "space-between", alignItems: "flex-end" },
  h1: { color: colors.textPrimary, fontSize: 28, fontWeight: "800", letterSpacing: -0.5 },
  h1sub: { color: colors.textSecondary, fontSize: 13, marginTop: 2 },
  counters: { flexDirection: "row", gap: 8 },
  counterPill: { flexDirection: "row", alignItems: "center", gap: 6, paddingHorizontal: 10, paddingVertical: 6, backgroundColor: colors.neonBlueSoft, borderRadius: radius.pill, borderWidth: 1, borderColor: "rgba(0,229,255,0.3)" },
  counterPillPurple: { flexDirection: "row", alignItems: "center", gap: 6, paddingHorizontal: 10, paddingVertical: 6, backgroundColor: colors.purpleSoft, borderRadius: radius.pill, borderWidth: 1, borderColor: "rgba(139,92,246,0.4)" },
  counterText: { color: colors.neonBlue, fontSize: 13, fontWeight: "700" },
  deck: { flex: 1, alignItems: "center", justifyContent: "center", paddingHorizontal: spacing.lg },
  card: { width: CARD_WIDTH, height: CARD_HEIGHT, borderRadius: radius.lg, overflow: "hidden", backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  cardInner: { flex: 1 },
  cardImg: { width: "100%", height: "100%", position: "absolute" },
  cardGradient: { position: "absolute", left: 0, right: 0, bottom: 0, height: "70%" },
  cardBody: { position: "absolute", left: 0, right: 0, bottom: 0, padding: spacing.lg, gap: 6 },
  matchPctBadge: { position: "absolute", top: 16, left: 16, flexDirection: "row", gap: 6, alignItems: "center", backgroundColor: "rgba(0,229,255,0.18)", borderWidth: 1, borderColor: "rgba(0,229,255,0.6)", paddingHorizontal: 12, paddingVertical: 6, borderRadius: radius.pill },
  matchPctText: { color: colors.neonBlue, fontSize: 13, fontWeight: "800" },
  statusRow: { flexDirection: "row", alignItems: "center", gap: 6 },
  statusDot: { width: 8, height: 8, borderRadius: 4 },
  statusLabel: { color: colors.textSecondary, fontSize: 12, fontWeight: "600" },
  cardName: { color: colors.textPrimary, fontSize: 28, fontWeight: "800", letterSpacing: -0.5 },
  locRow: { flexDirection: "row", alignItems: "center", gap: 6 },
  locText: { color: colors.textSecondary, fontSize: 13 },
  locDot: { color: colors.textMuted, marginHorizontal: 2 },
  bio: { color: colors.textPrimary, fontSize: 14, lineHeight: 20, marginTop: 4 },
  sharedRow: { marginTop: 10, gap: 6 },
  sharedLabel: { color: colors.neonBlue, fontSize: 10, fontWeight: "800", letterSpacing: 1 },
  tagsRow: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  gameTag: { backgroundColor: "rgba(139,92,246,0.18)", borderWidth: 1, borderColor: "rgba(139,92,246,0.55)", paddingHorizontal: 10, paddingVertical: 4, borderRadius: radius.sm },
  gameTagText: { color: colors.textPrimary, fontSize: 12, fontWeight: "600" },
  overlay: { position: "absolute", top: 30, paddingVertical: 8, paddingHorizontal: 16, borderWidth: 3, borderRadius: 8 },
  likeOverlay: { right: 24, borderColor: colors.neonBlue, transform: [{ rotate: "12deg" }] },
  passOverlay: { left: 24, borderColor: colors.pass, transform: [{ rotate: "-12deg" }] },
  overlayCenter: { position: "absolute", alignSelf: "center", top: "40%", borderWidth: 3, borderColor: colors.purple, paddingHorizontal: 24, paddingVertical: 8, borderRadius: 8 },
  overlayText: { fontSize: 38, fontWeight: "900", letterSpacing: 4, color: colors.neonBlue },
  actions: { flexDirection: "row", justifyContent: "center", alignItems: "center", gap: spacing.lg, paddingVertical: spacing.md },
  actionBtn: { width: 62, height: 62, borderRadius: 31, backgroundColor: colors.surface, alignItems: "center", justifyContent: "center", borderWidth: 1 },
  passBtn: { borderColor: "rgba(236,72,153,0.4)" },
  superBtn: { borderColor: "rgba(139,92,246,0.4)", width: 52, height: 52, borderRadius: 26 },
  likeBtn: { borderColor: "rgba(0,229,255,0.4)" },
  empty: { alignItems: "center", justifyContent: "center", gap: 8, padding: spacing.xl },
  emptyTitle: { color: colors.textPrimary, fontSize: 20, fontWeight: "700", marginTop: spacing.md },
  emptyText: { color: colors.textSecondary, textAlign: "center", fontSize: 14 },
  refreshBtn: { marginTop: spacing.md, backgroundColor: colors.purple, paddingVertical: 10, paddingHorizontal: 24, borderRadius: radius.pill },
  refreshBtnText: { color: "#fff", fontWeight: "700" },
});
