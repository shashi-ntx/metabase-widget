# Metabase REST API Integration

Read this at the start of Stage 2. It covers authentication, configuration, every endpoint the skill uses, the exact payload shapes, and how to handle errors.

The skill talks to Metabase through `scripts/metabase_api.py`. This document explains what the script does so you can debug or extend it; prefer running the script over crafting `curl` calls by hand.

## Setup checklist

Before Stage 2 will work the user needs:

1. **A Metabase instance URL** — e.g. `https://metabase.yourcompany.com` (no trailing slash).
2. **An API key:**
   - Admin → Settings → Authentication → **API Keys** → **Manage** → **Create API Key**.
   - Give it a descriptive name (`widget-builder-skill`).
   - Assign a group with permissions to (a) read the target database and (b) write to the target collection. A dedicated service-account-level key is strongly preferred over a personal admin key.
   - Copy the key immediately — it is shown only once.
3. **The database ID** of the data source the queries run against. Find it with `python scripts/metabase_api.py list-databases` (or `GET /api/database`).
4. **The collection ID** where cards and dashboards should be saved. Find with `list-collections` (or `GET /api/collection`). Optional — omit to save to the user's personal root.
5. **The table name** for SQL queries (defaults to `NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT`).

## Configuration

The skill reads configuration from environment variables, falling back to a local `.env` file if one is present in the working directory. Copy `.env.example` to `.env` and fill it in.

| Variable                         | Required | Default                                                    | Notes                                                            |
| -------------------------------- | -------- | ---------------------------------------------------------- | ---------------------------------------------------------------- |
| `METABASE_BASE_URL`              | yes      | —                                                          | No trailing slash. Used as the prefix for all API calls and URLs |
| `METABASE_API_KEY`               | yes      | —                                                          | Sent as `X-API-Key` header on every request                      |
| `METABASE_DATABASE_ID`           | yes      | —                                                          | Numeric ID; used as `database` in `dataset_query`                |
| `METABASE_DEFAULT_COLLECTION_ID` | no       | `null` (personal root)                                     | Numeric ID                                                       |
| `METABASE_DEFAULT_TABLE_NAME`    | no       | `NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT` | Used only for default SQL templates                              |

Never commit `.env` or any file containing the API key. `.env` should be `.gitignore`d.

## Connectivity check

Always run this first in Stage 2:

```bash
python scripts/metabase_api.py check
```

It calls `GET /api/user/current` and `GET /api/database/$METABASE_DATABASE_ID`. If either fails the script exits non-zero with a clear message and a suggested fix.

## Endpoints used by the skill

The skill only uses a small subset of the Metabase API. Other endpoints exist; do not call them from this skill without first updating this document and the helper script.

### Auth / identity

| Purpose        | Method | Endpoint            | Used for           |
| -------------- | ------ | ------------------- | ------------------ |
| Verify API key | GET    | `/api/user/current` | Connectivity check |

### Discovery

| Purpose                                | Method | Endpoint                                                   | Used for                                    |
| -------------------------------------- | ------ | ---------------------------------------------------------- | ------------------------------------------- |
| List databases                         | GET    | `/api/database`                                            | Resolve `METABASE_DATABASE_ID`              |
| Get database metadata (tables, fields) | GET    | `/api/database/{id}/metadata?include_hidden=true`          | (Optional) build field-ID map               |
| List collections                       | GET    | `/api/collection`                                          | Resolve `METABASE_DEFAULT_COLLECTION_ID`    |
| Search dashboards / cards              | GET    | `/api/search?q=<term>&models=dashboard` (or `models=card`) | Resolve "add to existing dashboard" by name |

### Create / read questions (cards)

| Purpose       | Method | Endpoint               |
| ------------- | ------ | ---------------------- |
| Create a card | POST   | `/api/card`            |
| Get a card    | GET    | `/api/card/{id}`       |
| Run a card    | POST   | `/api/card/{id}/query` |

### Create / update dashboards

| Purpose                        | Method | Endpoint                    | Notes                                                                                               |
| ------------------------------ | ------ | --------------------------- | --------------------------------------------------------------------------------------------------- |
| Create a dashboard             | POST   | `/api/dashboard`            | Returns the new dashboard with an empty `dashcards` array                                           |
| Get a dashboard                | GET    | `/api/dashboard/{id}`       | Read existing `dashcards` to compute next free grid position when adding to an existing dashboard   |
| Update dashboard (incl. cards) | PUT    | `/api/dashboard/{id}`       | Modern (v0.48+) way to attach cards. Pass the full `dashcards` array with positions. **Preferred.** |
| Add card to dashboard (legacy) | POST   | `/api/dashboard/{id}/cards` | Pre-v0.48 single-card add. Skill uses `PUT /api/dashboard/{id}` instead.                            |

## Payloads

### Create a native SQL card (dashboard-scoped)

Cards are saved **inside the dashboard** using the `dashboard_id` parameter (Metabase v0.51+). This prevents cards from appearing as standalone items in the collection, keeping the landing page clean.

`POST /api/card` body:

```json
{
  "name": "Save vs Save & Create",
  "description": "\"How often do users save their roles versus save and go to policy creation?\"\nShows whether users typically finish at Save or continue into policy creation.",
  "dashboard_id": 14,
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["ACTION_LABEL"],
    "graph.metrics": ["TOTAL_CLICKS"]
  },
  "dataset_query": {
    "database": 2,
    "type": "native",
    "native": {
      "query": "SELECT\n  CASE\n    WHEN DESTINATION_NAME = 'save_role' THEN 'Save'\n    WHEN DESTINATION_NAME = 'save_role_create_policy' THEN 'Save & Create Policy'\n  END AS ACTION_LABEL,\n  COUNT(*) AS TOTAL_CLICKS\nFROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT\nWHERE DESTINATION_NAME IN ('save_role', 'save_role_create_policy')\nGROUP BY ACTION_LABEL\nORDER BY TOTAL_CLICKS DESC",
      "template-tags": {}
    }
  }
}
```

**Key point:** Pass `"dashboard_id"` (not `"collection_id"`) when creating cards. The dashboard itself is created with `collection_id`; cards inherit their scope from the dashboard. Cards with `dashboard_id` set are invisible in collection listings and only appear when viewing the dashboard.

**Fallback (pre-v0.51):** If the Metabase instance does not support `dashboard_id`, fall back to `"collection_id"` on the card. Cards will then appear as standalone items in the collection alongside the dashboard.

Response (truncated):

```json
{
  "id": 123,
  "name": "Save vs Save & Create",
  "dashboard_id": 14,
  ...
}
```

Card URL for the user: `${METABASE_BASE_URL}/question/${id}`.

### Tier 1 / Tier 2 → SQL fallback

Metabase questions built in the Query Builder use MBQL (a JSON query language) which references columns by numeric **field ID**, not name. Field IDs are instance-specific and require a metadata fetch per database. Translating arbitrary Query Builder steps (filters, custom columns, summarize, breakouts, sort, limit) into MBQL is error-prone.

**Pragmatic default:** the skill creates **every** card as a native SQL question (`type: "native"`), even for Tier 1 and Tier 2 widgets. The Query Builder instructions remain in `widget-review.md` so the user can rebuild the question visually if they want; the saved card is functionally identical.

The SQL used for the API call lives in the `**SQL equivalent (used for Stage 2 API creation):**` code block at the bottom of each Tier 1/2 detailed section in `widget-review.md`. Stage 1 must always populate this block; if it can't, flag the row.

### Create a dashboard

`POST /api/dashboard` body:

```json
{
  "name": "Role Management — Telemetry Dashboard",
  "description": "Telemetry widgets for the Role Management feature area.",
  "collection_id": 63,
  "parameters": []
}
```

Returns the dashboard object with `id` and an empty `dashcards` array.

Dashboard URL: `${METABASE_BASE_URL}/dashboard/${id}`.

### Add cards to a dashboard (preferred: PUT)

The modern endpoint takes the full `dashcards` array:

`PUT /api/dashboard/{id}` body:

```json
{
  "dashcards": [
    {
      "id": -1,
      "card_id": 123,
      "row": 0,
      "col": 0,
      "size_x": 6,
      "size_y": 4,
      "parameter_mappings": [],
      "visualization_settings": {}
    },
    {
      "id": -2,
      "card_id": 124,
      "row": 0,
      "col": 6,
      "size_x": 6,
      "size_y": 4,
      "parameter_mappings": [],
      "visualization_settings": {}
    }
  ]
}
```

Rules:

- `id` must be a **negative integer** for new dashcards (Metabase assigns a real positive ID on save). Use `-1`, `-2`, … in array order.
- When **adding to an existing dashboard**, first `GET /api/dashboard/{id}` to read its current `dashcards` array, then PUT back the union: existing dashcards (with their real positive `id`s) plus the new ones (with negative `id`s).
- `col` ranges 0–23 (the grid is 24 columns wide). `row` is unbounded.
- See `dashboard-layout.md` for sizing heuristics and the auto-layout algorithm.

## Visualization settings cheat sheet

The skill must set `visualization_settings` for charts that need explicit dimension/metric assignments. Empty `{}` is fine for `table`, `scalar`, `funnel`, `pie`.

| Display        | Required `visualization_settings` keys                                            |
| -------------- | --------------------------------------------------------------------------------- |
| `bar`, `row`   | `graph.dimensions: ["<x_column>"]`, `graph.metrics: ["<y_column>"]`               |
| `line`, `area` | `graph.dimensions: ["<time_column>"]`, `graph.metrics: ["<y_column>"]`            |
| `combo`        | `graph.dimensions: [...]`, `graph.metrics: [...]`, `graph.series_settings`        |
| `stacked bar`  | `graph.dimensions`, `graph.metrics`, `stackable.stack_type: "stacked"`            |
| `100% stacked` | `graph.dimensions`, `graph.metrics`, `stackable.stack_type: "normalized"`         |
| `pie`          | `pie.dimension: "<category_column>"`, `pie.metric: "<value_column>"` (optional)   |
| `scalar`       | `{}` (Metabase uses the first numeric column)                                     |
| `smartscalar`  | `scalar.field: "<column>"` plus a date column in the query                        |
| `funnel`       | `funnel.dimension: "<step_column>"`, `funnel.metric: "<count_column>"` (optional) |
| `progress`     | `progress.goal: <number>`                                                         |
| `gauge`        | `gauge.segments: [{min, max, color}, ...]`                                        |
| `table`        | `{}` (or `table.columns` for explicit ordering)                                   |

Column names in `visualization_settings` are the **uppercase aliases** from the SQL query (e.g. `TOTAL_CLICKS`, `ACTION_LABEL`) — i.e. the names that appear in query results.

## Display value mapping

Map the chart recommendation from `widget-review.md` to the Metabase `display` value:

| Chart in review file    | API `display`                                |
| ----------------------- | -------------------------------------------- |
| Number (single scalar)  | `scalar`                                     |
| Trend                   | `smartscalar`                                |
| Bar (vertical)          | `bar`                                        |
| Row (horizontal bar)    | `row`                                        |
| Line                    | `line`                                       |
| Area                    | `area`                                       |
| Stacked bar             | `bar` + `stackable.stack_type: "stacked"`    |
| 100% stacked bar        | `bar` + `stackable.stack_type: "normalized"` |
| Pie / Donut             | `pie`                                        |
| Funnel                  | `funnel`                                     |
| Combo                   | `combo`                                      |
| Scatter                 | `scatter`                                    |
| Waterfall               | `waterfall`                                  |
| Table                   | `table`                                      |
| Pivot                   | `pivot`                                      |
| Progress bar            | `progress`                                   |
| Gauge                   | `gauge`                                      |
| Pin / region / grid map | `map`                                        |

## Error handling

The script translates HTTP errors into actionable messages. Recognised error shapes:

| HTTP / response                                 | Meaning                               | Skill action                                                                                              |
| ----------------------------------------------- | ------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| 401 / `Unauthenticated`                         | API key invalid or expired            | Stop. Tell the user to re-create the key (Admin → Settings → Authentication → API Keys)                   |
| 403 / `You don't have permissions...`           | Group missing read/write permission   | Stop for that resource. Tell the user which collection/database is denied and link to Admin → Permissions |
| 404 (database / collection / dashboard)         | ID is wrong                           | Suggest running the relevant `list-*` discovery command                                                   |
| 400 with `"errors": { "dataset_query": ... }`   | Invalid SQL (Snowflake compile error) | Record the error against that widget in `results.json`. Continue with the next widget.                    |
| 400 / `An object with that name already exists` | Duplicate dashboard or card name      | Ask the user: overwrite, rename, or skip? Default is rename with a numeric suffix.                        |
| 500                                             | Metabase internal error               | Retry once after 2s. If still failing, record the error and continue.                                     |
| Network timeout                                 | Slow Metabase                         | Retry once with a 30s timeout. If still failing, record and continue.                                     |

**Batch behaviour**: a single card failure must never abort the whole batch. Record the failure in `results.json`, continue with the remaining widgets, and surface every failure in chat + in the `## Results` section of `widget-review.md`.

**Rate limiting**: unlikely for batches under 50, but add a 200 ms sleep between card creations for larger batches.

**Idempotency**: by default the skill does **not** check for existing cards/dashboards with the same name — running Stage 2 twice will create duplicates. If the user asks for idempotency, search by name first (`GET /api/search?q=<name>&models=card`) and skip-or-update existing matches.

## Reference

- Metabase API changelog: <https://www.metabase.com/docs/latest/developers-guide/api-changelog>
- Live API docs for the user's instance: `${METABASE_BASE_URL}/api/docs`
