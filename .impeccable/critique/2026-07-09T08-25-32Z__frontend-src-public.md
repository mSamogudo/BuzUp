---
target: "public re-critique #3 (BusUp rename)"
total_score: 34
p0_count: 1
p1_count: 1
timestamp: 2026-07-09T08-25-32Z
slug: frontend-src-public
---
# Re-critique #3 — BusUp public pages

Method: dual-agent (A source+live DOM; B detector). Prior: 31→32→33.

## Score — 34/40 (+1 vs 33). Band: Good (upper).

BusUp rename verified complete in source (B: 0 stale "BuzUp", 72 "BusUp"; A: 0 grep matches). Consistency H4 moves 2→3 — the prior logo↔text P0 is resolved. Detector CLEAN (exit 0, first fully clean run): nav underline now transform:scaleX, --blue #0069E9 uniform, reduced-motion complete, z-index bounded.

Nielsen: 3/3/3/3(+1)/3/3/3/3/4/3 = 34/40.

## Fixed post-critique (were blocking the live score)
- Live :3008 served a stale pre-rename bundle (Windows Docker mount doesn't propagate file events → Vite didn't rebuild). Restarted frontend container; live now renders "BusUp" (Vite-served i18n module: 54 BusUp / 0 BuzUp).
- index.html + manifest + robots hardcoded "BuzUp" (outside src/, missed by the sweep) → renamed (commit 568d742). PWA/home-screen name + tab title now BusUp.

## Remaining
- [P0] AI-generated hero image with garbled text (LandingPage.tsx:128, hero-person.png). Last credibility killer. Needs a real render — ASSET DECISION.
- [P1] Eyebrow x10-13 softened not removed; template tell (H8).
- [P2] Quad card-grid monotony (benefits/how/app/segments + 2 pricing grids).
- [P2] Pricing shown twice (Landing tarifas vs /tarifas, slightly diverging).
- [P3] dist/ build artifact still says BuzUp until npm run build:static rebuild.

## Strengths
Best-in-class error/recovery (role=alert, aria, focus-to-error, server fallback); genuine PT/MZN localization; honest pre-launch waitlist funnel.
