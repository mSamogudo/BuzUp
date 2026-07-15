---
target: login page
total_score: 30
p0_count: 0
p1_count: 2
timestamp: 2026-07-15T07-32-06Z
slug: frontend-src-auth-loginpage-tsx
---
Method: dual-agent (A: design review · B: detector + browser evidence)

# Critique — BuzUp Login (`frontend/src/auth/LoginPage.tsx`)

Faithful port of a claude.ai/design login template, localized for BuzUp. Judged on fidelity + craft; genuine slop tells still flagged.

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | Spinner + OTP countdown good; no explicit success beat before redirect |
| 2 | Match System / Real World | 3 | Broken PT diacritics ("Numero", "codigo"); "Funcionário" vs eyebrow "EQUIPA" drift |
| 3 | User Control and Freedom | 3 | Change-phone/resend/cancel present; OTP auto-submits on 6th digit (no final review) |
| 4 | Consistency and Standards | 2 | Product name renders both **BusUp** and **BuzUp**; focus CSS targets dead class names |
| 5 | Error Prevention | 3 | Submit gated on required fields; numeric OTP filter; no phone format/mask validation |
| 6 | Recognition Rather Than Recall | 3 | Labels + masked phone echo; phone-format hint lives only in a 2.4:1 placeholder |
| 7 | Flexibility and Efficiency | 4 | OTP paste, auto-advance, one-time-code/current-password autofill, theme/lang — strong |
| 8 | Aesthetic and Minimalist | 3 | Clean, but above-fold dense: 3-mode toggle + 4 top-nav controls + eyebrow/h1/sub + brandside |
| 9 | Error Recovery | 3 | `role="alert"` banner + resend/change; messages generic; `.lgn-error` has no dark override |
| 10 | Help and Documentation | 3 | Security reassurance + trust points + reset flow adequate for a login |
| **Total** | | **30/40** | Good — held back by consistency + mobile/dark a11y defects |

## Anti-Patterns Verdict

**LLM assessment — Low-to-moderate ("premium template").** High-craft execution, not lazy output, but the *composition* is a recognizable stock pattern, so it doesn't read as distinctively BuzUp. Genuine tells: the dash-eyebrow (`.lgn-eyebrow`) appears **3× on one screen** (ACESSO DE EQUIPA / ÁREA DO PASSAGEIRO / A APP BUZUP) — the single most common AI-UI tell; split-screen auth + dark-gradient brand panel + 3× icon/title/subtitle trust points is the default SaaS-login template; radial navy + concentric rings + noise overlay is a generic "fintech premium" texture kit. Redeeming craft: Space Grotesk scale with `text-wrap: balance`, tabular-nums countdown, strong OTP UX, theme + i18n. The NFC "tap rings" are the **only** brand-specific idea — the one element that couldn't be pasted into any other fintech login.

**Deterministic scan** (`detect.mjs` on LoginPage.tsx): **clean — `[]`, exit 0, zero rule hits.** The stylistic tells above are choices the detector does not flag; reduced-motion is respected and contrast passes in light theme, so they're defensible, not defects. No glassmorphism, no gradient text, no side-stripe borders in the `.lgn` block; z-index scale modest (`.lgn-top` 20).

**Where detector + review agree/diverge:** detector clean everywhere; the review's real defects are semantic/contextual (dead focus selectors, dark-mode contrast, mobile overflow, naming) that a markup regex can't catch — that's why Assessment A's live inspection carries the P1s.

## Overall Impression

Handsome, trustworthy, well-crafted login that nails the passenger OTP moment. But it's a premium *template*, not an ownable BuzUp surface, and three concrete defects hit the exact core audience (low-end Android, one-handed, keyboard/AT users): a mobile toggle overflow, invisible button focus + failing dark-mode blue, and sub-44px targets. Biggest opportunity: fix the a11y/mobile defects, then make the tap-rings motif work harder so the page is unmistakably BuzUp.

## What's Working

1. **OTP flow craft** — masked phone echo, auto-advance/backspace, full paste handling, auto-submit on completion, `one-time-code` autofill, tabular `mm:ss` countdown. Best-executed part, and exactly the passenger trust moment that matters.
2. **Minimal fields + honest reassurance** — 1–2 fields per mode, green-shield "Pagamento protegido e encriptado", UpDigital attribution. Builds trust for a low-trust, low-bandwidth audience.
3. **Cohesive dark theme + brand fidelity** — the seam between near-black form column and gradient navy panel reads as one premium surface; logo/powered-by variants swap correctly by theme.

## Priority Issues

- **[P1] Mode toggle overflows on real phones.** The 3 segmented labels are `white-space: nowrap` and too long (~460px of text in a 320px box); the third pill clips to "Cria…". The `≤480` `flex:1` rule can't save it because nowrap pins each item's min-width to its text. **Why:** the primary mode-switch is broken on the low-end Android that IS the core audience. **Fix:** shorten mobile labels ("Funcionário / Passageiro / Criar conta"), allow `white-space: normal` + `flex-wrap`, or stack vertically under `≤480`. → **/impeccable adapt**
- **[P1] Invisible button focus + dark-mode blue fails WCAG AA.** `:focus-visible` rules (styles.css 4370–4373) target dead classes `.login-submit / .login-mode-btn / .otp-link-btn / .locale-flag-button`; the component renders `.lgn-*`, so every button/link falls back to a 0.8px near-black UA outline — invisible on dark navy, unusable for keyboard users. Separately, `--lgn-blue` #0057FF is never lightened for dark: eyebrow, inline links, and active-mode label run ~3.2–3.4:1 on the dark bg (FAIL). **Fix:** add `.lgn-*` `:focus-visible { outline: 2px solid var(--lgn-blue); outline-offset: 2px }`; add a dark text-blue token (e.g. existing #8FB4FF) for eyebrow/links/active label. → **/impeccable audit**
- **[P2] Sub-44px touch targets on primary controls.** Mode pills (h35), lang toggle (40×32), theme (40×40), password toggle (36×36), text links (~39×20) all miss 44×44 — one-handed on a moving bus. **Fix:** raise mode-pill + top-nav control min-height to 44px; give password toggle a 44px hit area (padding, same icon size). → **/impeccable adapt**
- **[P2] Brand name inconsistency: BusUp vs BuzUp.** i18n renders "Bem-vindo ao **BusUp**" / "Welcome to **BusUp**" while `brandsideEyebrow` says "A app **BuzUp**" / "The **BuzUp** app" and the tab title is BuzUp. Two spellings on one auth screen erodes trust. **Fix:** pick one canonical spelling, enforce across i18n + assets. → **/impeccable clarify**
- **[P3] Broken PT diacritics.** "Numero de Telefone" (→ Número), otpSubtitle "receber o codigo de acesso" (→ código) — yet register mode spells "código" correctly. Inconsistent accents in the primary language read unpolished. **Fix:** correct the i18n strings. → **/impeccable clarify**

## Persona Red Flags

- **Casey (mobile, one-handed on a bus):** P1 toggle overflow clips "Criar Conta" — a new passenger can't cleanly see the register option; sub-44px pills compound it. State/thumb-reach otherwise OK.
- **Sam (a11y / keyboard + screen reader):** three independent AA gaps — no visible focus on any button (dead selectors), dark-theme links/eyebrow fail 4.5:1, and password reveal is `tabIndex={-1}` so unreachable by keyboard.
- **Jordan (first-timer):** BusUp/BuzUp spelling split + phone-format hint hiding in a 2.4:1 placeholder create "is this legit / what do I type?" hesitation at the trust moment.

## Minor Observations

- Auto-submit on the 6th OTP digit (50ms) is efficient but removes final review; keep the explicit "Verificar" as the deliberate action, or add a beat.
- `.lgn-error` has no dark-theme override (the dark rule targets stale `.login-error`), so the error banner stays light-mode red on dark navy.
- Placeholders duplicate labels verbatim ("Utilizador"/"Utilizador", "Senha"/"Senha") — redundant; only the phone placeholder carries real info.
- Ring pulse (3.6s infinite) is respected under `prefers-reduced-motion`, but for default users it animates continuously beside the form the user is filling.
- Terminology drift: "Entrar como Funcionário" vs eyebrow "ACESSO DE EQUIPA" vs "staff" — three words for one concept.

## Questions to Consider

1. Does a 3G passenger need a split-screen with an animated brand panel, or would a single-column, toggle-first, thumb-reachable layout serve the task better — and kill the mobile overflow at the root?
2. Is a 3-way toggle the right model? Staff vs passenger are different journeys; would a separate `/staff` entry (default everyone to passenger OTP) remove the densest decision on the page?
3. The eyebrow appears 3×. If you deleted every eyebrow, would any user be worse off?
4. Right now only the NFC rings are unmistakably BuzUp — should that "tap" motif echo into the submit or OTP interaction so the brand idea works harder?
