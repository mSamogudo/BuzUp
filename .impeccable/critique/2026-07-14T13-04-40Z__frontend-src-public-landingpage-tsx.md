---
target: landing page
total_score: 28
p0_count: 1
p1_count: 2
timestamp: 2026-07-14T13-04-40Z
slug: frontend-src-public-landingpage-tsx
---
# Critique — BusUp landing page (`LandingPage.tsx` + `buzup-site.css`)

Method: dual-agent (A: design review, live Chrome inspection · B: detector + browser evidence). Register: brand.

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | "Baixar a app" silently opens a waitlist modal, not a download — button behavior not visible until clicked |
| 2 | Match System / Real World | 2 | On-page copy/prices are MZN, but product images show foreign locale: hero phone "75.00 AZN", app mockup "€24,50 / Lisboa – Centro / Autocarro 101" |
| 3 | User Control and Freedom | 3 | Skip link, drawer close, back-to-top, dismissible modal all present; PWA install toast can't be permanently dismissed on-page |
| 4 | Consistency and Standards | 2 | MZN on page vs EUR in images; store buttons say "Em breve" yet look like active download CTAs |
| 5 | Error Prevention | 3 | Contact form has honeypot + inline validation; pricing invites the "why buy a single ride?" error (see below) |
| 6 | Recognition Rather Than Recall | 3 | Clear labels, recognizable icons, sticky anchored nav |
| 7 | Flexibility and Efficiency | 3 | PT/EN toggle, theme toggle, skip link, keyboard-reachable |
| 8 | Aesthetic and Minimalist Design | 3 | Clean surfaces, but uppercase eyebrow on 7 sections + five repeated icon-tile grids add non-informational scaffolding |
| 9 | Error Recovery | 3 | Contact-form errors specific and bilingual |
| 10 | Help and Documentation | 3 | Footer help centre, FAQ on pricing page, phone/email exposed |
| **Total** | | **28/40** | **Good — solid foundation, two heuristics dragged down by one root cause (foreign-market imagery)** |

## Anti-Patterns Verdict

**Does this look AI-generated? Partially — clean but templated, not instant-slop.**

**LLM assessment:** Visibly *designed*, not a template dump — real art direction (editorial hero with a local brand agent, navy full-bleed "how it works" band, committed Space Grotesk/Manrope pairing, disciplined blue-and-white tokens exactly per brand). Clears the trash bar. But trips three ban-list tells:
- **Uppercase tracked eyebrow above nearly every section — CONFIRMED.** `.eyebrow` (12.5px, uppercase, blue) opens 7 sections in the identical eyebrow→h2→p triad. Strongest "an AI laid this out" signal on the page.
- **Repeated identical icon-tile grids — CONFIRMED.** Five sections are one recipe (rounded `#EAF0FF` square + blue glyph + heading + line): trust (3), benefits (4), app list (4), segments (6), chips (4). This is the generic-SaaS card-grid the brief names as an anti-reference.
- **Hero-metric cliché, gradient text, side-stripe borders — AVOIDED (good).** The numbered 4-step "how it works" is a genuine sequence, not scaffolding — leave it.

Missed personality: layout is *competent and safe* rather than *fintech-confident*. No bold moment that says "tap-to-pay is instant."

**Deterministic scan:** `detect.mjs` on `LandingPage.tsx` → exit 0, **zero findings**, no false positives. Agreement with LLM: the detector is markup-pattern based, so it correctly finds no structural slop — but the page's real problems are **content** (foreign imagery) and **semantics** (pricing logic), which a static scanner cannot see. Clean scan ≠ clean page here.

**Browser evidence:** Live on `localhost:3008`. All 4 product images load (HTTP 200, valid PNGs — no broken assets). Reveal-on-scroll IntersectionObserver fires correctly; reduced-motion guard forces `opacity:1`. No horizontal overflow, no layout breaks at desktop. One real console warning: `fetchPriority` (camelCase) not recognized by React — should be lowercase `fetchpriority` (`LandingPage.tsx:128`). Product PNGs are heavy (1.4–1.8 MB each). Mobile 390px could not be visually verified (claude-in-chrome can't emulate <~1426px) — CSS breakpoints exist at 1000/560px but rendered mobile behavior unconfirmed.

## Overall Impression

A well-built, accessible, genuinely bilingual page whose credibility is undercut by one thing: the product renders were mocked up for a different market (Azerbaijani manat, euros, Lisbon bus lines) and never localized to MZN/Maputo. For a brand whose entire thesis is *"trust is the product,"* planting a foreign currency in the very first phone a Maputo commuter sees is the worst-placed flaw possible. Fix the imagery and the pricing logic and this jumps from "good template" to "trustworthy local product." Biggest single opportunity: **re-render the hero + app screens in MZN/Maputo.**

## What's Working

1. **Localized bilingual copy.** `mkt-i18n.ts` is a complete PT↔EN dictionary — every string, including a11y and error states. PT is idiomatic Mozambican (telemóvel, M-Pesa, e-Mola, Matola, sem trocos). Directly serves brief principles 3 and 4. Best part of the build.
2. **Accessibility fundamentals actually implemented.** Real skip-link with visible focus ring, `focus-visible` outlines everywhere, a deliberate 44×44 touch-target technique (`.ttbtn::after` expands hit area without inflating the glyph), `prefers-reduced-motion` disables float + reveals + smooth-scroll, meaningful alt text on every image. Above the bar for marketing pages.
3. **Restrained, on-brand color/type.** Tokens disciplined (`--blue #0069E9`, `--navy #06122F` exactly per brand), no purple gradients, no neon, no crypto clichés. Full dark-mode theming via token overrides. Contrast measured clean (muted body ≈5.0:1, eyebrow blue ≈5.1:1 — both pass AA).

## Priority Issues

**[P0] Product imagery uses foreign currency and locale (AZN + EUR + Lisbon).**
- Why it matters: The two most important frames — hero phone ("75.00 AZN") and app mockup ("€24,50", "Lisboa – Centro", "Autocarro 101") — show a foreign market, contradict the on-page MZN pricing, break Nielsen #2/#4, and detonate trust at the exact money moments. Browser confirmed these images load fine — it's a content defect, not a technical one. A local visitor reads "copy-pasted foreign template."
- Fix: Re-render `hero-person.png` and `phone-float.png` (and any validator screen) with MZN values matching on-page prices (balance "75,00 MZN"; Diário 12 / Semanal 60 / Mensal 180), Maputo/Matola line names, MZN in recent activity.
- Suggested command: manual asset re-render (out of impeccable scope); then `/impeccable polish`.

**[P1] Pricing logic self-contradicts: single ride (20 MZN) costs more than the day pass (12 MZN).**
- Why it matters: At the money decision point, the numbers imply a rational passenger should never buy a single ride. Reads as an error, stalls comprehension.
- Fix: Reconcile the fare model, or if 12/60/180 is intentional add a one-line rationale ("O passe diário compensa a partir da 1.ª viagem") so it reads as a deal, not a typo.
- Suggested command: `/impeccable clarify`.

**[P1] PWA install toast overlaps the hero's secondary CTA.**
- Why it matters: The "Instalar BusUp" toast covers "Ver como funciona" on first paint (desktop showed it clipped to "Ver como fun…") and persists through scroll — the page's own exploratory conversion path is physically obscured.
- Fix: Move the prompt out of the CTA zone (top banner / corner chip), gate behind a scroll threshold, or suppress on the landing route. Also fix toast copy "Acesso rapido" → "rápido".
- Suggested command: `/impeccable adapt`.

**[P2] Reveal-on-scroll content is invisible without JS / on slow JS.**
- Why it matters: 46 `.reveal` elements start at `opacity:0`; only become visible when IntersectionObserver adds `.in`. Reduced-motion forces `opacity:1`, but users *without* that preference on low-end Android / slow connections (the brief's core audience) see blank content below the hero until the bundle boots. Because the project prerenders with react-snap (`build:static`), the snapshot can bake the `opacity:0` state → blank prerendered/preview HTML.
- Fix: Content visible by default; add the `opacity:0` only via a `.js`/`is-ready` class set on mount, so no-JS baseline is `opacity:1`.
- Suggested command: `/impeccable optimize`.

**[P2] Redundant "Em breve" + store-badge affordance confusion.**
- Why it matters: Each store badge shows a floating "EM BREVE" pill *and* the text "Em breve na App Store" — the phrase twice. The badges look like active download buttons but open a waitlist modal (mild bait-and-switch).
- Fix: Drop one "Em breve" instance; visually distinguish coming-soon badges from active CTAs (muted/disabled styling, pill only).
- Suggested command: `/impeccable clarify`.

**[P3] Eyebrow-on-every-section + five repeated icon-tile grids (anti-slop / personality).**
- Why it matters: Not a usability bug, but it's what makes the page read as templated and dilutes the "confident, distinctive" brand goal.
- Fix: Drop the eyebrow on 3–4 sections and let the h2 carry; vary at least one icon-grid (e.g. make segments a two-column consumer-vs-operator split instead of a flat 6-tile grid mixing passenger and B2B personas).
- Suggested command: `/impeccable distill` then `/impeccable bolder`.

## Persona Red Flags

**Mozambique commuter / low-end Android / bilingual (primary audience):**
- Hero phone "75.00 AZN" + app "euros / Lisboa – Centro" signal "not built for Mozambique" — the persona-killer.
- Reveal gated on JS → page can be blank below the hero during boot on a slow/old Android — exactly this user's device/connection.
- Five floating PNG renders (1.4–1.8 MB each) with infinite float animations — heavy for the 2G/entry-Android context the brief calls out.

**Jordan (first-timer):**
- Four hero actions that mostly hit the same waitlist modal — no single "start here."
- Pricing: single ride (20) > day pass (12) — can't tell if it's a deal or a typo, stalls at cost evaluation.
- 6-tile segment grid mixes "me" (workers/students/families) with irrelevant B2B tiles (operators/municipalities), forcing extra scanning to self-locate.

**Casey (distracted mobile):**
- Install toast covers "Ver como funciona" on mobile first paint — the one exploratory tap obscured.
- Store badges say "Em breve" twice then behave as an email form — thumb-tapping user expects an app store, gets a waitlist.

## Minor Observations

- Console: `fetchPriority` camelCase warning in React (`LandingPage.tsx:128`) — should be lowercase `fetchpriority`.
- Product PNGs 1.4–1.8 MB each; `phone-float.png` / `validator-card.png` lazy-load lag under fast scroll left the section visual momentarily blank in testing.
- Download intent expressed 3–5× above the fold (nav CTA + 2 hero CTAs + 2 store badges), all → same waitlist modal.
- `.card / .seg / .flist li / .plan` hover all use the identical `translateY(-4/-6px) + var(--shadow)` lift — hover language monotone.
- Perpetual 7–8.5s float on 4 large images — minor battery/CPU cost on target low-end devices.
- Footer is the most trustworthy block (real Matola address, phone, email, "Powered by UpDigital") — but arrives after trust is already dented upstream.
- No security/trust proof at the payment moment: a "Seguro" chip only — no encryption cue, no operator/bank logos, no "regulado", no testimonial.

## Questions to Consider

1. Your pitch is "trust is the product" — so why does the first phone a Maputo commuter sees display Azerbaijani manat, and the app screen display euros in Lisbon?
2. If "Baixar a app", both store badges, and the nav CTA all open the same waitlist form, why are there five of them? What if the hero had exactly one pre-launch action: "Avisem-me quando abrir"?
3. A single ride is 20 MZN but a full day unlimited is 12 MZN. Intentional — and if so, where do you *say* so before the reader concludes it's a bug?
4. Delete the eyebrow from all but the hero — does the page lose any information, or just stop looking section-generated?
5. For low-end Android on slow connections, why does all content below the hero depend on JS reaching IntersectionObserver before it's visible?
6. At the moment a user loads money onto a card, where is the reassurance beyond one "Seguro" chip?
