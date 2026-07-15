---
target: landing page
total_score: 30
p0_count: 1
p1_count: 1
timestamp: 2026-07-14T19-08-27Z
slug: frontend-src-public-landingpage-tsx
---
# Critique — BusUp landing page (re-run, commit a443589)

Method: dual-agent (A: design review, live Chrome desktop+mobile+dark · B: detector + browser evidence). Register: brand.

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | Nav scroll state, hover, reveal, PWA/waitlist feedback all present |
| 2 | Match System / Real World | 2 | Imagery shows "75.00 AZN" + euro/"Lisboa" — breaks Mozambique framing at the payment moment (known P0); copy layer (M-Pesa, MZN) is correct |
| 3 | User Control and Freedom | 3 | Drawer/dialog/PWA dismissable, but PWA banner re-appears and competes with CTAs |
| 4 | Consistency and Standards | 3 | "Baixar a app" opens a waitlist, not a download — label/behaviour mismatch vs the honest "Em breve" badges |
| 5 | Error Prevention | 3 | Little error surface on the landing itself |
| 6 | Recognition Rather Than Recall | 4 | Labels + icons self-evident, nav anchors clear |
| 7 | Flexibility and Efficiency | 3 | Anchor nav, PT/EN toggle, theme toggle |
| 8 | Aesthetic and Minimalist | 3 | Clean system, but icon-tile repetition + persistent PWA overlay add noise |
| 9 | Error Recovery | 3 | Mobile CTA text-clipping is an unrecoverable presentation error |
| 10 | Help and Documentation | 3 | Footer help, contact, phone, email present |
| **Total** | | **30/40** | **Good — up from 28. Two heuristics held down by the known imagery P0 + new mobile-clip issue** |

## Anti-Patterns Verdict — de-slopped; would NOT immediately read as AI-made

**LLM:** Clear improvement. Reads as a competent, human-directed fintech landing page. Biggest slop-killers: the real human agent photo in the hero + restrained navy/blue palette.
- **Eyebrows 7→1 — confirmed.** Only the hero kicker remains; every downstream section leads with a plain h2. Cadence materially improved; the "eyebrow on every section" tell is gone.
- **Segments split — good, reads intentional.** "Para passageiros" (4) + "Para operadores e cidades" (2), duo capped at 740px. The clearest "a human thought about this" moment among the grids.
- **Residual slop = icon-tile density.** Still ~5 consecutive icon+heading+text patterns (trust 3, benefits 4, app-list 4, segments 4+2, chips 4 ≈ 19 icon-badge units). Containers vary (cards / list rows / pills / navy steps) so it's under the "obvious template" threshold, but it's the weakest anti-slop area.
- Hero-metric, gradient text, side-stripe — avoided. Numbered "quatro passos" is a legit ordered list.

**Deterministic scan:** `detect.mjs` → exit 0, **zero findings**, no false positives.

**Browser evidence:** All 4 product images load (HTTP 200, render). Reveal content **visible by default** in all three states (as-loaded, js-reveal forced, prerender-sim) — P2-reveal fix confirmed solid. Segments = 2 `.seg-group` blocks confirmed. Store badges = `.store.soon` dashed confirmed. **No React `fetchPriority` warning** — lowercase fix holds. Console: only 2 pre-existing React Router v7 future-flag warns + 1 PWA info; no errors.
- **Important divergence:** B measured `documentElement` horizontal overflow = **0px at true 390px (CDP emulation)** — but that metric is **masked by `.bz{overflow-x:hidden}`**. A, measuring the actual element edges, found the final CTA card content overflowing to 410px with buttons clipped past the viewport. The overflow-hidden hides the scrollbar so the user can't even scroll to reach the clipped buttons. **The clean overflow metric is a false all-clear; the LLM caught the real break.**

## Overall Impression

The trust/clarity + anti-slop pass landed: honest pre-launch signalling, logical fare ordering, one-eyebrow cadence, a real segments IA, and content that's now visible without JS. Score moved 28→30. But mobile — the product's stated primary context — has two fresh breaks that undercut the win: the **final CTA clips its own buttons at 390px**, and the **dark-mode nav wordmark is nearly invisible**. Biggest opportunity: fix the mobile CTA overflow (it's the highest-intent moment, visibly broken) and make the brand logo theme-aware.

## What's Working

1. **Restrained, human hero** — real agent photo + single flat-blue accent + one eyebrow escapes template-land and delivers the trustworthy fintech tone.
2. **Honest pre-launch signalling** — dashed "Em breve" store badges, waitlist-aware aria-labels, final CTAs reworded to "Avisem-me quando abrir". No longer over-promises a download that doesn't exist.
3. **Pricing IA** — 4 fare points as 3 cards + one prose avulsa line, strict ascending order (8<12<60<180), "Mais popular" anchor on Semanal. Low load, transparent.

## Priority Issues

**[P0] Foreign currency/locale in product imagery** *(known / re-render in progress)* — hero phone "75.00 AZN" + app "€ / Lisboa – Centro" break trust at the payment moment. Fix: re-render mockups with MZN + Maputo/Matola. Listed for completeness. → user is handling.

**[P1] NEW — Final CTA clips text + buttons on mobile (≤~410px).** `.cta` / `.bz-home .cta-card` (LandingPage ~347–359; CSS ~464–480, 589–590). At 390px the card is 350px but content `scrollWidth`=410px; each `.cta-actions .btn` right edge = 392px, past the card and viewport; paragraph + buttons ("Avisem-me quando abrir (Android)", "Falar com a equipa BusUp") are cut, and `.bz{overflow-x:hidden}` hides the scrollbar so they can't be reached. Root cause: mobile single-col grid children have `min-width:auto`, and `.btn` sets `white-space:nowrap` + `min-width:230px` → a ~347px min-content track can't shrink into the ~302px box. **Aggravated by this pass's longer CTA labels.** Fix: at ≤560px add `.bz-home .cta-card{grid-template-columns:minmax(0,1fr)}` (or `min-width:0` on `.cta-actions`/`.inner`) AND `.cta-actions .btn{white-space:normal;min-width:0;width:100%}`. Verify longest PT label. → `/impeccable adapt`.

**[P2] NEW — Dark-mode nav/brand logo invisible.** `BrandLogo.tsx` uses a static `tone` prop; nav + drawer render default `onLight` = navy wordmark PNG. On the transparent nav over the dark hero, the navy "Bus" disappears; only blue "Up" shows. Every dark-mode visitor loses the brand name on first impression. Fix: make `BrandLogo` theme-aware — render both PNGs and swap via `html[data-theme="dark"]`, or read theme from `useUi()`. Footer's explicit `tone="onDark"` is fine; only theme-reactive surfaces (nav, drawer) break. → `/impeccable adapt` or `colorize`.

**[P3] NEW — PWA install banner competes with the page's own conversion path.** `PwaInstallPrompt.tsx` fires immediately (no scroll/time gate on the `beforeinstallprompt` path), persists across all scroll, overlaps content, and adds a third install ask ("Instalar BusUp") alongside "Baixar a app" (→waitlist) and "Avisem-me quando abrir". Fix: gate behind scroll-depth/time and/or suppress on the landing route until past the hero; reconcile wording with the "Em breve / Avisem-me" pre-launch narrative. → `/impeccable adapt` + `clarify`.

**[P3] Residual — icon-tile density.** ~5 stacked icon+heading+text grids carry the page middle. Vary one more (e.g. drop icons from one grid, or make one a different composition) to break the SaaS sameness. → `/impeccable distill` / `layout`.

## Persona Red Flags

**Casey (distracted mobile) — hit hardest:** the clipped final CTA (P1) breaks the primary conversion buttons exactly where they decide; the persistent PWA banner steals the bottom thumb-zone. Touch targets themselves fine (≥48px).
**Jordan (first-timer):** "Baixar a app" opens a waitlist not a store — mild bait-and-switch; "75.00 AZN" reads as "not for my country". The 4-step "Como funciona" orients well.
**Mozambique commuter / low-end Android:** reveal ships visible by default (good, no JS-gate); but hero PNG (1086×1448) + 4 floating PNGs with infinite `bzfloaty` transforms are heavy on a slow link (float disabled under reduced-motion — correct — but no low-bandwidth image strategy). AZN currency alienates this core persona most.

## Minor Observations

- "Baixar a app" promises a download but triggers `openWaitlist()`; consider "Quero a app" / "Entrar na lista" pre-launch to match the badges.
- Landing has an in-page `id="tarifas"` section AND nav "Tarifas" → separate `/tarifas` route — confirm intentional.
- `.seg-grid` `auto-fit minmax(232px,1fr)`: at ~470–700px the 4 passenger tiles may land 2+2 vs 1-col — verify the mid-range reads deliberate.
- `.plan .desc{min-height:44px}` hard-codes alignment height; longer EN strings may wrap to 2 lines and misalign — check EN.
- "Avisem-me" (2nd-person plural) is an intentional informal register, consistent across CTAs — confirm it's the desired voice vs "Avise-me".

## Questions to Consider

1. The hero sells "trust is the product", yet its own phone shows a successful payment in a foreign currency. Why is the trust-defining asset the one that's wrong?
2. Four overlapping install asks (hero "Baixar a app"→waitlist, badges "Em breve", PWA "Instalar", CTA "Avisem-me"). What exactly should a first-time visitor do in the next 5 seconds — one obvious thing, or four ambiguous ones?
3. The mobile final CTA — the highest-intent moment — clips its own buttons off-screen. What does your pre-ship review actually test at 390px? Should mobile be the default review viewport for a mobile-first product?
4. Five stacked icon-tile grids carry the page middle. Delete the icons — does the page lose meaning, or just lose the thing that makes it feel like every other SaaS template?
