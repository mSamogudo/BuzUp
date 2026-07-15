---
target: login page
total_score: 36
p0_count: 0
p1_count: 0
timestamp: 2026-07-15T08-42-05Z
slug: frontend-src-auth-loginpage-tsx
---
Method: dual-agent (A: design review · B: detector + browser evidence) — RE-RUN after adapt/audit/clarify/delight/polish.

# Critique — BuzUp Login (`frontend/src/auth/LoginPage.tsx`) — re-run

Prior fixes hold under measurement. **Score 30 → 36/40.** No P0/P1. Remaining items are refinements, not defects.

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | Spinner + timer + verifying-green good; verifying not announced to SR, no post-success confirmation before redirect |
| 2 | Match System / Real World | 4 | PT-first, M-Pesa/e-Mola, prefixes, plain labels |
| 3 | User Control and Freedom | 3 | Back/change/resend/mode-switch present; reset modal has no Escape-to-close |
| 4 | Consistency and Standards | 4 | BusUp naming unified; one-time-code; aria patterns; reset modal borrows admin shell (slight seam) |
| 5 | Error Prevention | 4 | Submit gated; inputMode numeric; paste/auto-advance sanitize |
| 6 | Recognition over Recall | 4 | Visible labels, phone hint, OTP echoes target phone |
| 7 | Flexibility and Efficiency | 4 | OTP paste, auto-advance, auto-submit, autocomplete, full keyboard path |
| 8 | Aesthetic and Minimalist | 4 | Brand panel, NFC rings, clean hierarchy, balanced type |
| 9 | Error Recovery | 3 | role=alert + shake + clear + resend; verifying-green reads ambiguously like success |
| 10 | Help and Documentation | 3 | Assurance line + trust points; no support affordance (fine for login) |
| **Total** | | **36/40** | **+6 vs prior 30 — "Good, minor polish only"** |

## Anti-Patterns Verdict

**LLM: NOT SLOP (confidently human-crafted).** Scoped `.lgn-*` token system; the NFC "tap" motif now carries end-to-end (dark rings → CTA ripple → OTP digit-pop → verifying-green → error-shake); PT-first copy with correct diacritics; real product refs (M-Pesa, e-Mola, 84/85/86/87); every animation `prefers-reduced-motion`-gated. Delight is thematically coherent (payment = tap) — the opposite of slop.

**Detector (`detect.mjs`): clean — `[]`, exit 0.** Console clean (only Vite + known RR-v7 future-flag warnings). No glass/gradient-text/side-stripe/magic-z-index inside `.lgn`. Prior dead `.login-*` focus/error rules confirmed removed; surviving `.login-field*` rules are live (reset modal).

**Contrast (measured, both themes): all PASS.**
- Dark `--lgn-blue-text` #8FB4FF on #0A1224 = **9.01:1** (eyebrow/links), active pill **8.36:1**, sub **7.65:1**; brand-side lead ~11:1, tpoint ~16:1.
- Light: eyebrow/links #0057FF **5.52:1**, inactive tab 5.38:1, sub 5.77:1.
- (B's first light-theme brand-side reading of 1.7/1.1 was a false positive — gradient bg not exposing solid backgroundColor; recomputed ~11:1 and ~16:1.)

**Touch targets (measured):** mode pills 44, theme 44×44, backlink 44, password-toggle 44×44 — all PASS. **Only miss: `.lgn-langtog` PT/EN buttons at 44×38 (8px short on height).**

## What's Working

1. **Accessibility rebuild is real, not cosmetic** — dark blue AA smashed (9.01:1), focus-visible rings render on every `.lgn-*` control in both themes, full keyboard path incl. password reveal.
2. **Complete, sane keyboard path** — password toggle reachable (tabIndex 0, aria-label, aria-pressed); reset modal is role=dialog/aria-modal with auto-focused input.
3. **Coherent, restrained delight** tied to tap-to-pay, fully reduced-motion-gated.

## Priority Issues (all P2/P3 — refinements)

- **[P2] Peak-end not closed.** OTP success `navigate(replace)` fires immediately — no post-verify confirmation. Verifying-green softens but doesn't cap it; on a 200ms connection the user never sees it. **Fix:** brief (~350–450ms, min-duration guaranteed) verified beat (ShieldCheck/green check) after verify resolves, before redirect. → `/impeccable delight` or inline
- **[P2] Reset modal a11y gaps.** No Escape-to-close, no focus trap, labeled via `aria-label` not `aria-labelledby`→visible `<h3>`. The one control that skipped the a11y pass. → `/impeccable harden`
- **[P2] Staff tab-order oddity.** "Esqueceu a palavra-passe?" sits in the label-row *above* the password input, so tab/SR order is username → forgot-link → password. **Fix:** move link after input in DOM (or below visually). → `/impeccable adapt`/inline
- **[P3] OTP verifying/auto-submit silent to SR.** Auto-submit on 6th digit + verifying produce no `aria-live`. **Fix:** `aria-live="polite"` region for "A verificar…" + countdown. → `/impeccable harden`
- **[P3] Register-mode eyebrow mismatch.** Eyebrow reads "ÁREA DO PASSAGEIRO" while heading says "Criar conta de Passageiro". **Fix:** dedicated "CRIAR CONTA" eyebrow for register mode. → `/impeccable clarify`
- **[P3] Lang toggle 44×38.** 8px short on height (B measured). **Fix:** `.lgn-langtog button` min-height 44 (or container padding). → inline

## Persona Red Flags

- **Casey (mobile/3G):** targets + toggle fit confirmed; auto-verify-on-6th could fire before a slow network responds (verifying-green mitigates); no offline/timeout messaging for a dropped OTP request (minor).
- **Sam (a11y):** big wins — focus both themes, dark blue AA, full keyboard incl reveal. Remaining: modal focus-trap/Escape, silent verifying state, forgot-link tab order. None blocking.
- **Jordan (first-timer):** clear labels + trust + cross-links; only register eyebrow mismatch could cause a half-second doubt.

## Minor Observations

- Disabled `.lgn-submit` renders lighter-solid-blue — could momentarily read as loading vs disabled (cosmetic).
- Wrong-code shake clears all 6 digits + refocuses digit 1 — punishing on slow 3G re-type; preserving digits for correction would be kinder.
- OTP digit uses both `autoFocus` and a `setTimeout(focus,100)` — redundant but benign.
- Reset modal (admin shell, `--app-*` vars) not visually verified in dark this pass.

## Questions to Consider

1. If verify resolves in 200ms the success-green is never seen — should the success beat have a guaranteed min-duration rather than tracking network latency?
2. Wrong-code clears all digits — would preserving them and highlighting for correction be kinder on 3G?
3. Staff is the default mode on a passenger-facing product — should passenger OTP be the default instead?
4. The reset modal is the one control still on the admin shell — adopt `.lgn-*` for a single coherent auth surface?
