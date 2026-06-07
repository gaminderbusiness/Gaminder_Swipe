# Gaming Buddy — Product Requirements (MVP)

## Overview
Gaming Buddy is a mobile app (React Native Expo, iOS-first) that helps gamers discover, match, and chat with other gamers based on the games they play. NOT a dating app — purpose is finding gaming friends, duo partners, teammates.

## Stack
- Frontend: Expo SDK 54, expo-router, react-native-reanimated, react-native-gesture-handler, lucide-react-native, react-native-svg, expo-linear-gradient
- Backend: FastAPI, MongoDB (motor), bcrypt token-based auth
- Theme: Dark `#050505`, neon blue `#00E5FF`, purple `#8B5CF6`

## Features Built
1. **Auth (email + password)** — JWT-less bearer-token sessions. Signup includes username, age, country, languages, bio, top games + hours.
2. **Swipe screen** — Tinder-style card swipe (reanimated + gesture handler). LIKE/PASS/SUPER overlays animate on drag. Bottom action buttons.
3. **Daily Like quota** — 20 likes / 24h; counter visible in header.
4. **Super Like** — 1 per 7 days; vertical swipe up or button.
5. **Standout tab** — Top 10 highest-compatibility profiles with Super Like CTA.
6. **Matches tab** — Mutual likes; rows with avatar + activity status + last message preview.
7. **Chat tab + chat detail** — Text messaging, 3s polling for new messages.
8. **Profile tab** — Steam-styled top games library with rank, hours, plus like/superlike stats.
9. **Activity status** — Online (<5m), Recently Active (<3h), Offline. Computed from `last_active` updated on every authenticated request.
10. **Match Modal** — Celebratory overlay with "It's a Match" badge + go-to-chat CTA.
11. **Seeded 20 realistic gamer profiles** on backend startup for instant demo.

## Compatibility Algorithm
Score (1-99) = shared games (50pts) + playtime similarity (20pts) + country match (15pts) + shared language (15pts), with a minimum floor based on deterministic hash to ensure every card shows a meaningful percentage.

## Out of Scope (MVP)
Premium subs, voice/video chat, forums, file sharing, Xbox/PlayStation integration, real Steam OAuth (mocked), dating mode.

## Routes
- `/auth/welcome`, `/auth/login`, `/auth/signup`
- `/(tabs)/swipe`, `/(tabs)/standout`, `/(tabs)/matches`, `/(tabs)/chat`, `/(tabs)/profile`
- `/chat/[matchId]`

## Backend Endpoints (all prefixed `/api`)
- POST `/auth/signup`, POST `/auth/login`, GET `/auth/me`
- PUT `/profile/me`
- GET `/swipe/feed`, POST `/swipe`
- GET `/standout`
- GET `/matches`
- GET `/messages/{match_id}`, POST `/messages/{match_id}`
