# BotForge Demo Reel — Production Plan

## Overview
- **Format**: Animated screenshot reel with text overlays
- **Duration**: ~60 seconds
- **Scenario**: "Bella's Boutique" — e-commerce customer support bot
- **Target**: Upwork clients evaluating AI chatbot development services

## Demo Account
- **Site**: https://bot.fenloai.com
- **Email**: demo@bellasboutique.com
- **Password**: BotForgeDemo2026!

## Demo Documents
- `bellas-boutique-support-guide.txt` — Full support KB (returns, shipping, sizing, pricing, loyalty, escalation)
- `bellas-boutique-faq.txt` — 12 common FAQs

## Shot List

| # | Time | Scene | Screenshot | Text Overlay |
|---|------|-------|-----------|--------------|
| 1 | 0-3s | Title card | Generated (no screenshot) | "BotForge — AI Chatbot Platform" |
| 2 | 3-8s | Dashboard | `/dashboard` with stats populated | "Your command center" |
| 3 | 8-13s | KB Upload | `/kb` — upload both .txt files | "Upload your docs" |
| 4 | 13-16s | Processing | `/kb` — documents show "ready" | "Auto-parsed & embedded" |
| 5 | 16-22s | RAG Chat Q1 | `/chat` — "What is your return policy?" | "Instant answers" |
| 6 | 22-26s | RAG Chat Q2 | `/chat` — "Do you ship internationally?" | "With source citations" |
| 7 | 26-30s | Knowledge Gaps | `/kb?tab=gaps` — gap detected | "Knows what it doesn't know" |
| 8 | 30-37s | Voice | `/voice` — web call panel + transcript | "AI phone agent" |
| 9 | 37-44s | Inbox | `/inbox` — multi-channel conversation list | "Unified inbox" |
| 10 | 44-50s | Analytics | `/analytics` — charts and metrics | "Real-time analytics" |
| 11 | 50-55s | Channels | `/channels` — WhatsApp + widget setup | "Deploy everywhere" |
| 12 | 55-60s | CTA | Generated (no screenshot) | "Let's build yours → Upwork" |

## Chat Script (Exact Questions)

**Question 1**: "What is your return policy?"
- Expected: 30-day return policy, original tags, sale items exchange only
- Citations: bellas-boutique-support-guide.txt, bellas-boutique-faq.txt

**Question 2**: "Do you ship internationally?"
- Expected: Canada shipping, $9.95 standard, $19.95 express
- Citations: bellas-boutique-support-guide.txt

**Question 3** (for knowledge gap): "Do you have a store in New York?"
- Expected: Bot can't answer (not in docs) → knowledge gap created

## Production Steps

### Phase A: Seed the Demo
- [x] Register demo account on live site
- [x] Complete onboarding wizard (skip or finish)
- [x] Upload both demo documents to KB
- [x] Wait for processing to complete (20 chunks indexed)
- [x] Send chat questions to populate conversations
- [x] Trigger a knowledge gap

### Phase B: Take Screenshots
- [x] Dashboard (with populated stats) — `02-dashboard.png`
- [x] Knowledge Base (documents listed as "ready") — `03-kb.png`
- [x] Chat conversation (with citations visible) — `05-chat.png`, `05-chat-q1.png`
- [x] Knowledge Gaps tab — `07-gaps.png`
- [x] Voice page (web call panel) — `08-voice.png`
- [x] Inbox (conversation list) — `09-inbox.png`
- [x] Analytics (charts populated) — `10-analytics.png`
- [x] Channels page — `11-channels.png`

### Phase C: Build Animation
- [x] Create HTML page with CSS keyframe animations
- [x] Add screenshots as background images per slide
- [x] Add text overlays with fade-in/out transitions
- [x] Add progress bar at bottom
- [x] Test autoplay timing
- [ ] Export or screen-record

## Output
- HTML animation file: `frontend/public/demo/reel.html`
- Screenshots: `frontend/public/demo/screenshots/`
- Final video: Screen-record the HTML page with Loom/OBS
