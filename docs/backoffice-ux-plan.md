# BuzUp Backoffice — UI/UX & Error-Handling Improvement Plan

> Scope: the entire backoffice (`frontend/src/admin/`, 30 pages) + shared UI (`frontend/src/ui/`).
> Goal: consistent, professional, accessible UI; forms that guide instead of frustrate;
> error messages a non-technical user understands; coherent toast + notification system.

---

## 1. Where we are today

**Foundation is already good — do not rebuild it:**

| Asset | File | Status |
|---|---|---|
| Toasts | `lib/toast.ts` (sonner) | Works, underused for success |
| Confirm dialogs | `ui/ConfirmDialog.tsx` (`useConfirm`) | Used universally for destructive actions |
| Modals | `ui/common.tsx` `AdminModal` | Used by all create/edit forms |
| Tables | `ui/common.tsx` `DataTable` | Search + sort + paginate + skeleton + empty |
| Detail views | `ui/DetailDrawer.tsx` | Used by ~20 pages |
| API errors | `lib/api.ts` `extractApiError` | Returns **first** error string only |
| Design tokens | `styles.css` `:root` | BuzUp blue `#1D5FA7`, Zinc, Inter/Manrope, dark mode |

**Design-system target (keep existing brand, systematize it):**
Data-Dense Dashboard style — KPI cards, dense tables, drill-down, minimal padding,
row-hover highlight, hover tooltips, smooth filter transitions. WCAG AA.
Avoid: ornate decoration, removing filters.

## 2. Top systemic problems (from full 30-page survey)

1. **No field-level validation.** Forms rely on browser `required`; on submit, any backend
   error becomes one generic `"Erro"` toast. User can't tell *which field* or *why*.
2. **DRF per-field errors discarded.** `extractApiError` flattens `{field: [msg]}` to a single
   string. Backend validation is effectively invisible.
3. **Silent error swallowing.** Detail loads use `.catch(() => {})` (PassengersPage:57-69,
   RoutesPage:58, StopsPage:52, FaresPage:67, DashboardPage:99) → drawers show stale/empty data, no reason given.
4. **Mutation buttons rarely show spinners.** Most show a `busy` label swap, no `ButtonSpinner`. Users double-click.
5. **Empty states are bare text.** No icon, no "create your first X" guidance.
6. **Inconsistent filters.** PaymentsPage hand-rolls a 6-control filter bar; others use DataTable's single search; DevicesPage filters via tabs. No reusable pattern.
7. **Detail view split.** ~20 pages use `DetailDrawer`; TripDetailPage uses bespoke inline sections.
8. **Raw/untranslated technical messages** can reach the toast (e.g. JSON dumps, `Erro 500`).
9. **Notifications bell is a dead placeholder** ("Sem notificacoes." hardcoded, AdminLayout:195).
10. **TripDetail polls every 5s** with no backoff / stop / "last updated" indicator.

---

## 3. The plan — phased

Each phase builds shared primitives first, then rolls them across pages. Order = highest pain first.

### Phase 0 — Shared primitives (build once)
New files in `frontend/src/ui/`:

- **`ApiError`** (extend `lib/api.ts`): a class carrying `message: string` **and**
  `fieldErrors: Record<string,string>`. `extractApiError` becomes `parseApiError` returning both.
  All `apiFetch/apiPost/...` throw `ApiError` instead of bare `Error`.
- **`form.tsx`** — `FormField` wrapper: `<label>` + required asterisk + optional helper text +
  error slot (red text + `aria-invalid` + `aria-describedby`). Variants: text, select, textarea, number.
- **`SubmitButton`** — primary button with built-in `ButtonSpinner`, `disabled` while busy, busy-label.
- **`useFormSubmit`** — hook wrapping the submit lifecycle: sets `busy`, calls API, on `ApiError`
  routes `fieldErrors` to fields + `message` to toast, on success fires success toast + closes.
  Kills the copy-pasted try/catch in every page.
- **`EmptyState`** — icon + title + hint + optional CTA button. Replaces bare `admin-empty-state` text.
- **`FilterBar`** — composable filter row (search + select chips + date range) to replace
  PaymentsPage's bespoke version and standardize the rest.
- **`errorMessages.ts`** — map of HTTP status / known backend codes → friendly i18n keys
  (PT/EN). Fallback: "Algo correu mal. Tenta novamente." / "Something went wrong."
  Never show raw `Erro 500` or JSON.

### Phase 1 — Error & feedback system (highest impact)
- Wire `ApiError` end-to-end; `parseApiError` maps status → friendly message via `errorMessages.ts`.
- Remove silent `.catch(() => {})` on detail/data loads → show toast + inline retry in drawer.
- Standardize: **success toast on every mutation** (create/update/delete/approve/block), not just errors.
- Build a real **notification center**: replace the dead bell popover with a list fed by recent
  actions (start client-side: session activity log; leave a typed hook for a future backend feed).

### Phase 2 — Form system rollout
- Convert every `AdminModal` form to `FormField` + `SubmitButton` + `useFormSubmit`.
  Pages: Drivers, Passengers, Fares (3 forms), Cards (2), Routes, Packages (2), Vehicles (2),
  Stops, Devices (2), Pricing, Topups, etc.
- Add: required-field markers, helper text on non-obvious fields, inline field errors from `fieldErrors`.
- Light client validation before submit (required, phone/email format, positive amounts) so the
  user gets instant feedback without a round-trip.

### Phase 3 — Loading, empty & polish
- `ButtonSpinner` on **all** mutating buttons (via `SubmitButton`, so automatic).
- Replace all `emptyMessage` text with `EmptyState` (icon + guidance + create CTA where applicable).
- Skeletons already exist for tables; add skeletons to DetailDrawer and Dashboard cards.
- TripDetail polling: add backoff, a visible "Atualizado há Xs", and pause when tab hidden.

### Phase 4 — Detail-view consistency
- Standardize on `DetailDrawer` for record details; refactor TripDetail to the same shell (or
  formalize a `DetailPage` layout and apply consistently). One mental model.
- Add per-field copy-to-clipboard + status badges uniformly.

### Phase 5 — Table & filter standardization
- Roll `FilterBar` to all list pages; migrate PaymentsPage off its custom bar.
- Consistent column density, row-hover, sticky header, right-aligned numeric/currency columns.

### Phase 6 — Accessibility, responsive & token cleanup
- Audit per ui-ux-pro-max checklist: 4.5:1 contrast, visible focus rings, `aria-label` on icon
  buttons, keyboard nav, `prefers-reduced-motion`, 44px touch targets.
- Verify 375 / 768 / 1024 / 1440px. Modals/drawers full-screen on mobile.
- Consolidate ad-hoc inline `style={{}}` (AdminLayout has many) into token-driven CSS classes.

### Phase 7 — SEO (public pages only — backoffice is auth-gated, not indexable)
- Scope `/seo-optimizer` to `public/` (Landing, Pricing, Contact): titles, meta description,
  Open Graph, JSON-LD, semantic headings, Core Web Vitals. Backoffice excluded by design.

---

## 4. Suggested execution order & effort

| Phase | Pain killed | Touches | Rough effort |
|---|---|---|---|
| 0 Primitives | enables all | new `ui/` files + `api.ts` | M |
| 1 Errors/feedback | #1,2,3,8,9 | `api.ts` + all pages (light) | M |
| 2 Forms | #1,2,4 | ~15 form pages | L |
| 3 Loading/empty | #4,5,10 | all pages (light) | M |
| 4 Detail views | #7 | ~5 pages | M |
| 5 Filters/tables | #6 | list pages | M |
| 6 a11y/responsive | quality | global CSS | M |
| 7 SEO | public only | `public/` | S |

Recommend shipping **Phase 0 + 1 together** first (biggest UX jump for least surface change),
then Phase 2.

## 5. Design guardrails (apply throughout)
- SVG icons only (lucide) — no emoji.
- `cursor-pointer` + 150–300ms color/opacity hover (no layout-shifting scale).
- Light mode body text `#475569` min; borders `#e4e4e7` visible.
- Reuse existing tokens (`--app-*`); don't introduce new palettes.
- Toast policy: success = green, error = red w/ friendly message, never raw status/JSON.
