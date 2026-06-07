import { Tabs } from "expo-router";
import { Flame, Star, MessageCircle, User as UserIcon, Heart } from "lucide-react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { colors } from "@/src/lib/theme";
import { View, StyleSheet } from "react-native";

export default function TabsLayout() {
  const insets = useSafeAreaInsets();

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarStyle: {
          backgroundColor: colors.surface,
          borderTopColor: colors.border,
          borderTopWidth: 1,
          height: 64 + insets.bottom,
          paddingTop: 8,
          paddingBottom: Math.max(insets.bottom, 8),
        },
        tabBarActiveTintColor: colors.neonBlue,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarLabelStyle: { fontSize: 11, fontWeight: "600" },
      }}
    >
      <Tabs.Screen
        name="swipe"
        options={{
          title: "Swipe",
          tabBarIcon: ({ color, size }) => (
            <View testID="tab-swipe"><Flame size={size} color={color} /></View>
          ),
        }}
      />
      <Tabs.Screen
        name="standout"
        options={{
          title: "Standout",
          tabBarIcon: ({ color, size }) => (
            <View testID="tab-standout"><Star size={size} color={color} /></View>
          ),
        }}
      />
      <Tabs.Screen
        name="matches"
        options={{
          title: "Matches",
          tabBarIcon: ({ color, size }) => (
            <View testID="tab-matches"><Heart size={size} color={color} /></View>
          ),
        }}
      />
      <Tabs.Screen
        name="chat"
        options={{
          title: "Chat",
          tabBarIcon: ({ color, size }) => (
            <View testID="tab-chat"><MessageCircle size={size} color={color} /></View>
          ),
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: "Profile",
          tabBarIcon: ({ color, size }) => (
            <View testID="tab-profile"><UserIcon size={size} color={color} /></View>
          ),
        }}
      />
    </Tabs>
  );
}

const _s = StyleSheet.create({});
