# Dashboard Category Tabs Design

**Intent:** Let staff inspect call center performance by category without changing the dashboard's existing look or leaving the page.

## Goals
- Add in-page category tabs for overview, employee performance, customer satisfaction, and issue/alert insights.
- Reuse the existing `/files` data, date filters, metrics, charts, and case-inspection modal.
- Keep the current colors, layout language, Thai/English toggle, and responsive behavior.
- Show employee-level averages from evaluated calls grouped by `assigned_agent_code`; keep unassigned calls out of the ranking and retain their existing place in general totals.

## Non-goals
- No new API, database fields, dependencies, or separate routes.
- No changes to how scores or sentiment are calculated.
- No redesign of the sidebar or global visual theme.

## Approaches
1. **In-page tabs (selected):** switch visible dashboard sections and reuse current state. This matches the reference interaction with the smallest change.
2. Separate pages: more room per category, but adds navigation and duplicated page state.

## Behavior
- Keep the existing summary header and time filters visible across categories.
- Overview shows headline metrics and issue distribution.
- Employee performance shows a descending leaderboard of assigned agents, with average agent score and evaluated-call count; clicking an agent opens that agent's matching cases.
- Customer satisfaction shows the existing sentiment summary, distribution chart, and drill-down.
- Issues and alerts shows keywords, issue categories, anomalies, and their existing case drill-downs.
- Time filters apply to every category. Switching language updates tab labels too. Existing modal and export/print behavior remain available.

## Constraints and implementation calls
- Implement within `backend/templates/dashboard.html`; use the dashboard's existing arrays and renderer rather than adding a framework.
- Preserve the current visual tokens and theme.
- Use only evaluated (`agent_score > 0`) cases assigned to an agent in the ranking; an agent with no evaluated calls is not ranked.
- Preserve existing role checks, date filter behavior, record status handling, and all current case calculations.
