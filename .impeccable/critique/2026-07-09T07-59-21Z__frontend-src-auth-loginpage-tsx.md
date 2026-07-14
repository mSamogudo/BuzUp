---
target: login page (first)
total_score: 27
p0_count: 0
p1_count: 3
timestamp: 2026-07-09T07-59-21Z
slug: frontend-src-auth-loginpage-tsx
---
# Critique — BuzUp login page (first run)

Method: dual-agent (A source + partial live; B detector). Product register (app auth).

## Score — 27/40. Band: Good (lower end).

Solid interaction engineering (best-in-class OTP flow) dragged down by form-a11y labeling and i18n polish. Note: several findings FIXED post-critique (see below).

Nielsen: status 3, match 3, control 3, consistency 2, prevention 3, recognition 2, flexibility 3, aesthetic 3, recovery 2, help 3 = 27/40.

Detector: 0 findings (tsx). 

## Priority (with post-critique status)
- **[P1] Inputs placeholder-only, no programmatic label** — FIXED post-critique: aria-label added to all 5 inputs.
- **[P1] Error banner not announced to screen readers** — FIXED: role="alert" added to `.login-error`.
- **[P1] PT diacritics missing in i18n.ts dictionary** (Sessao/Codigo/Funcionario/invalidas — the strings that actually render) — FIXED: Sessão, Código×5, Funcionário, inválidas, obrigatório, ative.
- **[P2] Dark-mode regressions** — FIXED: powered-by logo now theme-aware (was dark PNG invisible on dark panel); error red brightened for dark.
- **[P2] Hero logo asset says "BusUp"** (same as public P0) — USER DECISION.
- **[P3, still open] OTP boxes have no error styling (only banner); resend has no cooldown; reset modal lacks Esc/focus-trap/focus-return; text inputs stay editable during loading; staff is the default mode though passengers are primary (consider OTP-first); mode-toggle labels wrap at 380px; inactive 12px toggle label #71717a on #f4f4f5 ≈ 4.3:1 (fails AA).**

## Strengths
Best-in-class OTP (paste-distribute, auto-advance, backspace-nav, auto-submit, expiry countdown, resend, one-time-code autofill); password-manager-ready autocomplete; token-driven accent adapts light/dark; focus-visible on every custom control; reduced-motion honored.
