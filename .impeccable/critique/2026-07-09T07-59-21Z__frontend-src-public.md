---
target: "public pages re-critique #2"
total_score: 33
p0_count: 2
p1_count: 0
timestamp: 2026-07-09T07-59-21Z
slug: frontend-src-public
---
# Re-critique #2 — BuzUp public pages

Method: dual-agent (A live browser + B detector). Prior: 31 → 32.

## Score — 33/40 (+1 vs 32). Band: Good, not yet brand-distinctive.

Both prior fixes verified holding (live + source): waitlist modal now renders styled under `.bz` (honeypot hidden off-screen), and blue is uniform `#0069E9` (zero `#0057FF`/`rgba(0,87,255)`/`%230057FF`). The +1 is earned by the restored funnel (styled waitlist dialog with success state) + blue consistency. Capped at +1 by two untouched brand-asset P0s.

Nielsen: status 4, match 3, control 3, consistency 3, prevention 4, recognition 3, flexibility 3, aesthetic 2, recovery 4, help 4 = 33/40.

Detector: 1 finding at assess time (`transition:width` nav underline, buzup-site.css:104) — FIXED post-critique (→ transform:scaleX). Now clean. No side-stripes, no gradient-text, disciplined z-index, reduced-motion complete.

## Priority
- **[P0] Logo wordmark reads "BusUp", all copy says "BuzUp"** — nav/footer/login lockup. Brand-name defect in the primary lockup. Needs corrected PNG (or confirm BusUp is canonical). USER DECISION.
- **[P0] Hero `hero-person.png` is AI-generated with garbled text** ("Viagenuratos", "75000AIZN", card "BuzYp"). Most trust-damaging element. Replace with real render. USER DECISION.
- **[P2] Eyebrow ×10-13 + repeated icon-card grids** — template cadence; needs live visual iteration.
- **[P3] No active-section nav indicator; root route intermittently redirected to /login during review (confirm public landing isn't auth-gated).**

## Strengths
Thorough error handling (role=alert, aria, focus-to-error, honeypots), strong PT/MZN local match, solid a11y/SEO scaffolding.
