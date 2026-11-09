# Review Requirements — Call Center AI

This document records the reviewed requirements and how the current implementation addresses them.

## Data retention: Enable / Disable only

Customer/call records must not be physically deleted through the normal application workflow. Operational record management uses `enabled` / `disabled` status through `/api/cases/{file_id}/status`.

Legacy delete permission keys are intentionally absent from the active permission matrix, so legacy delete endpoints cannot be authorized through RBAC.

## Export data

The CSV export endpoint `/export/csv` exports the complete `record_to_dict()` representation for matching records, including customer data, warranty data, call metadata, AI analysis, conversation data, quality scores, status, agent assignment and timestamps.

Supported filtering:
- all records
- one `record_id`
- all records for a customer phone number

## Warranty data

Warranty information is stored with the call/customer record and includes:
- warranty number
- product name
- serial number
- purchase date
- warranty duration
- warranty terms
- brand

The dedicated warranty page is `/warranty/{file_id}`.

## Case transfer

Cases can be forwarded to another valid employee through `/api/cases/{file_id}/transfer`. The destination is stored in `assigned_agent_code`.

## Roles and permissions

The system uses three roles.

### Staff / พนักงาน
Handles day-to-day customer operations: dashboard, customer records, customer registration, audio upload and case transfer. Staff cannot manage employee accounts, system permissions, or enable/disable records.

### Supervisor / หัวหน้า
Oversees customer operations and staff. Supervisor can view customer/dashboard data, register customers, upload audio, enable/disable records, transfer cases and view employees. Supervisor does not control the system permission matrix or employee account administration.

### IT / ผู้ดูแลระบบ
Responsible for technical administration: dashboard/system visibility, employee account administration, permission configuration and system settings. IT does not perform normal customer registration, audio upload, case transfer, or operational record enable/disable by default.

Permissions remain configurable through the Permission Matrix UI so access can be increased or reduced when organizational policy changes.

## UI language and readability

The application uses Thai for operational explanations and user-facing actions, while established technical/product terms such as Dashboard, Staff, Supervisor, IT, Warranty and AI may remain in English where they improve clarity. Avoid mixing languages for the same action on different pages.

User-facing body text should target at least 16px for normal content and larger sizes for headings, important values and actions.

## Cloud readiness

For cloud deployment:
- keep secrets in environment variables; do not commit `.env`
- keep uploaded recordings and AI model files outside Git
- use persistent/object storage for production uploads
- use a managed/persistent database rather than relying on a local SQLite file for multi-instance production deployment
- configure `CALLCENTER_AUTH_SECRET` from the cloud secret/environment configuration
- place the FastAPI service behind HTTPS/reverse proxy or a managed application/load-balancing service
- add backups, logging and access controls before production use

These requirements are deployment guidance; cloud provider selection is intentionally independent of the application logic.
