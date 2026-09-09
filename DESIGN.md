# Compliance Copilot interface system

## Direction

The interface follows a **control ledger** direction: an institutional operations workspace built for repeated compliance work. It uses the structure and density of a case register rather than the visual language of a consumer chatbot or a generic analytics template.

The product is light first. Deep green establishes identity and navigation; warm neutral surfaces keep long sessions calm. Rules, documentary evidence, generated explanation, and human actions remain visually distinct.

## Foundation

- Background: warm slate `#f4f5f1`.
- Surface: white `#ffffff`; muted surface `#f0f2ed`.
- Primary text: graphite `#18221d`; secondary `#49574f`; muted `#6e7b73`.
- Brand: institutional green `#176149`; hover `#124b3a`; shell `#06251c`.
- Semantic colors: green for allowed/success, blue for reporting/information, amber for pre-approval/warning, red for restriction/danger, slate for inconclusive and inactive states.
- Focus: two-pixel green outline with offset. Every interactive control must remain visible by keyboard.

CSS custom properties live in `frontend/src/app/globals.css`; the corresponding brand scale lives in `frontend/tailwind.config.ts`. New interface code should use these shared values and semantic component variants.

## Typography

The system UI stack avoids an external font dependency. Page titles are 24px with restrained negative tracking. Section titles are 14–16px and semibold. Body and table content use 14px; metadata and overlines use 10–12px. Identifiers, percentages, dates, values, and tickers use tabular figures or the system monospace stack.

## Geometry and spacing

- Default radii: 6px for controls, 9px for panels, 12px for modal surfaces.
- Panels use a one-pixel slate border and a minimal shadow.
- Controls have a 40px minimum height.
- The desktop shell uses a 272px sidebar, a 72px top bar, and a content maximum of 1440px.
- Tables remain dense, with 12px vertical row padding. On narrow screens, their panel owns horizontal scrolling so the document never overflows.

Whitespace and dividers create hierarchy. Avoid decorative gradients, glass effects, large shadows, oversized cards, purple accents, and icon tiles without informational purpose.

## Navigation

The sidebar groups routes into Workspace, Compliance, Supervisão, and Administração. Items are filtered by the existing role rules. The current route uses a high-contrast white state. The footer identifies the current user and role and contains logout.

Below the tablet breakpoint the sidebar becomes a modal drawer with a backdrop and explicit open/close controls. The top bar retains page context and the demo-environment indicator.

## Decisions and status

`DecisionBadge`, `RiskBadge`, and `StatusBadge` are the canonical status components. Each combines text, color, and an icon or shape, so meaning never depends on color alone.

- `ALLOWED`: green check.
- `REPORT_REQUIRED`: blue report icon.
- `PRE_APPROVAL_REQUIRED`: amber clock.
- `RESTRICTED`: red prohibition icon.
- `INCONCLUSIVE`: slate question icon.

Color stays local to badges, alerts, and small emphasis areas. It must not flood a result page. A Copilot result presents the structured decision first, matched rules second, generated explanation third, and source evidence last. Only the applicable workflow action is prominent.

## Components

Use `Button` variants for primary, secondary, ghost, and destructive actions. Use `ConfirmDialog` for consequential changes. Use `Panel`, `SectionHeader`, `FilterBar`, and `TableFrame` where they reduce repeated layout. Known-content loading uses `Skeleton` or `SkeletonRows`; spinners are reserved for small regions and submitted actions. `SourceCard` is the canonical rendering for document name, section, page, excerpt, and relevance score.

Form labels stay adjacent to their controls. Help text and validation errors sit below the related field. Errors use inline alerts and should expose retry when the operation is safe to repeat. Empty states describe what is absent and show a call to action only when the current role can perform it.

## Responsive behavior

Desktop remains information dense. Form grids collapse to one column on mobile. Page actions wrap below the heading. Tables scroll inside their bordered surface. The shell, Copilot input, approval actions, dialogs, and upload control remain keyboard accessible and usable at 390px wide. Motion is disabled when `prefers-reduced-motion` is active.
