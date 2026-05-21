# Telemetry Data Model

## Tables

| Table | Purpose |
|---|---|
| `NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL` | Raw events, `PAYLOAD` as JSON/VARIANT |
| `NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT` | Flattened view — JSON keys as regular columns. **Preferred** for Metabase. **Always use this full name — the alias `NUSIGHTS_EVENTS_FLAT` does not exist as a Snowflake object.** |

Use the flat view for Query Builder questions. The raw table requires SQL to parse JSON.

In the Query Builder data picker this table appears as **Nusights Events Activitytype Default Historical Tbl Flat**. In SQL, always use `NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT` — never the shorthand `NUSIGHTS_EVENTS_FLAT`.

## Column mapping

Metabase shows columns by their **display name** (Title Case with spaces), but the underlying DB column is uppercase snake_case. SQL questions use the DB name; Query Builder filters and custom expressions use the display name in `[brackets]`.

| Telemetry event field | DB column (SQL) | Metabase display name (Query Builder) | Notes |
|---|---|---|---|
| `actionName` | `DESTINATION_NAME` | `Destination Name` | Primary event-name column |
| `actionName` (fallback) | `ACTION_NAME` | `Action Name` | Sometimes populated when `Destination Name` isn't |
| `actionType` | `ACTION_TYPE` | `Action Type` | Usually `click`, `view`, `submit` |
| `featName` | `FEATNAME` | `Featname` | Feature area (e.g. `Role`, `Policy`) |
| `pageSection` | `PAGE_SECTION` | `Page Section` | e.g. `form.create_role` |
| `subPageSection` | `SUB_PAGE_SECTION` | `Sub Page Section` | **Often NULL for bulk/group events** |
| `product` | `PRODUCT` | `Product` | |
| `sessionId` | `SESSION_ID` | `Session ID` | |
| `hashedAccountId` | `HASHED_ACCOUNTID` | `Hashed Accountid` | Numeric in the flat view |
| `hashedAccountId` (payload) | `PAYLOAD_HASHED_ACCOUNTID` | `Payload Hashed Accountid` | |
| `entityId` | `ENTITY_ID` | `Entity ID` | |
| `entityId` (payload) | `PAYLOAD_ENTITY_ID` | `Payload Entity ID` | |
| `entityTypeName` | `ENTITY_TYPE_NAME` | `Entity Type Name` | |
| `eventId` | `EVENT_ID` | `Event ID` | |
| `eventType` | `EVENT_TYPE` | `Event Type` | |
| `sourceClusterUuid` | `SOURCE_CLUSTER_UUID` | `Source Cluster UUID` | |
| `sourceClusterUuid` (payload) | `PAYLOAD_SOURCE_CLUSTER_UUID` | `Payload Source Cluster UUID` | |
| timestamp | `TIMESTAMP` | `Timestamp` | Datetime type |
| URL | `URL` | `URL` | |

Other display names visible in the table: `Namespace`, `Iam Svc Acc Details`, `Pulse Converted Cluster Type`, `Pulse Converted Cluster Version`, `Pulse Converted Ncc Version`, `Source Cluster Hypervisor Type`, `Source Cluster Rackable Unit Model`, `Source Cluster Type`, `Source Cluster Version`, `Source Collected Timestamp Usecs`, `Source Instance UUID`, `Source Ncc Version`, `Payload Timestamp Usecs`, `Validation Stage Timestamp Usecs`.

## Usage rules

- **Query Builder filters / custom expressions**: use the display name with `[brackets]`, e.g. `[Destination Name]`, `[Sub Page Section]`, `[Hashed Accountid]`. Names are case-sensitive in expressions.
- **SQL questions**: use the DB column name uppercase, e.g. `DESTINATION_NAME`, `SUB_PAGE_SECTION`, `HASHED_ACCOUNTID`.
- The data picker in the notebook editor shows the table as **Nusights Events Activitytype Default Historical Tbl Flat** — the user typically searches by typing `Nusights` or `flat`.

## Event name patterns

Event names in `Destination Name` / `Action Name` follow the pattern `<prefix>:<specific>`:

- `add_operation:View Virtual Machine`
- `add_operation_group:disk`
- `add_operation.with_related_operations:Create VM`
- `remove_operation:Access Console Virtual Machine`
- `save_role` (no colon — simple actions)
- `save_role_create_policy`

Variable-length prefixes. Never hardcode prefix length.

## Counting conventions

- `COUNT(*)` (Query Builder: **Count of rows**) by default
- `COUNT(DISTINCT HASHED_ACCOUNTID)` (Query Builder: **Number of distinct values of** → `Hashed Accountid`) for unique users/accounts
- `COUNT(DISTINCT SESSION_ID)` (Query Builder: **Number of distinct values of** → `Session ID`) for unique sessions
- Only use distinct counts when the question explicitly asks for unique users/accounts/sessions.
