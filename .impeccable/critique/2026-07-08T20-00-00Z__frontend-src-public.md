---
target: all 3 public pages (landing/pricing/contact)
total_score: 31
p0_count: 2
p1_count: 2
timestamp: 2026-07-08T20-00-00Z
slug: frontend-src-public
---
# Critique — BuzUp public pages (Landing / Pricing / Contact)

Method: dual-agent (A: design review, source-only · B: deterministic detector). Browser/overlay evidence UNAVAILABLE — the extension's Chrome could not reach the dev server (network-isolated from host) across 6 attempts; A fell back to source + computed-contrast review. Detector ran clean.

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|:---:|-----------|
| 1 | Visibility of System Status | 3 | Good nav/scroll/active states; no form submit/loading state (instant fake success) |
| 2 | Match System / Real World | 4 | Excellent — M-Pesa, e-Mola, MZN, PT-first, transit metaphors |
| 3 | User Control and Freedom | 3 | Drawer/backdrop, theme+lang reversible; no skip-link, no breadcrumb |
| 4 | Consistency and Standards | 3 | Strong shared system, but two card systems + eyebrow overuse |
| 5 | Error Prevention | 3 | noValidate + custom checks, but only on submit, basic regex |
| 6 | Recognition Rather Than Recall | 3 | Labels+icons, comparison table; pricing holds a lot at once |
| 7 | Flexibility and Efficiency | 3 | Lang/theme/anchor nav; focus ring only on form fields |
| 8 | Aesthetic and Minimalist | 3 | Clean rhythm; landing 9+ sections + eyebrow noise repeats |
| 9 | Error Recovery | **2** | Color-only error (red border), zero message text |
| 10 | Help and Documentation | 3 | FAQ, contact, help link, tooltips — adequate for marketing |
| **Total** | | **31/40** | **Good** |

## Anti-Patterns Verdict

**Does it look AI-generated?** "Competent template with visible AI scaffolding" — not pure slop, but a director clocks template DNA in seconds. Bones are template; flesh is bespoke (localized copy, custom imagery, real inclusion angle).

**LLM assessment (A):** Anti-refs VIOLATED — identical repeated card grids (5 near-identical grids, shared white/1px-line/24px-radius/translateY(-6px) hover), uppercase eyebrow above nearly every section, numbered 1-2-3-4 steps, "Mais popular" badge, floating-phone + radial-glow hero. Anti-refs AVOIDED (credit): no purple gradients (disciplined brand blue), **no hero-metric cliché**, not crypto/neon, not bureaucratic.

**Deterministic scan (B):** Detector exit 2 — **1 finding only**: `layout-transition` warning at `buzup-site.css:90` (`transition: width` on 2px nav underline pseudo-element — negligible, arguable false positive). Otherwise clean: zero side-stripe borders, zero gradient-text, backdrop-filter used only functionally (2×, sticky nav + drawer scrim), z-index is a sane semantic scale (0-3, 60, 70 — no 999/9999), clamp maxes all <4.25rem (no shouting), no letter-spacing tighter than -0.04em, `@media (prefers-reduced-motion: reduce)` present and correct (buzup-site.css:441-445).

**Agreements A+B:** eyebrow-on-every-section (B counted **13**: Landing 7, Pricing 5, Contact 1) and repeated card idiom (B counted **26** card-class usages across the two pages) — both flag as the loudest tells. **B caught what A didn't:** display font is **Space Grotesk** (`--font-display`) + Manrope body — Space Grotesk is a reflex-default; and **94 raw hex literals** bypass the palette tokens (partial token discipline). **A corrected B's contrast worry:** muted body `#5C667A` computes ≈5.8:1 on white / 5.4:1 on `--soft` — passes AA (B had flagged it "verify").

**Visual overlays:** none — browser injection unavailable (network isolation). Fallback = source + computed contrast only. Rendered dark theme, actual PNG content, and live reveal-on-scroll not visually verified.

## Overall Impression

Solid, professionally-engineered marketing site with genuine local-market fit — and a **broken funnel**. Every design decision serves "fast/secure/modern" competently, but the two moments that convert (app download, operator contact) are non-functional: CTAs point at empty anchors and the contact form silently discards submissions. The single biggest opportunity: make the funnel real, then strip the template scaffolding (eyebrows, one card idiom) so the bespoke local content carries the page.

## What's Working

1. **Real market fit, not template copy** — M-Pesa/e-Mola/MZN/Matola/"sem troco/sem papel", PT-first. Directly serves the trust/legitimacy goal. The standout.
2. **Disciplined scoped design system** — `buzup-site.css` fully namespaced under `.bz`, CSS-var theming with full dark-mode parity, real reduced-motion fallback. No leakage into the app. (Detector confirms the hygiene.)
3. **Inclusion-aware IA** — "Sem smartphone? Sem problema" + physical-card path acknowledges riders without smartphones. Thoughtful for the audience (though buried too low).

## Priority Issues

**[P0] Every primary conversion CTA is dead.** `Baixar a app`, App Store / Google Play badges, "Obter o cartão", both final-CTA download buttons → `#` / `#download` (LandingPage 76, 95, 109, 113/117, 256, 337-338). The page's entire job is non-functional. *Fix:* wire real store URLs or a waitlist capture; never ship a hero whose main button jumps to an empty anchor. *Command: /impeccable harden.*

**[P0] Contact form is a silent no-op.** `onSubmit` (ContactPage 41-55) validates then `setSent(true)` — no fetch/action. Inquiries lost while success UI celebrates. *Fix:* POST to a real endpoint; pending + error states; success only on 200. *Command: /impeccable harden.*

**[P1] Error feedback is color-only, no text.** `.field.err` = red border/pink bg (CSS 390) and nothing else. Fails WCAG 1.4.1 (color-only) + 3.3.1/3.3.3 (error id/suggestion); tanks Heuristic 9. *Fix:* inline `<span role="alert">` per invalid field ("Email inválido", "Obrigatório"). *Command: /impeccable clarify.*

**[P1] Low-contrast disabled feature rows.** `.plan li.off` `#A6AEBF` on white ≈ **2.2:1** (icon `#C4CAD6` lower) conveys what a plan EXCLUDES — meaningful info below 4.5:1. *Fix:* darken to ≥`#5C667A` + sr-only "não incluído". *Command: /impeccable audit.*

**[P2] Template scaffolding: eyebrow ×13 + one card idiom ×26.** The uppercase tracked eyebrow on nearly every section + five near-identical card grids are the AI/SaaS tells that keep this at "competent template". *Fix:* keep one deliberate kicker as brand voice, drop the rest; differentiate section rhythm; vary card treatments by content. *Command: /impeccable quieter (then /impeccable layout).*

**[P2] Dead legal/trust links.** Form's "Política de Privacidade" is `href="#"` while copy asks consent to it; footer "Sobre/Carreiras/Imprensa/Pontos de recarga" all `#`. On a page collecting personal data, a dead privacy link is a trust + compliance gap. *Command: /impeccable harden.*

## Persona Red Flags

**Jordan (first-timer, landing):** Taps hero "Baixar a app" → scrolls to final CTA → taps App Store → nothing. The one action the page wants is impossible. First impression: "is this even real?"

**Casey (mobile, one-handed, slow connection):** Four heavy PNGs (up to 1024×1536) with drop-shadow filters + continuous `bzfloaty` animation; no `loading="lazy"`, no `srcset`. Heavy on a slow Moçambique link. Reveal-on-scroll gates content on `opacity:0` until IntersectionObserver adds `.in` — no no-JS/failed-IO safety net (only reduced-motion). Theme/lang toggles ~40px, under 44px target.

**Riley (stress-tester):** Empty submit → red borders, no explanation. `a@b` → red border, still no message. Valid → "enviada!" but zero network requests; inquiry discarded. No honeypot/rate-limit; consent claimed against a dead privacy link.

## Minor Observations

- **Brand-blue drift (confirmed):** CSS `--blue:#0057FF`, but PRODUCT.md + the new logo PNG + the regenerated icon tile use `#0069E9`. Two different blues ship side by side. Pick one canonical brand blue and align CSS token, logo, and icons.
- Micro-type: store subtitle 10px, footer "Powered by" 11px — legibility-borderline.
- Content duplication: landing has a full Tarifas section AND a dedicated `/tarifas` page — and they already diverge (home 3 plans vs pricing 4 tickets). Double maintenance, drift risk.
- No skip-to-content link; keyboard users tab the full nav each page. Custom focus only on form fields; nav/buttons/FAQ rely on UA default outline.
- Placeholders `#9AA3B5` on `--soft` ≈ 2.4:1 (advisory; placeholders semi-exempt).

## Questions to Consider

1. If the single job is downloads, why does every primary CTA point to `#`? Shipped or mock — and what's the real success metric if nothing links out?
2. Need `/tarifas` AND a Tarifas section on landing? They already disagree (3 vs 4 tickets) — which updates when prices change?
3. For a market where many riders lack smartphones, why is the hero 100% app-first while the physical card (more inclusive entry) is buried mid-page?
4. Is the contact form intentionally client-only? Where does a real operator lead go today — and who notices it never arrived?
5. `--blue #0057FF` vs brand `#0069E9`: which is truth, and does the logo PNG match?
