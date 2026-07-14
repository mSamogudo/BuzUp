---
target: all 3 public pages (re-critique)
total_score: 32
p0_count: 1
p1_count: 2
timestamp: 2026-07-09T07-14-19Z
slug: frontend-src-public
---
# Re-critique — BuzUp public pages (Landing / Pricing / Contact)

Method: dual-agent (A: design review — browser reached localhost:3008 this run, desktop only; B: deterministic detector). Prior run: 31/40.

## Design Health Score — 32/40 (+1 vs prior)

| # | Heuristic | Score | Δ | Key Issue |
|---|-----------|:---:|:---:|-----------|
| 1 | Visibility of Status | 3 | +1 | form has submitting/success states; waitlist modal gave no styled feedback (unstyled) |
| 2 | Match Real World | 4 | 0 | superb PT transit register |
| 3 | User Control & Freedom | 3 | 0 | dialog Esc/backdrop/X; reduced-motion honored |
| 4 | Consistency | **2** | −1 | logo reads "BusUp" vs "BuzUp" text; waitlist modal unstyled; stray #0057FF in table SVG |
| 5 | Error Prevention | 3 | +1 | regex+required+honeypot; honeypot was visible in unstyled modal |
| 6 | Recognition vs Recall | 4 | 0 | labeled fields, clear pricing |
| 7 | Flexibility & Efficiency | 3 | 0 | lang/theme toggles, focus rings |
| 8 | Aesthetic & Minimalist | 3 | 0 | polished bodies, but 13 eyebrows + twin card grids + AI hero + broken modal |
| 9 | Error Recovery | 3 | +1 | per-field role="alert" + server fallback |
| 10 | Help & Docs | 3 | 0 | FAQ, contact methods |
| **Total** | | **32/40** | **+1** | **Competent, not launch-ready** |

The a11y + form + footer-link fixes genuinely landed (~+3 of value), but a NEW P0 regression (waitlist modal rendered unstyled) plus the unresolved "BusUp" logo dragged Consistency down and capped the net gain at +1. With the modal fixed (done post-critique), this is a legit 34-35.

## Anti-Patterns Verdict
De-slop partially worked. Eyebrow softened (weight 600, .04em, dash gone — verified), glows toned, headings balanced, blue unified. The 3 page bodies render genuinely polished (strong dark "Como funciona" break, clean pricing table). But tells survive:
1. **AI-generated hero with garbled text** (`LandingPage.tsx:128`, hero-person.png) — validator reads "Viagenuratos", phone "75000 AIZN", card "Buzup". Loudest slop signal now; worse than the CSS ever was. Confirmed live at zoom.
2. **Eyebrow still on 13 sections** (softened, not removed) + identical 4-up card grids ×2.
3. Template silhouette persists: eyebrow → H2 → sub → card grid.

**Detector (B): near-clean** — 1 finding: `layout-transition` on the 2px nav-underline `transition:width` (`buzup-site.css:104`, negligible/false-positive). No side-stripes, no gradient-text, z-index clean (max 80), reduced-motion present (3 blocks), no oversized clamps.

**Fixes verified present (B):** eyebrow softening, `--blue:#0069E9` (no #0057FF/rgba(0,87,255) in normal CSS), skip-link+#main+focus-visible, lazy on non-LCP imgs, role="alert", honeypot both forms, reduced-motion. A11y scaffolding is real.

## Priority Issues
**[P0] Waitlist modal rendered unstyled + honeypot exposed** — `PublicLayout` mounted `<WaitlistModal/>` outside the `.bz` wrapper, so scoped styles + `--blue` tokens failed; raw HTML dialog with visible "Website" honeypot. Destination of all 6 app CTAs. **FIXED post-critique (901b3bd)** — wrapped in `<div className="bz">`.

**[P1] Logo wordmark reads "BusUp", product is "BuzUp"** — on nav/drawer/footer of every page. (Note: this is the logo asset the user supplied and approved; flagged as a brand-name reconciliation decision, not a code bug.)

**[P1] AI-generated hero with garbled text** — `LandingPage.tsx:128`. Replace with real product screenshots / clean render.

**[P2] Reveal leaves viewports blank mid-scroll** — `.reveal{opacity:0}` until IntersectionObserver (threshold .14, rootMargin −8%). Fast scroll hits blank screens. Lower the threshold or ship visible-by-default.

**[P2] Eyebrow ×13 + twin card grids** — softened only; deferred de-scaffolding needs live visual iteration.

**[P3] Last legacy blue** — `%230057FF` in comparison-table check SVG. **FIXED post-critique (901b3bd).**

## Persona Red Flags
- **Jordan (passenger, low trust):** P0 half-fixed at critique time (CTA opened broken-looking modal) → now fixed.
- **Riley (operator B2B):** well served (pricing → working contact form); "BusUp" logo quietly dents credibility.
- **Casey (keyboard/AT):** biggest winner — skip link, focus-visible, role="alert", reduced-motion all verified.

## Strengths
1. PT transit-native copy & localization — the standout.
2. Real, verified a11y scaffolding.
3. Visual craft on the 3 page bodies (dark section contrast, pricing table).

## Questions
1. Logo says "BusUp", product is "BuzUp" — which is canonical? Reconcile logo↔text.
2. Six "Baixar a app" buttons all resolve to a "not yet" waitlist — would one "Junte-se à lista" convert better than six?
3. The AI hero has reader-visible gibberish in a trust-sensitive payments market — replace with a real render?
4. On sections where the H2 already says what the eyebrow says, what's lost by deleting the eyebrow?
