# Warranty Auto-Fill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fill the warranty page from the selected case, then the best same-phone/same-brand record, and mark display-only mockup values for remaining gaps.

**Architecture:** Keep selection and merge logic in the `/warranty/{item_id}` route in `backend/main.py`; render the selected case's identity with merged warranty fields. Update `warranty.html` to render those values, the fallback-source case, and a clear mockup notice.

**Tech Stack:** FastAPI, SQLAlchemy, Python, HTML/CSS.

**Spec:** `docs/superpowers/specs/2026-10-25-warranty-autofill-design.md`

## Global Constraints

- Same normalized phone number and same brand for fallback records; include inactive history.
- Choose one fallback record with the most populated warranty fields; newest record wins ties.
- Keep selected case data primary and fill only missing warranty fields.
- Never save mockup values or use them to calculate real warranty status.
- Keep missing real coverage status unknown.

## Review Focus

- Another product or brand belonging to the same phone must not supply warranty details.
- Existing selected-case warranty values must not be overwritten.
- Mockup values must be visibly labeled and must not alter stored data or status.
- Missing phone or brand must not accidentally match an unrelated record.
- Warranty template fields and creation date must render without raw template syntax.

---

### Task 1: Merge warranty details and render the warranty page

**Files:**
- Modify: `backend/main.py` (`get_warranty_page` and warranty helpers)
- Modify: `backend/templates/warranty.html`

**Interfaces:**
- `get_warranty_page(item_id: int, db: Session) -> HTMLResponse` keeps the selected `CallRecord` as page identity and adds display-only merged warranty data.
- Warranty fields: `warranty_number`, `product_name`, `serial_number`, `purchase_date`, `warranty_duration`, `warranty_terms`, `start_date`, and `end_date`.

- [ ] Read the approved spec and current `/warranty/{item_id}` renderer.
- [ ] Query same-phone, same-brand records including inactive history; select one fallback by field completeness, newest first on ties.
- [ ] Merge only blank warranty fields into a display mapping; keep all selected-case identity and case fields unchanged.
- [ ] Supply clearly labeled, deterministic mockup display values for fields still blank. Do not save them or use mockup dates in `_warranty_end` or status calculation; retain unknown real status.
- [ ] Render a source-case note when historical data is used and a mockup notice when samples are shown.
- [ ] Replace all warranty template placeholders, including title, terms, and created date, with rendered values.
- [ ] Inspect the changed route/template and verify Python syntax without adding or running a test suite.

**Review checks:**
- Same customer and brand data fills gaps; other brands never match.
- Selected-case values win over historical values.
- Mockup strings remain explicitly labeled, and no database fields are changed.
- Warranty status remains based only on real dates.
- No Jinja-style placeholders remain in the served warranty HTML.
