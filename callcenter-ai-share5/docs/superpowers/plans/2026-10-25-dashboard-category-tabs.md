# Dashboard Category Tabs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add in-page dashboard categories while retaining the existing theme, filters, data, and case drill-down behavior.

**Architecture:** Keep the hero and time filters in place, then group existing dashboard blocks into four tab panels. Add a small client-side leaderboard derived from the already-loaded filtered calls, grouped by `assigned_agent_code`.

**Tech Stack:** FastAPI Jinja HTML template, existing CSS, vanilla JavaScript, existing Chart.js instances.

**Spec:** `docs/superpowers/specs/2026-10-25-dashboard-category-tabs-design.md`

## Global Constraints
- No new API, database fields, dependencies, or routes.
- Preserve the current theme and Thai/English language switch.
- Preserve existing date filters, metrics, score calculations, case status behavior, and case modal.
- Rank evaluated assigned calls only; keep unassigned calls in existing overall totals.

## Review Focus
- Empty or unassigned agent data: show an empty state and no fabricated employee score.
- Date filters: every category and leaderboard use `filteredFiles`.
- Hidden charts: resize an existing chart when its panel becomes visible.
- Language switch: update all category tab labels and empty-state copy.
- Case drill-down: employee rows show that agent's cases; existing topic and sentiment drill-downs still work.

---

### Task 1: Group dashboard content into accessible category tabs

**Files:**
- Modify: `backend/templates/dashboard.html`

**Interfaces:**
- Consume existing `filteredFiles`, `dashboardBarChart`, `dashboardDonutChart`, `openInspectByType`, and `displayModalCases`.
- Add `setDashboardTab(tab)` to update selected tab state, panel visibility, and resize the two existing charts.
- Add `renderAgentLeaderboard(files)` and `openInspectByAgent(agentCode)`; aggregate assigned records with `agent_score > 0`, order by average score descending, and open matching assigned cases from the current filtered set.

- [x] Add four translated tab buttons (overview, employee performance, customer satisfaction, issues and alerts) and four `role="tabpanel"` panels, with overview selected initially.
- [x] Place current KPI/topic blocks in overview, the new leaderboard and existing score breakdown in employee performance, the existing sentiment chart in customer satisfaction, and keywords plus anomaly cases in issues and alerts.
- [x] Add small theme-matched responsive tab and leaderboard styles, with visible focus indicators.
- [x] Render the leaderboard from `filteredFiles` whenever existing dashboard renderers run; keep unassigned cases out of ranking and use `assigned_agent_code` as the label.
- [x] Add category tab language keys and keyboard navigation (left/right, Home/End); retain selection across language changes.
- [x] Review the template diff and manually trace initial, empty-data, filter-change, language-switch, keyboard, and case-drill-down flows. Do not add a separate test framework or change unrelated code.

