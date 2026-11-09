# Standalone Warranty Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an independent Warranty overview page while keeping case-specific printable warranty details.

**Architecture:** Reuse `CallRecord` data. Serve a new list template at `/warranty`, expose its records through a customer-permission-protected read endpoint, keep `/warranty/{item_id}` as the detail view, and add Warranty links to the existing dashboard and customer sidebars.

**Tech Stack:** FastAPI, SQLAlchemy, HTML, CSS, vanilla JavaScript.

**Spec:** `docs/superpowers/specs/2026-10-26-warranty-standalone-design.md`

## Global Constraints

- One list item per case/product; do not group distinct cases by phone.
- Do not add a warranty table or schema migration.
- Keep the existing dark theme and existing detail route.
- Keep display-only mockup fields visibly marked and out of real warranty status calculations.

## Review Focus

- A phone with multiple cases/products must retain a separate list item for each case.
- Search must match customer, phone, brand, product, and serial fields.
- List links must open the selected case's existing `/warranty/{item_id}` page.
- `/warranty` must not serve the raw detail template with unresolved placeholders.
- The two main sidebar links must work in both Thai and English labels.

---

### Task 1: Add the standalone Warranty overview

**Files:**
- Create: `backend/templates/warranty_list.html`
- Modify: `backend/main.py` (`warranty_default_page`)
- Modify: `backend/templates/dashboard.html` (sidebar and translations)
- Modify: `backend/templates/customers.html` (sidebar and translations)
- Modify: `backend/templates/warranty.html` (return link)

**Interfaces:**
- `/warranty` serves `warranty_list.html`.
- `GET /api/warranties` returns customer-permission-protected case data; the list filters/searches client-side and links to `/warranty/{item_id}`.
- `/warranty/{item_id}` keeps its current response and data rules.

- [ ] Add a responsive table/card list using the current OMAZZ dark theme, with customer, phone, brand, product, serial, warranty dates/status, and a detail action.
- [ ] Add `GET /api/warranties` under the existing customer-view permission so users without dashboard permission can load the page.
- [ ] Fetch warranty records, render one entry per case, and provide a clear empty state and search across the review fields.
- [ ] Add a Warranty sidebar item to dashboard and customer pages in Thai and English.
- [ ] Point the detail page's return link back to `/warranty`.
- [ ] Route `/warranty` to the new overview while preserving `/warranty/{item_id}`.
- [ ] Check Python syntax and inspect for unresolved template placeholders; do not add or run a test suite.
