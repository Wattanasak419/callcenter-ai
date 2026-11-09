# Warranty Auto-Fill Design

## Intent

Fill missing warranty details on `/warranty/{id}` from the customer's existing records and provide visibly marked sample values where the saved data has no answer.

## Scope and behavior

- Keep the selected record as the source for customer identity, brand, case number, assignee, and any warranty fields it already contains.
- For missing warranty fields, look for another record with the same normalized phone number and brand. Include inactive records because they may hold the only warranty details.
- Use one matching record with the most populated warranty fields; break ties by newest record. Fill only blanks, and show which case supplied fallback details.
- For fields still missing after that lookup, show clearly marked mockup values and a page notice that mockup data is not real customer or warranty information.
- Keep mockup values display-only: do not save them to the database or use sample dates to calculate warranty end date or active/expired status. Real missing dates remain unknown.
- Render all warranty fields and the recorded date as actual values rather than raw template placeholders.

## Approaches

1. **Selected (user choice):** Reuse the best-matching same-phone, same-brand record, then show labeled mockup values for remaining blanks. This uses saved data first and keeps samples distinct from real data.
2. **AI extraction from conversation:** Could recover more details, but may invent or misread serial numbers, dates, or coverage; deferred.

## Constraints and non-goals

- No schema or stored-record changes.
- Do not combine warranty fields from several products or brands.
- Do not treat mockup values as proof of product coverage.

## Approval

The user selected same-customer lookup and requested mockup values for other missing information. Implementation awaits approval of this revised design.
