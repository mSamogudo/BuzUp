---
target: landing page
total_score: 29
p0_count: 1
p1_count: 2
timestamp: 2026-07-14T19-47-59Z
slug: frontend-src-public-landingpage-tsx
---
# Critique — BusUp landing page (3rd pass, HEAD 677dadd)

Method: dual-agent (A: design review, live desktop+mobile+dark+/en · B: detector + browser evidence). Register: brand.

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | Good hover/scroll/dialog feedback; 4 CTAs silently funnel to the same waitlist/#download with no state hint |
| 2 | Match System / Real World | 3 | PT-first language match strong; currency/locale problem sits in imagery (scored under #4) |
| 3 | User Control and Freedom | 3 | Skip-link, drawer close, dialog ::backdrop dismiss all present |
| 4 | Consistency and Standards | 2 | Prices disagree across surfaces: page tarifas 12/60/180 MZN vs app-mockup €4,50/16/40 vs hero phone 75.00 AZN — three currencies on one page |
| 5 | Error Prevention | 3 | Low-risk page; forms validate |
| 6 | Recognition Rather Than Recall | 3 | Clear anchor nav + labels |
| 7 | Flexibility and Efficiency | 3 | Lang + theme toggle, anchored jumps |
| 8 | Aesthetic and Minimalist | 3 | Clean, but three icon-tile bands add visual redundancy |
| 9 | Error Recovery | 3 | Waitlist/contact error copy human |
| 10 | Help and Documentation | 3 | Footer help/contact, FAQ on pricing route |
| **Total** | | **29/40** | **Good — capped by unfixed product imagery (drags #4 to 2). Every structural fix from passes 1–2 holds.** |

Prior runs: 28 → 30 → 29. The plateau is real: the dominant remaining lever is the imagery P0, which is asset content (user re-rendering), not layout. Code-side returns are now diminishing.

## Anti-Patterns Verdict — structurally de-slopped; residual = icon-tile density

**LLM ban-list walk:** eyebrow (1, pass), hero-metric (pass), gradient text (pass, `.accent` solid blue), side-stripe (pass), text overflow (pass — mobile CTA wrap holds), numbered markers (soft-flag — the 4 "quatro passos" are legit ordinal but should be `<ol>`). **FAIL (residual, worst area): three icon+heading+text grids** — benefits `.cards` (4), app `.flist` (4 check-tiles), segmentos `.seg` (4+2) = ~14 near-identical "soft-blue rounded icon square + bold label + muted line" tiles. Different shells, same rhythm → the only place still reading templated.

**Detector:** `detect.mjs` → exit 0, **zero findings**, no false positives.

**Browser evidence:** all 3 fixes from pass 2 hold — CTA buttons within 390px (right 346), dark-logo swap correct (light hidden / dark shown in dark theme), PWA banner absent at scrollY 0 (gated), reveal visible by default (loaded + prerender-sim opacity 1), segments = 2 groups, badges dashed, eyebrow = 1. No `fetchPriority` warning; console clean bar 2 React Router v7 future-flag warns. **New hard datum: 3 hero PNGs are 1.37–1.79 MB each (~4.6 MB combined for the four) — heavy for the slow-connection core audience.**

## Overall Impression

The structural discipline is holding across three passes. What remains splits cleanly: (1) the **imagery P0** (two phone renders still foreign — hero AZN + app-mockup €/Lisboa; validators ARE localized) which only re-rendered assets fix and which caps the score; (2) one genuine **P1 design decision** — the three icon-tile grids; (3) a handful of **P2/P3 polish** items (card-title baselines, "hoje" copy tension, semantics, /en mockup, PWA desktop overlap, image weight). Biggest lever remains the imagery.

## What's Working

1. **Dark mode is genuinely polished** — theme-aware wordmark swap, card surfaces lift off bg with legible borders, no contrast failures observed.
2. **Hero art direction beats the anti-reference** — a real human agent presenting card + phone, warm and specific, not the generic-SaaS abstract-illustration trap.
3. **Restraint on the fixed items** — single eyebrow, ordered transparent pricing (8 payg / 12<60<180), waitlist-aware dashed badges. Structural discipline is clean.

## Priority Issues

**[P0] Foreign currency/locale in the two phone renders** *(known, user re-rendering).* Hero `hero-person.png` = "75.00 AZN" + English "Payment Successful"; app `phone-float.png` = "€ 24,50", "Autocarro 101 · Lisboa – Centro", €4,50/16/40. Validators are correctly localized. Fix: re-render both phones with MZN, PT UI, a Maputo route (e.g. "Chapa 101 · Baixa – Museu"). Caps the score until done.

**[P1] Collapse the three icon-tile grids into distinct treatments.** ~14 near-identical tiles = #1 slop signal. Fix: keep ONE as a card grid (benefits); recast app `.flist` as an image-anchored feature list (it already pairs with the phone — lean in); render segmentos as inline text pills / a single "who it's for" line instead of a third bordered-icon grid. Differentiate shape, not just content. → `/impeccable distill` / `layout`.

**[P1] Price/currency parity in the mockup (persists even after the P0 re-render).** Once localized, the mockup's ticket prices must equal the page's 12/60/180 MZN or a passenger spots the lie. Fix: bake 12/60/180 MZN into `phone-float.png`'s "Comprar bilhete" list. → asset (pair with P0 re-render).

**[P2] Benefits card title raggedness + ad-hoc head spacing.** "Pagamento sem contacto" wraps to 2 lines while the other three titles are 1 line → body copy starts on a different baseline per card. Also `.head` spacing set via inline `style={{marginBottom}}` (6px/34px) rather than a token/class. Fix: `min-height` on `.card h3` (~2 lines) to lock baselines; move ad-hoc head margins into CSS classes. → `/impeccable layout`.

**[P2] Final-CTA promise/reality copy tension.** "Comece a viajar com a BusUp **hoje**" over "**Avisem-me quando abrir**" is contradictory pre-launch. Fix: soften the heading to launch-appropriate copy ("Seja dos primeiros a viajar com a BusUp."). → `/impeccable clarify`.

**[P3] Semantics + a11y nits + /en mockup + PWA desktop overlap + image weight.** Heading skip (hero h1 → trust-strip h4, no h2/h3 between); the 4 steps are `<div class="step">` not `<ol>`; on `/en` the mockup still shows PT ("Saldo disponível"); the PWA toast pins bottom-right covering the last card corner on desktop for its whole lifetime; PNGs >1.3 MB should be WebP/AVIF. Fix piecemeal. → `/impeccable harden` / `optimize`.

## Persona Red Flags

- **Jordan (commuter, skims):** "75.00 AZN" on the hero phone in the first 2s → "this isn't for me / foreign template." Highest-impact.
- **Casey (compares prices):** €4,50 daily in the mockup vs 12,00 MZN in tarifas → "which is it?" Trust dent at the money moment.
- **Mozambique / low-end Android:** hero PNG 1086×1448 + four `bzfloaty`-animating drop-shadowed images ≈ heaviest part of the page on a weak GPU/slow link; `fetchpriority` helps LCP but WebP/AVIF + a perf-gated float would help. "Lisboa" in the mockup silently tells this exact user it was built elsewhere.

## Minor Observations

- Heading-level skip: hero h1 → `.trust-item h4` with no intervening h2/h3 — semantic nit.
- The 4 "quatro passos" are `<div class="step">`, not an `<ol>`; numbered markers would be free + semantic as an ordered list.
- Affordance honesty: store badges + "Comprar bilhete" + "Baixar a app" all resolve to waitlist/scroll — many doors, one pre-launch room.
- Segmentos "duo" grid (`max-width:740px`) leaves a large empty right gutter on desktop vs the full-width passenger row above — slightly unbalanced.
- Focus-visible outlines + 44px `::after` hit-areas correctly implemented — good.

## Questions to Consider

1. Delete the segmentos icon grid, replace with one sentence ("Trabalhadores, estudantes, turistas, famílias, operadores e municípios.") — is anything of value lost, or does the page get faster AND less templated?
2. The hero sells trust with a human face, then the phone in his hand shows a foreign currency. Which does a first-time visitor believe?
3. Three CTAs on the final card, all opening the same waitlist — choice, or the illusion of choice papering over "the app isn't out yet"? What would a single honest "Entrar na lista de espera" cost?
4. Four images floating on independent sine timers — on a $60 Android in Maputo, is that "premium," or the frame the user notices dropping?
5. If "trust is the product," why does the most-viewed pixel (hero phone balance) still say 75.00 AZN on the 3rd pass?
