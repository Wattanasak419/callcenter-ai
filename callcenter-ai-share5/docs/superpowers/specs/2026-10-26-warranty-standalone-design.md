# Standalone Warranty Page

## Intent

Give Warranty its own navigation entry and overview page, separate from the customer list, while keeping the existing per-case warranty detail page.

## Goals

- List one warranty entry per case/product so multiple products for one phone remain separate.
- Let users search for a customer, phone, brand, product, or serial number and open that case's warranty detail.
- Use the existing dark OMAZZ theme and the supplied registration-detail image as a field/layout reference.
- Reuse current `CallRecord` data and existing `/warranty/{item_id}` details; clearly label any display-only mockup data.

## Non-goals

- Add a new warranty database table or change existing customer records.
- Treat sales-order values in the screenshots as customer data; the images are visual references only.
- Claim mockup values as verified warranty coverage.

## Approaches

1. **Standalone list backed by existing cases (selected):** make `/warranty` a searchable warranty overview and keep `/warranty/{item_id}` for details. This fits the current schema and needs no migration.
2. **Separate warranty table:** model registrations independently from call cases. This requires migration and a new source-of-truth/sync rule, which the project does not currently have.

The user requested a separate page and supplied screenshots of a sales order and warranty-registration detail. Reusing case records is the smallest approach that fits that request; one row per case preserves distinct products.

## Behavior

- Add a Warranty item to the sidebar navigation on the dashboard and customer pages.
- `/warranty` shows the warranty overview; `/warranty/{item_id}` continues to show the existing printable detail.
- The overview searches customer name/phone, brand, product, and serial number, and links each row to its detail page.
- Existing warranty fields come from the case and same-phone/same-brand history rules already implemented. Existing display-only samples remain visibly identified and cannot affect real status.
- The overview uses the current theme and requires no schema change.

## Approval

Approved by the user on 2026-10-26. The supplied sales-order and registration-detail screenshots are visual references only.
