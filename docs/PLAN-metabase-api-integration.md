# Plan: Metabase API Integration — Automated Dashboard & Widget Creation

> **Goal:** Evolve the `metabase-widget` skill from generating _instructions_ to directly _creating_ dashboards and widgets in Metabase via the REST API. Keep it flexible — let users add widgets to existing dashboards, create new dashboards from scratch, or decide interactively.

---

## Table of Contents

1. [Current State](#1-current-state)
2. [Target State](#2-target-state)
3. [Metabase API Primer](#3-metabase-api-primer)
4. [Authentication & Configuration](#4-authentication--configuration)
5. [API Endpoints Reference](#5-api-endpoints-reference)
6. [Two-Stage Workflow: Prepare → Confirm → Execute](#6-two-stage-workflow-prepare--confirm--execute)
7. [User Interaction Flows](#7-user-interaction-flows)
8. [Implementation Phases](#8-implementation-phases)
9. [Data Structures & Payloads](#9-data-structures--payloads)
10. [Error Handling & Edge Cases](#10-error-handling--edge-cases)
11. [Open Questions & Risks](#11-open-questions--risks)

---

## 1. Current State

The skill today:

- Takes a telemetry question + event payload(s) as input.
- Classifies the question, picks a tier (Query Builder or SQL), and chooses a visualization.
- Outputs a **markdown file with step-by-step instructions** the user must follow manually in the Metabase UI.
- For batch input (spreadsheet), produces one markdown file per requirement plus an index file.

**What's missing:** No programmatic interaction with Metabase. The user still has to log in, manually build each question, save it, create a dashboard, and add cards by hand.

---

## 2. Target State

The skill should operate in **two explicit stages** — a preparation stage and an execution stage — with a user-controlled gate between them.

### Stage 1: Preparation (always runs)

1. Accept requirement(s) + payload(s) (single or batch from a spreadsheet).
2. Classify each requirement, pick the tier, choose visualization, generate the query.
3. **Produce a review markdown file** — a structured table listing every widget the skill intends to build, with the recommended approach, an alternative approach, and all metadata. This file is the user's checkpoint.
4. The user reviews, edits the markdown if needed (swap approaches, change titles, drop rows, adjust filters), and **explicitly tells the skill to proceed**.

### Stage 2: Execution (only on explicit user confirmation)

5. **Create Metabase questions (cards)** directly via the API — both native SQL and MBQL (structured query) types.
6. **Create a new dashboard** and add the generated question(s) to it as cards with sensible layout, OR
7. **Add question(s) to an existing dashboard** the user specifies (by name, ID, or URL), OR
8. **Just create saved questions** — the user arranges them on dashboards themselves.
9. **Return live Metabase URLs** for every created question and dashboard.

**The skill must never call the Metabase API to create/modify resources until the user has reviewed the preparation file and explicitly confirmed execution.**

---

## 3. Metabase API Primer

Metabase exposes a REST API at `<METABASE_BASE_URL>/api/`. Every endpoint accepts and returns JSON. The API is **not versioned** — it can change between Metabase releases, but breaking changes are rare and tracked in the [API changelog](https://www.metabase.com/docs/latest/developers-guide/api-changelog).

Your hosted instance also serves **live OpenAPI docs** at `<METABASE_BASE_URL>/api/docs` — use these as the definitive reference for your version.

### Key Concepts

| Metabase concept    | API term       | What it is                                                                                 |
| ------------------- | -------------- | ------------------------------------------------------------------------------------------ |
| Question            | **Card**       | A saved query (SQL or Query Builder) plus its visualization settings                       |
| Dashboard           | **Dashboard**  | A collection of cards arranged on a 18-column grid                                         |
| Card on a dashboard | **DashCard**   | A card placed at a specific grid position on a dashboard, with optional parameter mappings |
| Collection          | **Collection** | A folder-like organizer for cards and dashboards                                           |
| Database            | **Database**   | A connected data source (Snowflake, Postgres, etc.)                                        |

---

## 4. Authentication & Configuration

### API Key Authentication

API keys are long-lived and not tied to a user session. This is the chosen authentication method for the skill.

**Setup steps:**

1. Log into your hosted Metabase as an **Admin**.
2. Go to **Admin** → **Settings** → **Authentication**.
3. Scroll down to **API Keys** and click **Manage**.
4. Click **Create API Key**.
5. Enter a descriptive name (e.g., `widget-builder-skill`).
6. Select a **group** that has permission to:
   - Read the Snowflake database (to create questions against it).
   - Write to the target collection(s) (to save questions and dashboards).
   - Create and edit dashboards.
7. Click **Create** — copy the generated key immediately (it won't be shown again).

**Usage — every API call in this skill uses this header:**

```bash
curl -H "X-API-Key: YOUR_API_KEY" https://your-metabase.example.com/api/card
```

**Security note:** Store the API key in an environment variable or a secrets manager — never commit it to the repository. Create a dedicated service-account-level key with scoped permissions rather than using a personal admin key.

### Configuration the Skill Will Need

The skill will require a configuration block (environment variables or a config file) with:

| Setting                          | Description                                                           | Example                                                    |
| -------------------------------- | --------------------------------------------------------------------- | ---------------------------------------------------------- |
| `METABASE_BASE_URL`              | Base URL of your Metabase instance (no trailing slash)                | `https://metabase.yourcompany.com`                         |
| `METABASE_API_KEY`               | API key created above                                                 | `mb_XXXXXXXXXXXXXXXX`                                      |
| `METABASE_DATABASE_ID`           | Numeric ID of the Snowflake database in Metabase                      | `2`                                                        |
| `METABASE_DEFAULT_COLLECTION_ID` | Collection ID where new questions are saved (optional, `null` = root) | `63`                                                       |
| `METABASE_DEFAULT_TABLE_NAME`    | Default table name for queries                                        | `NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT` |

**How to find your Database ID:**

```bash
curl -H "X-API-Key: YOUR_API_KEY" https://your-metabase.example.com/api/database

# Returns a list of databases; find yours by name and note the "id" field
```

**How to find your Table ID (needed for MBQL queries):**

```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  "https://your-metabase.example.com/api/database/DATABASE_ID/metadata?include_hidden=true"

# Returns all tables and their IDs; find the flat table
```

**How to find Collection IDs:**

```bash
curl -H "X-API-Key: YOUR_API_KEY" https://your-metabase.example.com/api/collection

# Returns all collections; note the "id" of your target collection
```

---

## 5. API Endpoints Reference

### Questions (Cards)

| Action                       | Method & Endpoint                    | Key Parameters                                                                               |
| ---------------------------- | ------------------------------------ | -------------------------------------------------------------------------------------------- |
| List all questions           | `GET /api/card`                      | —                                                                                            |
| Get a question               | `GET /api/card/{id}`                 | —                                                                                            |
| **Create a question**        | `POST /api/card`                     | `name`, `dataset_query`, `display`, `visualization_settings`, `collection_id`, `description` |
| Update a question            | `PUT /api/card/{id}`                 | Same as create                                                                               |
| Delete a question            | `DELETE /api/card/{id}`              | —                                                                                            |
| Run a question (get results) | `POST /api/card/{id}/query`          | —                                                                                            |
| Search questions             | `GET /api/search?q=term&models=card` | `q`, `models`                                                                                |

### Dashboards

| Action                             | Method & Endpoint                         | Key Parameters                                        |
| ---------------------------------- | ----------------------------------------- | ----------------------------------------------------- |
| List dashboards                    | `GET /api/dashboard`                      | —                                                     |
| Get a dashboard                    | `GET /api/dashboard/{id}`                 | —                                                     |
| **Create a dashboard**             | `POST /api/dashboard`                     | `name`, `description`, `collection_id`, `parameters`  |
| **Update dashboard (incl. cards)** | `PUT /api/dashboard/{id}`                 | `dashcards` (array with card positions), `parameters` |
| Add card to dashboard              | `POST /api/dashboard/{id}/cards`          | `cardId`, `row`, `col`, `size_x`, `size_y`            |
| Delete a dashboard                 | `DELETE /api/dashboard/{id}`              | —                                                     |
| Search dashboards                  | `GET /api/search?q=term&models=dashboard` | `q`, `models`                                         |

### Collections

| Action                    | Method & Endpoint                | Key Parameters                              |
| ------------------------- | -------------------------------- | ------------------------------------------- |
| List collections          | `GET /api/collection`            | —                                           |
| Create a collection       | `POST /api/collection`           | `name`, `description`, `color`, `parent_id` |
| Get items in a collection | `GET /api/collection/{id}/items` | `models` (filter by type)                   |

### Databases

| Action                                 | Method & Endpoint                       | Key Parameters   |
| -------------------------------------- | --------------------------------------- | ---------------- |
| List databases                         | `GET /api/database`                     | —                |
| Get database metadata (tables, fields) | `GET /api/database/{id}/metadata`       | `include_hidden` |
| Sync schema                            | `POST /api/database/{id}/sync_schema`   | —                |
| Re-scan field values                   | `POST /api/database/{id}/rescan_values` | —                |

### Utility

| Action              | Method & Endpoint       | Notes                                                                      |
| ------------------- | ----------------------- | -------------------------------------------------------------------------- |
| Run an ad-hoc query | `POST /api/dataset`     | Does not create a saved question; useful for testing queries before saving |
| Get current user    | `GET /api/user/current` | Verify authentication is working                                           |

---

## 6. Two-Stage Workflow: Prepare → Confirm → Execute

Every invocation of the skill — single requirement or batch — follows a strict two-stage workflow. The user has full control between stages.

### Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                        STAGE 1: PREPARATION                         │
│                                                                      │
│  User provides requirement(s) + payload(s)                           │
│       │                                                              │
│       ▼                                                              │
│  Skill classifies, picks tier, generates query, chooses chart        │
│       │                                                              │
│       ▼                                                              │
│  Skill produces: widget-review.md (editable review table)            │
│       │                                                              │
│       ▼                                                              │
│  User reviews / edits the markdown file                              │
│                                                                      │
│  ──────────────── GATE: user explicitly confirms ──────────────────  │
│                                                                      │
│  User says: "proceed", "create these in Metabase", etc.             │
│       │                                                              │
│       ▼                                                              │
│                        STAGE 2: EXECUTION                            │
│                                                                      │
│  Skill reads the (possibly edited) review file                       │
│       │                                                              │
│       ▼                                                              │
│  Skill asks: which flow? (new dashboard / existing / questions only) │
│       │                                                              │
│       ▼                                                              │
│  Skill calls Metabase API to create cards, dashboards                │
│       │                                                              │
│       ▼                                                              │
│  Skill returns live Metabase URLs + creation summary                 │
└──────────────────────────────────────────────────────────────────────┘
```

### Stage 1: Preparation — The Review Markdown File

After processing the requirement(s), the skill generates a **review file** named `widget-review.md` (or a name the user specifies) in the output folder. This file is the single source of truth for what will be created in Metabase. It contains:

1. **A summary table** — one row per requirement, with all key decisions visible at a glance.
2. **Detailed per-widget sections** — the full build instructions for each widget (recommended + alternative approaches), following the per-requirement format from `SKILL.md`.

#### Review Table Format

The summary table at the top of `widget-review.md` is the quick-scan view:

```markdown
# Widget Review — <Feature Area / Project Name>

> Generated: <timestamp> | Total: <N> requirements | Flagged: <M>

## Summary

| #   | Requirement                                            | Widget Title          | Recommended Approach                                                                                                        | Tier | Visualization          | Alternative Approach                                       | Alt Tier | Alt Visualization | Status                          |
| --- | ------------------------------------------------------ | --------------------- | --------------------------------------------------------------------------------------------------------------------------- | ---- | ---------------------- | ---------------------------------------------------------- | -------- | ----------------- | ------------------------------- |
| 1   | How often do users save roles vs save & create policy? | Save vs Save & Create | Query Builder — filter on `Destination Name is any of save_role, save_role_create_policy`, group by Destination Name, Count | T1   | Bar                    | SQL — `CASE` to label actions, `COUNT(*)` grouped          | T3       | Bar               | ✅ Ready                        |
| 2   | Which operations are added most frequently?            | Top Operations Added  | Query Builder — custom column `regexextract` to strip prefix, Count, group by cleaned name, sort desc, limit 10             | T2   | Row (≤10) / Pie (many) | SQL — `SPLIT_PART` + `GROUP BY` + `ORDER BY DESC LIMIT 10` | T3       | Row               | ✅ Ready                        |
| 3   | What is the funnel from role creation to policy save?  | Role Creation Funnel  | SQL — `UNION ALL` with per-step counts                                                                                      | T3   | Funnel                 | _(no alternative — only SQL can express this)_             | —        | —                 | ✅ Ready                        |
| 4   | How often do users toggle feature X?                   | —                     | —                                                                                                                           | —    | —                      | —                                                          | —        | —                 | ⚠️ Flagged: no payload provided |

### Column Descriptions

- **#** — Row number, matches the requirement order from the input sheet.
- **Requirement** — The original question, cleaned up for grammar.
- **Widget Title** — The short title for Metabase's "Save question" dialog.
- **Recommended Approach** — Brief description of the primary approach the skill will use.
- **Tier** — T1 (Basic Query Builder), T2 (Advanced Query Builder), or T3 (SQL).
- **Visualization** — The chart type for the recommended approach.
- **Alternative Approach** — Brief description of the fallback/alternative approach.
- **Alt Tier** — Tier of the alternative.
- **Alt Visualization** — Chart type for the alternative.
- **Status** — `✅ Ready` (will be created), `⚠️ Flagged: <reason>` (skipped unless user provides missing info), or `❌ Dropped` (user decided to remove it).
```

#### What the User Can Edit

The user can edit `widget-review.md` before confirming. Common edits:

- **Swap approaches** — Move the alternative into the recommended column (just swap the cell contents or write "use alternative" in the Status column).
- **Change titles** — Rewrite the Widget Title column.
- **Drop rows** — Change Status to `❌ Dropped` to skip a widget.
- **Resolve flagged rows** — Add the missing payload/info and change status from `⚠️ Flagged` to `✅ Ready`.
- **Adjust details** — Edit the per-widget detailed sections below the table (change filters, metrics, chart type, etc.).

The skill must **re-read** this file at the start of Stage 2 and respect all user edits.

#### Detailed Sections (Below the Table)

After the summary table, the file contains the full per-widget details — one section per `✅ Ready` row — following the per-requirement markdown format defined in `SKILL.md` (Question, Payload Context, Recommended Approach, Alternative Approaches, Assumptions & Caveats, Metabase Save Details).

```markdown
---
## Widget Details

### 1. Save vs Save & Create

(Full per-requirement details here — same format as SKILL.md output)
---

### 2. Top Operations Added

(Full per-requirement details here)

---

(…and so on for each ready widget)
```

### Stage 2: Execution — Only After Explicit Confirmation

The skill does **not** proceed to Stage 2 automatically. The user must explicitly say something like:

- "Proceed with creation"
- "Create these in Metabase"
- "Go ahead and build the widgets"
- "Execute"

**If the user never confirms, Stage 1 is still valuable** — the review file serves as documentation and can be used for manual widget creation.

When the user confirms, the skill:

1. Re-reads `widget-review.md` (the user may have edited it).
2. Filters to only `✅ Ready` rows.
3. For each ready widget, uses the **Recommended Approach** column (unless the user swapped it).
4. Asks the user which execution flow to use (see Section 7).
5. Calls the Metabase API.
6. Updates the review file with a new **Results** column showing the Metabase URL or error for each widget.

---

## 7. User Interaction Flows

After the user confirms Stage 2, the skill must support four execution flows.

### Flow 1: Create new dashboard + widgets from scratch

```
User confirms: "proceed" + "create a new dashboard"
                                           │
                ┌──────────────────────────┐│
                │ Read widget-review.md    ││
                │ Filter to ✅ Ready rows   ││
                └──────────┬───────────────┘│
                           │                │
                ┌──────────▼───────────────┐│
                │ Ask: dashboard name,     ││
                │ description, collection  ││
                └──────────┬───────────────┘│
                           │                │
                ┌──────────▼───────────────┐│
                │ POST /api/card (×N)      ││
                │ → save each question     ││
                └──────────┬───────────────┘│
                           │                │
                ┌──────────▼───────────────┐│
                │ POST /api/dashboard      ││
                │ → create the dashboard   ││
                └──────────┬───────────────┘│
                           │                │
                ┌──────────▼───────────────┐│
                │ POST /api/dashboard/     ││
                │   {id}/cards  (×N)       ││
                │ → add cards with layout  ││
                └──────────┬───────────────┘│
                           │                │
                ┌──────────▼───────────────┐
                │ Update widget-review.md  │
                │ with URLs + summary      │
                └──────────────────────────┘
```

### Flow 2: Add widgets to an existing dashboard

```
User confirms: "proceed" + "add to <dashboard name/ID/URL>"
                                           │
                ┌──────────────────────────┐│
                │ Read widget-review.md    ││
                │ Filter to ✅ Ready rows   ││
                └──────────┬───────────────┘│
                           │                │
                ┌──────────▼───────────────┐│
                │ Resolve dashboard:       ││
                │ GET /api/search or       ││
                │ GET /api/dashboard/{id}  ││
                └──────────┬───────────────┘│
                           │                │
                ┌──────────▼───────────────┐│
                │ GET existing cards to    ││
                │ compute next free grid   ││
                │ position                 ││
                └──────────┬───────────────┘│
                           │                │
                ┌──────────▼───────────────┐│
                │ POST /api/card (×N)      ││
                │ → save questions         ││
                └──────────┬───────────────┘│
                           │                │
                ┌──────────▼───────────────┐│
                │ POST /api/dashboard/     ││
                │   {id}/cards  (×N)       ││
                │ → add to existing grid   ││
                └──────────┬───────────────┘│
                           │                │
                ┌──────────▼───────────────┐
                │ Update widget-review.md  │
                │ with URLs + summary      │
                └──────────────────────────┘
```

### Flow 3: Create saved questions only (no dashboard)

```
User confirms: "proceed" + "just save the questions"
                                           │
                ┌──────────────────────────┐│
                │ Read widget-review.md    ││
                │ Filter to ✅ Ready rows   ││
                └──────────┬───────────────┘│
                           │                │
                ┌──────────▼───────────────┐│
                │ POST /api/card (×N)      ││
                │ → save each question     ││
                │ to specified collection  ││
                └──────────┬───────────────┘│
                           │                │
                ┌──────────▼───────────────┐
                │ Update widget-review.md  │
                │ with URLs + summary      │
                └──────────────────────────┘
```

### Flow 4: Generate markdown only (no API calls — current behavior)

The existing skill behavior. Stage 1 produces the review file plus the detailed per-requirement markdown files. The user never triggers Stage 2. No Metabase API interaction.

### Flow Selection

After the user confirms they want to proceed, if they haven't specified a flow, **ask them** to choose:

> You've confirmed the widget review. How would you like me to create these in Metabase?
>
> 1. **Create a new dashboard** — I'll create the questions, build a new dashboard, and arrange the widgets on it.
> 2. **Add to an existing dashboard** — Tell me the dashboard name or ID, and I'll add the new widgets to it.
> 3. **Save as questions only** — I'll create saved questions in Metabase; you can add them to dashboards yourself.

---

## 8. Implementation Phases

### Phase 1: Configuration & Connectivity (Foundation)

**Goal:** Establish authenticated communication with the Metabase API using the API Key.

- [ ] Create a `config.json` (or `.env`) schema for Metabase connection settings (API key, base URL, database ID, collection ID, table name).
- [ ] Implement a connection-test utility: `GET /api/user/current` to verify the API key works.
- [ ] Implement database/table discovery: `GET /api/database` → `GET /api/database/{id}/metadata` to auto-detect table IDs.
- [ ] Implement collection discovery: `GET /api/collection` to let the user pick where to save things.
- [ ] Document the setup steps for the user (API key creation, finding database IDs, etc.).

**Deliverable:** The skill can authenticate, list databases, list collections, and confirm connectivity.

### Phase 2: Preparation Stage — Review File Generation

**Goal:** After processing requirements, produce the `widget-review.md` file with the summary table and detailed widget sections for user review.

- [ ] Build the review-table generator: take the skill's per-requirement output (tier, query, chart, title, description, alternatives) and format it into the summary table defined in Section 6.
- [ ] Build the detailed-sections generator: append the full per-widget instructions (from `SKILL.md` output format) below the summary table.
- [ ] Handle batch input: process all rows from a spreadsheet, populate the table, flag incomplete rows with `⚠️ Flagged` status and reason.
- [ ] Handle single-requirement input: same file format, just one row in the table.
- [ ] Save the file to the output folder as `widget-review.md` (or user-specified name).
- [ ] Present an in-chat summary telling the user to review and edit the file, and to explicitly confirm when ready.
- [ ] Implement the re-read logic: when the user confirms, re-parse `widget-review.md` and respect any edits (swapped approaches, changed titles, dropped rows, resolved flags).

**Deliverable:** The skill produces a structured, editable review file and can re-read user edits to drive Stage 2.

### Phase 3: Question (Card) Creation via API

**Goal:** Programmatically create saved questions in Metabase from the confirmed review file.

- [ ] Build the `POST /api/card` payload for **Tier 3 (SQL)** questions — this is the simpler case (native query, no MBQL).
- [ ] Build the `POST /api/card` payload for **Tier 1 / Tier 2 (Query Builder)** questions — requires translating the skill's filter/summarize/group-by instructions into MBQL JSON.
- [ ] Map the skill's visualization recommendations to Metabase `display` values: `table`, `bar`, `row`, `line`, `area`, `pie`, `scalar` (number), `smartscalar` (trend), `funnel`, `scatter`, `combo`, `waterfall`, `progress`, `gauge`, `map`, `pivot`.
- [ ] Set `visualization_settings` appropriately (axis labels, sorting, formatting).
- [ ] Validate created questions with `POST /api/card/{id}/query` and confirm they return data.
- [ ] Handle errors: invalid SQL, missing table/columns, permission denied, etc.
- [ ] After creation, update `widget-review.md` with a new **Metabase URL** column showing the link to each created question (or the error message).

**Deliverable:** The skill can create saved questions in Metabase, return their URLs, and update the review file with results.

### Phase 4: Dashboard Creation & Widget Placement

**Goal:** Create dashboards and arrange widgets on them with a sensible grid layout.

- [ ] Implement `POST /api/dashboard` to create empty dashboards.
- [ ] Implement `POST /api/dashboard/{id}/cards` to add cards with grid positions.
- [ ] Build a **layout engine** that auto-arranges cards on the 18-column grid:
  - Default card size: 6 columns × 4 rows (3 cards per row).
  - Single-number / trend cards: 4 columns × 3 rows (fit more per row).
  - Full-width tables or funnels: 18 columns × 6 rows.
  - Stack cards top-to-bottom, filling rows left-to-right.
- [ ] For "add to existing dashboard," compute the next available grid position below existing cards.
- [ ] Implement dashboard-level filter parameters (e.g., date range filter) that connect to all cards.
- [ ] Return the dashboard URL: `<METABASE_BASE_URL>/dashboard/{id}`.
- [ ] Update `widget-review.md` with the dashboard URL in a header section.

**Deliverable:** The skill can create dashboards, place widgets in a readable layout, and return live URLs.

### Phase 5: Interactive Flow Selection & Polish

**Goal:** Tie everything together with a smooth user experience.

- [ ] Implement the flow selection mechanism (ask user after they confirm, or infer from their confirmation message).
- [ ] Support dashboard lookup by name (via `GET /api/search?q=name&models=dashboard`) or by Metabase URL (extract ID from URL path).
- [ ] Add collection creation: if the user wants a new collection for their questions, create it via `POST /api/collection`.
- [ ] Batch processing: for spreadsheet input, create all questions and add them to a single dashboard (or multiple dashboards grouped by page section).
- [ ] Post-creation summary: update `widget-review.md` with a results section listing every created question and dashboard with clickable Metabase URLs.
- [ ] Error recovery: if some questions fail to create, still create the dashboard with the ones that succeeded, and report failures in the review file.
- [ ] Markdown fallback: the review file always exists (Stage 1), so even if Stage 2 partially fails, the user has full documentation.

**Deliverable:** Full end-to-end two-stage workflow from requirement to live Metabase dashboard.

### Phase 6: MBQL Deep Dive (Advanced, Optional)

**Goal:** Support complex Query Builder questions via MBQL JSON (instead of only SQL).

Translating the skill's Tier 1/Tier 2 instructions into MBQL is the hardest part. MBQL is Metabase's internal JSON query language and it's not trivially documented. Strategy:

- [ ] Use browser DevTools to capture the MBQL payloads that Metabase generates when you build questions in the UI.
- [ ] Build a mapping from skill instructions (filter, summarize, group-by, custom-column expressions) to MBQL structures.
- [ ] For Tier 1: straightforward — filters and aggregations map cleanly to MBQL.
- [ ] For Tier 2: complex — custom expressions need to be translated to MBQL expression nodes.
- [ ] Fall back to SQL (Tier 3) for any MBQL translation that's too complex or error-prone.

> **Pragmatic recommendation for Phase 3:** Start by creating all questions as **native SQL** (Tier 3 payloads). Even for Tier 1/2 requirements, generate the equivalent SQL and save it as a native question. This gets the end-to-end flow working immediately. Tackle MBQL translation in Phase 6 as an optimization — MBQL questions have better drill-through in the Metabase UI, but SQL questions are fully functional.

---

## 9. Data Structures & Payloads

### Create a Native SQL Question

```json
{
  "name": "Save vs Save & Create",
  "description": "\"How often do users save their roles versus save and go to policy creation?\"\nShows whether users typically finish at Save or continue into policy creation.",
  "collection_id": 63,
  "dataset_query": {
    "database": 2,
    "type": "native",
    "native": {
      "query": "SELECT\n  CASE\n    WHEN DESTINATION_NAME = 'save_role' THEN 'Save'\n    WHEN DESTINATION_NAME = 'save_role_create_policy' THEN 'Save & Create Policy'\n  END AS ACTION_LABEL,\n  COUNT(*) AS TOTAL_CLICKS\nFROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT\nWHERE DESTINATION_NAME IN ('save_role', 'save_role_create_policy')\nGROUP BY ACTION_LABEL\nORDER BY TOTAL_CLICKS DESC",
      "template-tags": {}
    }
  },
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["ACTION_LABEL"],
    "graph.metrics": ["TOTAL_CLICKS"]
  }
}
```

### Create a Structured (MBQL) Question

```json
{
  "name": "Top Operations Added",
  "description": "\"Which operations do users add most frequently?\"\nHighlights the most-clicked operations in the add-operation workflow.",
  "collection_id": 63,
  "dataset_query": {
    "database": 2,
    "type": "query",
    "query": {
      "source-table": 42,
      "filter": ["starts-with", ["field", 101, null], "add_operation:"],
      "aggregation": [["count"]],
      "breakout": [["field", 101, null]],
      "order-by": [["desc", ["aggregation", 0]]],
      "limit": 10
    }
  },
  "display": "row",
  "visualization_settings": {}
}
```

> **Note:** Field IDs (like `101` above) are numeric and specific to your Metabase instance. They must be looked up via `GET /api/database/{id}/metadata`. The skill will need to build this mapping during Phase 1.

### Create a Dashboard

```json
{
  "name": "Role Management — Telemetry Dashboard",
  "description": "Telemetry widgets for the Role Management feature area.",
  "collection_id": 63,
  "parameters": [
    {
      "name": "Date Range",
      "slug": "date_range",
      "id": "abc123",
      "type": "date/range"
    }
  ]
}
```

### Add a Card to a Dashboard

```json
{
  "cardId": 456,
  "row": 0,
  "col": 0,
  "size_x": 6,
  "size_y": 4,
  "parameter_mappings": [
    {
      "parameter_id": "abc123",
      "card_id": 456,
      "target": ["dimension", ["field", 200, null]]
    }
  ]
}
```

### Dashboard Grid Layout Model

Metabase uses an **18-column grid**. Cards are placed with `(col, row)` as the top-left origin and `(size_x, size_y)` for dimensions.

```
col:  0  1  2  3  4  5  6  7  8  9  10 11 12 13 14 15 16 17
     ┌────────────────┐┌────────────────┐┌────────────────┐
row 0│  Card A (6×4)  ││  Card B (6×4)  ││  Card C (6×4)  │
     │                ││                ││                │
     │                ││                ││                │
     └────────────────┘└────────────────┘└────────────────┘
     ┌─────────────────────────────────────────────────────┐
row 4│              Card D (18×6, full-width table)        │
     │                                                     │
     │                                                     │
     │                                                     │
     │                                                     │
     └─────────────────────────────────────────────────────┘
```

Default sizing heuristic:

| Widget type              | `size_x` | `size_y` | Cards per row |
| ------------------------ | -------- | -------- | ------------- |
| Number / Trend / Gauge   | 4        | 3        | 4             |
| Bar / Row / Line / Pie   | 6        | 4        | 3             |
| Funnel / Combo / Stacked | 9        | 5        | 2             |
| Table / Pivot            | 18       | 6        | 1             |

### Display Type Mapping

Map skill chart recommendations to Metabase API `display` values:

| Skill recommendation         | API `display` value                                              |
| ---------------------------- | ---------------------------------------------------------------- |
| Number (single scalar)       | `scalar`                                                         |
| Trend (with previous period) | `smartscalar`                                                    |
| Bar (vertical)               | `bar`                                                            |
| Row (horizontal bar)         | `row`                                                            |
| Line                         | `line`                                                           |
| Area                         | `area`                                                           |
| Stacked bar                  | `bar` (with `stackable.stack_type` in `visualization_settings`)  |
| Stacked area                 | `area` (with `stackable.stack_type` in `visualization_settings`) |
| 100% stacked bar             | `bar` (with `stackable.stack_type: "normalized"`)                |
| Pie / Donut                  | `pie`                                                            |
| Funnel                       | `funnel`                                                         |
| Combo (dual y-axis)          | `combo`                                                          |
| Scatter                      | `scatter`                                                        |
| Waterfall                    | `waterfall`                                                      |
| Table                        | `table`                                                          |
| Pivot table                  | `pivot`                                                          |
| Progress bar                 | `progress`                                                       |
| Gauge                        | `gauge`                                                          |
| Pin map                      | `map`                                                            |
| Region map (choropleth)      | `map`                                                            |

---

## 10. Error Handling & Edge Cases

| Scenario                                                 | How to handle                                                                                          |
| -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| API key invalid / expired                                | Fail fast with a clear message; link to the API key creation steps                                     |
| Database ID wrong                                        | Offer to run `GET /api/database` and let the user pick                                                 |
| Table not found                                          | Suggest running schema sync: `POST /api/database/{id}/sync_schema`                                     |
| SQL syntax error on card creation                        | Return the Metabase error message; offer to fix the SQL and retry                                      |
| Card creation succeeds but query returns no data         | Warn the user; suggest checking filters and running the diagnostic SQL                                 |
| Dashboard name already exists                            | Ask: overwrite, rename, or add to existing?                                                            |
| Permission denied (collection/database)                  | Explain which permission is missing and link to Admin → Permissions                                    |
| Rate limiting                                            | Unlikely for small batches, but add a 200ms delay between API calls for batches of 20+                 |
| Partial batch failure                                    | Create what you can; list failures with reasons in the review file; offer retry for failed ones        |
| User edits review file with broken markdown table syntax | Parse gracefully; report malformed rows with line numbers; refuse to proceed until fixed               |
| User never confirms Stage 2                              | That's fine — the review file from Stage 1 is still useful as documentation for manual widget creation |
| User confirms but review file has no `✅ Ready` rows     | Warn that there's nothing to create; ask if they want to re-edit                                       |
| User swaps to an alternative that's a different tier     | Re-read the detailed section for that widget; use the alternative's query/approach for card creation   |

---

## 11. Open Questions & Risks

| #   | Question                                 | Notes                                                                                                                                                                                                                                                               |
| --- | ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | **Which Metabase version is deployed?**  | API payloads differ slightly across versions. The `PUT /api/dashboard/:id/cards` endpoint was deprecated in v0.48; use `PUT /api/dashboard/:id` for newer versions. Check your version at `GET /api/session/properties` → `version.tag`.                            |
| 2   | **MBQL vs SQL-only?**                    | Starting with SQL-only (Phase 3) is pragmatic. MBQL gives better drill-through and lets non-SQL users edit questions. Worth investing in Phase 6 if the team values this.                                                                                           |
| 3   | **Template tags for dashboard filters?** | Native SQL questions need `template-tags` to participate in dashboard filter widgets. Structured (MBQL) questions get this for free. If dashboard-level date filters are important, SQL questions need filter variable syntax: `WHERE TIMESTAMP >= {{start_date}}`. |
| 4   | **Who owns the API key?**                | The API key's permissions determine what the skill can do. Create a dedicated service account with scoped permissions rather than using a personal admin key.                                                                                                       |
| 5   | **Idempotency**                          | Running the skill twice with the same input will create duplicate questions/dashboards. Consider adding a name-based check: search for existing questions with the same title in the target collection before creating a new one.                                   |
| 6   | **Metabase API stability**               | The API is unversioned. Pin your implementation to the current Metabase version and monitor the [API changelog](https://www.metabase.com/docs/latest/developers-guide/api-changelog) before upgrades.                                                               |
| 7   | **Field ID discovery**                   | MBQL queries reference fields by numeric ID, not name. The skill needs a one-time metadata fetch to build a field-name → field-ID mapping. Cache this and refresh on schema sync.                                                                                   |
| 8   | **Review file format stability**         | The skill must parse user-edited markdown reliably. If users break the table syntax, the skill should fail gracefully with a clear error pointing to the malformed row, not silently skip widgets.                                                                  |

---

## Quick-Start Checklist

Once you're ready to start implementing, do these steps first:

1. **Get your Metabase instance URL** — e.g. `https://metabase.yourcompany.com`
2. **Create an API key** — Admin → Settings → Authentication → API Keys → Create
3. **Test connectivity:**
   ```bash
   curl -H "X-API-Key: YOUR_KEY" https://your-metabase.example.com/api/user/current
   ```
4. **Find your database ID:**
   ```bash
   curl -H "X-API-Key: YOUR_KEY" https://your-metabase.example.com/api/database
   ```
5. **Find your table ID (for MBQL):**
   ```bash
   curl -H "X-API-Key: YOUR_KEY" \
     "https://your-metabase.example.com/api/database/DATABASE_ID/metadata" | \
     python3 -c "import sys,json; [print(t['id'],t['name']) for t in json.load(sys.stdin)['tables']]"
   ```
6. **Find your collection ID (optional):**
   ```bash
   curl -H "X-API-Key: YOUR_KEY" https://your-metabase.example.com/api/collection
   ```
7. **Open `<METABASE_BASE_URL>/api/docs`** in your browser to explore the live API docs for your specific version.
