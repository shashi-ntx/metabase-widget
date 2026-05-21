---
name: metabase-widget
description: Build Metabase widgets from telemetry questions and event payloads — one at a time or in batch from a spreadsheet. Operates in two stages: (1) prepares a reviewable `widget-review.md` with step-by-step Query Builder instructions or SQL plus suggested chart, title, and description; (2) on explicit user confirmation, creates the questions and dashboards directly in Metabase via the REST API and returns live URLs. Use when the user wants to create a Metabase question, widget, card, chart, or dashboard tile from telemetry data — even if they just paste an event payload and ask "how do I visualize this", hand over a CSV/Excel/Google Sheet of telemetry requirements, or ask to push widgets into an existing dashboard.
---

# Metabase Widget Builder

Given a telemetry question and the event data that answers it, produce the simplest Metabase widget that works. Always try the visual Query Builder first; fall back to SQL only when the builder genuinely can't express the logic.

This skill operates in **two stages** with a hard user-controlled gate between them:

1. **Stage 1 — Preparation.** Always runs. Classifies each requirement, picks the tier, chooses a visualization, generates the query, and writes a single `widget-review.md` file. **No Metabase API calls happen here.**
2. **Stage 2 — Execution.** Only runs after the user explicitly confirms (e.g. "proceed", "create these in Metabase"). Re-reads `widget-review.md` (respecting any edits) and creates the questions/dashboard via the Metabase REST API, then writes live URLs back into the same file.

**Never call the Metabase API to create or modify anything until the user has reviewed `widget-review.md` and explicitly confirmed execution.**

## Classify the question first

Before picking filters or charts, map the question to a type. This drives the metric and visualization.

| Type            | Signals in the question                | Default metric         |
| --------------- | -------------------------------------- | ---------------------- |
| Adoption        | "how many users", "who uses"           | Distinct users         |
| Frequency       | "how often", "how many times"          | Count of events        |
| Comparison      | "X vs Y", "which is used more"         | Count, grouped         |
| Ranking         | "most used", "top", "commonly"         | Count, sorted desc     |
| Flow / Friction | "drop off", "funnel", "where do users" | Sessions / SQL funnel  |
| Trend           | "over time", "changed", "growing"      | Count, grouped by time |

See `references/query-patterns.md` § "Metric selection" for the full heuristic on choosing between event counts, distinct users, and sessions.

## Make the widget human-readable, not raw telemetry

The widget is for someone trying to answer a product question, not someone debugging telemetry plumbing. **Never ship raw event payloads as the final output.** Apply at least the cleaning below before declaring the widget done — even if the user didn't explicitly ask:

- **Strip event-name prefixes.** Show `View Virtual Machine`, not `add_operation:View Virtual Machine`. Use `regexextract([Destination Name], "[^:]+$")` in the Query Builder or `SPLIT_PART(DESTINATION_NAME, ':', 2)` in SQL.
- **Replace snake_case with readable text.** Show `Save Role`, not `save_role`. In SQL: `INITCAP(REPLACE(col, '_', ' '))`. The Query Builder can't do this in one expression — if the user needs title-casing, escalate to SQL.
- **Disambiguate near-duplicate events with a label, not a raw value.** If `add_operation_group:disk` and `add_operation:disk` collapse to the same operation name after prefix stripping, append a clarifier like `disk (Group)` rather than leaving the prefix in.
- **Use friendly axis/series labels.** A `CASE` that maps `save_role` → `Save Role` and `save_role_create_policy` → `Save & Create Policy` belongs in the query, not in the user's head. Aliases like `AS ACTION_LABEL` / `AS TOTAL_CLICKS` (or column renames in the Query Builder) should be plain English, not the DB name.
- **Pick a visualization that fits the question.** A two-row "X vs Y" comparison is a bar chart, not a table dump. A time series is a line or trend chart. A top-N by category is a horizontal bar chart sorted descending. Always state which visualization to pick in the output, with one sentence on why. **For anything beyond the obvious cases (single number, simple bar, simple line), read `references/chart-selection.md` before deciding** — it covers funnels, combo charts, stacked vs. 100%-stacked, trend vs. line, pie vs. bar thresholds, when a table actually is the right answer, and common anti-patterns.
- **Guarantee expected categories appear.** If the question is "X vs Y" and one of them has zero events, the widget must still show that category with `0`. `GROUP BY` silently drops empty categories — in SQL, build a `labels` CTE with `UNION ALL` of all expected labels + `LEFT JOIN` to the counts + `COALESCE(count, 0)`.
- **Give conditional chart recommendations when result cardinality is unknown.** The agent usually can't predict how many rows a `GROUP BY` will return. A horizontal bar chart that works for 5 categories is unreadable at 50. When cardinality is uncertain, give two recommendations: one for a small result set (≤ 15 rows) and one for a large result set (> 15 rows). See `references/chart-selection.md` § "Result cardinality affects chart choice" for the full decision table and output format.

Apply these by default. If raw values genuinely answer the question better (e.g. exploring unknown event names during discovery), say so explicitly and confirm with the user before producing the final widget.

## Always propose a title and description

Every widget — Tier 1, Tier 2, or Tier 3 — must come with a suggested **title** and **description** that the user can paste into Metabase's "Save question" dialog (or that the skill will use directly when creating the card via API). Treat these as part of the deliverable, not a nice-to-have.

**Title** (goes into the _Name_ field):

- Short, declarative, **noun phrase** — not a question. `Related-Op Adds by Op`, not "How often do users add operations that have related operations?".
- Title Case, **max ~40 characters** — aim for 3–5 words. Cut filler words (`of`, `the`, `for`, `that are`). Abbreviate where unambiguous (`Op` for Operation, `Accts` for Accounts).
- Lead with the metric or subject, then the breakdown: `<Metric> by <Dim>`, `<Metric> over Time`, `<Action> Funnel`, `Top N <Things>`.
- Use the same clean labels the chart uses — strip prefixes, de-snake_case, expand abbreviations. No raw event names (`save_role`) or DB column names (`DESTINATION_NAME`) in the title.
- **Include the metric type when ambiguous.** If a number could be read as users or events, append a short parenthetical: `Search Adoption (Users)`, `Alert Clicks (Events)`. Skip it when the title already makes the unit obvious (e.g. `Top Pages` clearly implies a count).

**Description** (goes into the _Description_ field):

Keep it tight — two lines, nothing more:

1. **The corrected, formatted question** on the first line — rewrite the user's question into a single clean sentence with proper grammar, capitalisation, and a trailing question mark. Keep the intent intact; don't paraphrase. Wrap it in quotes.
2. **One short sentence** on what the widget helps the viewer understand — the insight, not the mechanics.

Do **not** include: which events/columns are counted, filter scope or date ranges, how dashboard filters interact, or implementation details of any kind.

**When proposing multiple widgets**, every widget gets its **own** title and description. Don't share a single title/description across widgets — each widget is a separate saved question in Metabase.

**Example.** User's raw question: `how often do users save their roles vs save and go to policy creation`

- **Title:** `Save vs Save & Create`
- **Description:**
  > "How often do users save their roles versus save and go to policy creation?"
  >
  > Shows whether users typically finish at Save or continue into policy creation.

## Input format

### Single question

The user provides:

1. **A question** — what they want to learn from telemetry ("Do people add individual or group operations?")
2. **Event payloads** — one or more JSON-ish telemetry event samples showing the relevant fields

If payloads are missing or ambiguous, **stop and ask** for clarification before building the widget. If the user can't provide more detail after being asked, note the assumption explicitly in the output and proceed — but never silently guess which events or fields to use.

### Batch input (spreadsheet)

The user provides a spreadsheet (CSV, Excel, or Google Sheet) containing multiple requirements. Don't assume fixed column names — **infer the schema** from the header row. Common columns include:

- Page section / feature area
- Sub-page section
- The telemetry question
- UI elements to track (often empty — treat as optional context)
- Event payload(s) or telemetry data

Read the first few rows to identify which column serves which role. If the mapping is genuinely ambiguous, ask the user once to confirm column roles before processing.

**Batch processing rules:**

- Process every row through the same skill logic (classify → tier → build widget → title/description).
- **Don't stop on each ambiguous row.** Collect all incomplete or unclear rows, note what's missing in the output doc, and proceed with the rest. Surface the full list of skipped/flagged rows in both the output doc and the in-chat summary.
- Rows with the same page section / feature area are grouped together in the output.
- If multiple rows share identical payloads but ask different questions, each still gets its own widget proposal.

## Decision hierarchy

Try approaches in this order. Stop at the first one that works.

### Tier 1 — Basic Query Builder

Use only built-in filters and built-in Summarize metrics (Count of rows, Sum of, Average of, Distinct values of, Min, Max, etc.) with one or more grouping columns. Sort and Row limit are also fair game. No custom columns, no custom expressions.

**Can handle:**

- Single filtered count
- Counts over time (group by timestamp)
- Comparing values in the same column (multi-value filter + group by)
- Top-N by a single dimension

### Tier 2 — Advanced Query Builder

Same visual builder, but with custom columns, custom filters, or custom summaries.

**Can handle:**

- Stripping prefixes from event names (`regexextract`, `splitPart`)
- Labeling/bucketing rows (`case`/`if`)
- OR conditions across filters
- Conditional counting (`CountIf`, `SumIf`, `Share`)
- Period-over-period comparisons (`Offset`)
- Derived metrics (arithmetic on columns)

**When to use:** the question requires string manipulation, conditional logic, or aggregation expressions that basic filters/summarize can't express.

### Tier 3 — SQL

Write Snowflake-compatible SQL for use as a native Metabase question.

**When to use:**

- Funnel analysis (multiple steps with different filter sets → `UNION ALL`)
- Time-between-events (pairing start/end events via `SESSION_ID` + `TIMESTAMPDIFF`)
- Self-joins, window functions beyond `Offset`, or CTEs
- Title-casing, `REPLACE`, `INITCAP` — string operations the expression editor lacks
- Guaranteed-zero rows for missing categories (`labels` CTE + `LEFT JOIN`)

> **Pragmatic note for API execution (Stage 2):** even when a widget is authored as Tier 1 or Tier 2 in the Query Builder, the skill creates the corresponding card as a **native SQL question** by default — this avoids fragile MBQL field-ID translation. The Query Builder instructions remain in `widget-review.md` so the user can rebuild the question visually if they prefer. See `references/api-integration.md` § "Tier 1/2 → SQL fallback".

## Stage 1 — Preparation: produce `widget-review.md`

After processing the requirement(s), write **one** file: `widget-review.md` in the output folder (default: `metabase-widget-suggestions/`, or a path the user specifies). This is the single source of truth for what will be created in Metabase.

The file contains:

1. A **summary table** — one row per requirement, with the recommended approach, alternative, tier, visualization, and status.
2. **Detailed per-widget sections** — full build instructions for each `✅ Ready` widget (Question, Payload Context, Recommended Approach, Alternative(s), Assumptions & Caveats, Metabase Save Details).

The exact format, parsing rules, and what the user can edit are defined in `references/review-file-format.md`. **Read that reference whenever generating or re-reading the review file.**

After writing `widget-review.md`, **stop and tell the user**:

- That the review file is ready at `<path>`.
- That they should open it, review the recommended approaches, swap alternatives or edit details if needed, mark rows `❌ Dropped` to skip them, and resolve any `⚠️ Flagged` rows.
- That when they're happy with the file, they should explicitly tell the skill to proceed (e.g. "proceed", "create these in Metabase", "execute"). Until then, **do not** call the Metabase API.

If the user only ever wants markdown (the original behavior of this skill), Stage 1 alone is the deliverable — never push toward Stage 2.

### Per-requirement markdown files (opt-in only)

By default, **do not** generate one markdown file per requirement. `widget-review.md` is the single deliverable.

Only generate per-requirement files when the user explicitly asks for them. Triggers include phrases like:

- "also generate individual files" / "one file per widget" / "split into separate files"
- "create per-requirement markdown" / "give me a file for each row"
- "generate the markdown files too"

When the user opts in, write the files under an `output/` subfolder inside the chosen output directory (default: `metabase-widget-suggestions/output/`). One file per requirement row, **regardless of status** — Ready, Flagged, and Dropped rows all get a file so the user has a complete record.

**File naming convention** — every filename starts with the requirement row number (zero-padded to two digits) so files sort in input order:

| Row status               | Filename format                            | Example                             |
| ------------------------ | ------------------------------------------ | ----------------------------------- |
| `✅ Ready`               | `<NN>-<slug-of-widget-title>.md`           | `01-save-vs-save-and-create.md`     |
| `⚠️ Flagged: no payload` | `<NN>-no-payload-<slug-of-requirement>.md` | `04-no-payload-toggle-feature-x.md` |
| `⚠️ Flagged: <reason>`   | `<NN>-flagged-<short-reason>-<slug>.md`    | `07-flagged-ambiguous-events-...md` |
| `❌ Dropped`             | `<NN>-dropped-<slug>.md`                   | `09-dropped-old-metric.md`          |

Rules:

- **Two-digit zero-padded row number** (`01`, `02`, …, `42`). If there are more than 99 requirements, pad to three digits.
- **Slug** is lowercase, hyphen-separated, ASCII only — strip punctuation, collapse whitespace to single hyphens, max ~50 chars.
- **"no payload"** is the canonical marker when the user didn't provide a telemetry payload for that requirement — encode it in the filename so the gap is visible at a glance in the file list. Use the requirement text (not a widget title — there is none) for the slug.
- For other flag reasons (ambiguous events, missing column, etc.), use `flagged-<2-3-word-reason>` and slug the requirement text.

**File contents:**

- `✅ Ready` rows: the same per-widget detailed section from `widget-review.md` (Question, Payload Context, Recommended Approach, Alternative(s), Assumptions & Caveats, Metabase Save Details).
- `⚠️ Flagged` rows: the original requirement, the reason it was flagged, and a "What's needed to unblock" section telling the user exactly what to provide.
- `❌ Dropped` rows: the original requirement and a one-line note that it was dropped (useful as documentation that the requirement was considered).

**Index file:** when per-requirement files are generated, also write `output/_index.md` listing every file grouped by page section / feature area, with a separate "Flagged / Skipped" section at the bottom. See `references/review-file-format.md` § "Per-requirement files (opt-in)" for the exact index template.

`widget-review.md` is **still generated** even when per-requirement files are requested — the two outputs are complementary, not alternatives. Stage 2 always reads from `widget-review.md`, never from the per-requirement files.

## Stage 2 — Execution: create in Metabase

Only enter Stage 2 when the user explicitly confirms. Triggers include:

- "Proceed" / "Proceed with creation"
- "Create these in Metabase"
- "Go ahead and build the widgets"
- "Execute"

When the user confirms:

1. **Verify configuration.** Read environment variables / `.env` (see `references/api-integration.md` § "Configuration"). Run a connectivity check: `GET /api/user/current`. If anything is missing or fails, stop and tell the user exactly what to fix.
2. **Re-read `widget-review.md`.** The user may have edited it. Respect every edit: dropped rows are skipped; swapped approaches use the alternative; edited titles/descriptions/queries are used as-is. Use `scripts/widget_review.py parse` to extract the structured widget list — never re-derive the widget list from the original requirement input.
3. **Ask which execution flow** the user wants (unless they already said in the confirmation message). See `references/execution-flows.md` for the four supported flows and their decision logic.
4. **Create the cards** via `POST /api/card`. Use the helper script `scripts/metabase_api.py create-card`. Default to native SQL payloads for all tiers (see Tier 1/2 fallback note above).
5. **Create / update the dashboard** depending on the chosen flow (`POST /api/dashboard`, then `PUT /api/dashboard/{id}` with the dashcards array). Use the layout heuristic in `references/dashboard-layout.md`.
6. **Write results back into `widget-review.md`** — add or update a `Result` column in the summary table with the live Metabase URL (or the error message) for each row, and append a `## Results` section at the bottom with the dashboard URL, totals, and any failures.
7. **Report in chat**: total created, total failed (with reasons), dashboard URL, and the path to the updated review file.

If any individual card fails to create, **continue with the rest** — record the failure in the review file, still build the dashboard with the cards that succeeded.

### Output format

**Tier 1 / Tier 2 widget build format (Query Builder)** — used inside the per-widget detailed sections of `widget-review.md`. Mirror the Metabase notebook editor's step order. Skip steps the question doesn't need.

````
**Tier:** 1 (Basic Query Builder) | 2 (Advanced Query Builder)

**Pick data:** NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT (or the user's table)

**Custom columns (Tier 2 only, if any):**
- Name: `Operation Name`
  Expression: `regexextract([Destination Name], "[^:]+$")`

**Filter:**
- COLUMN is `value`
- COLUMN starts with `value` (Use for prefix matching to match e.g. `delete` or `delete_confirm` prefixes while avoiding `abc_delete`)
- COLUMN contains `value` (Use only when the search term can appear anywhere in the string)
- COLUMN is any of `value1`, `value2` (select multiple values in one filter pill for OR behavior; do NOT say "is in")
- (For OR across different columns, use Filter → Custom Expression)
- (Omit Action Type when it's `click` — that's the default for most telemetry events)
…

**Summarize:**
- Metric: Count of rows  (or Sum of …, Average of …, Custom Expression, etc.)
- Group by: COLUMN  (datetime columns let you pick granularity — default: `Month`, though `Day`/`Week` are options if requested)

**Sort (only for top-N or ordered output):**
- COLUMN descending

**Row limit (only for top-N):**
- 10

**Visualization:** table / bar / row / line / trend / funnel / combo / stacked bar / etc.
(If result cardinality is unknown, give two conditional recommendations — see chart-selection.md.)

**Why this chart:** one sentence tying the chart choice to the question's shape and intent (see `references/chart-selection.md`).

**Why these filters:** one-sentence explanation of what each filter isolates and why it was chosen.

**SQL equivalent (used for Stage 2 API creation):**
```sql
-- Snowflake-compatible SQL that produces the same result as the Query Builder steps above.
-- This is what the skill will POST to /api/card if the user confirms execution.
SELECT …
````

```

**Tier 3 widget build format (SQL)**

```

**Tier:** 3 (SQL)

**SQL:**

```sql
-- Snowflake-compatible, directly pasteable into Metabase
SELECT …
```

**What it returns:** one-sentence explanation.

**Visualization:** the chart type to switch to after running the query (native queries default to a table — actively pick the right chart per `references/chart-selection.md`).

**Why this chart:** one sentence justifying the choice.

````

The full `widget-review.md` structure (summary table columns, status values, detailed-section ordering) is defined in `references/review-file-format.md`.

## Data model

Read `references/data-model.md` for the table/column mapping, field aliases, and known quirks. If the user names a table or columns not in the reference, use what they provide.

## Gotchas

- **Use display names in the Query Builder, DB names in SQL.** The same column has two representations: SQL uses the uppercase DB name (`DESTINATION_NAME`, `SUB_PAGE_SECTION`, `HASHED_ACCOUNTID`); Query Builder filters and custom expressions use the Title-Case display name in brackets (`[Destination Name]`, `[Sub Page Section]`, `[Hashed Accountid]`). Never write `[DESTINATION_NAME]` in a custom expression — it won't resolve. Check `references/data-model.md` for the mapping.

- **Filter columns may be NULL for some event variants.** Two events that look like siblings (e.g. a "single" action and its "bulk" counterpart) often differ in which context columns are populated. If a filter makes one variant disappear, drop that filter or make it optional and run a diagnostic before concluding the data is missing.

- **Match order matters for overlapping prefixes.** When one prefix is a substring of another (e.g. `foo` and `foo_group`), check the longer/more-specific one first in `CASE` and `ILIKE` chains, or the specific variant gets misclassified as the general one.

- **`regexExtract` returns the full match, not a capture group.** Metabase's documented signature is `regexExtract(text, regular_expression)` — there is no group-index argument. Write patterns that match only the desired substring (e.g. `[^:]+$`), not `^prefix:(.+)$`. Function names in the editor are case-insensitive (`regexextract` works), even though docs use camelCase.

- **The expression editor has no `indexOf`.** Use `regexExtract`, `splitPart`, or `substring` instead. (`replace`, `concat`, `case` are all available — see `references/advanced-operations.md` for the full list before assuming a function is missing.)

- **Multiple values in one filter pill = OR; separate pills = AND.** Useful when comparing values in the same column.

- **Do NOT use the phrase "is in" for visual filters.** There is no "is in" option in the Metabase filter UI. Instead, suggest "COLUMN is any of `value1`, `value2`" (instructing the user to select multiple checkboxes within a single filter pill), or write a Custom Filter Expression using `in([Column], "val1", "val2")` or `[Column] = "val1" OR [Column] = "val2"`. If the logic gets too complex or involves multiple steps/joins, escalate to Tier 3 SQL.

- **Default time-series granularity to Month.** When displaying trends or metrics over time, default to grouping by `Month` rather than `Week` or `Day`, unless a different granularity is explicitly requested or there's very little data history.

- **No date filter is applied by default.** Remind the user to add a relative date filter if the question is about recent behavior.

- **Sync after schema changes.** New Snowflake tables/views need Admin → Databases → Sync database schema now → Re-scan field values before Metabase sees them.

- **Always use the full table name — never the alias.** The flat view is `NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT`. The shorthand `NUSIGHTS_EVENTS_FLAT` does not exist as a Snowflake object and will cause a compilation error. Use the full name in SQL and in "Pick data" instructions.

- **Don't over-filter global questions.** If the question is broad ("which pages are most visited"), filter only on `ACTION_TYPE` / `FEATNAME` — don't add `DESTINATION_NAME` or `SUB_PAGE_SECTION` unless the question scopes to a specific entity or page. Adding every payload field as a filter is the fastest way to accidentally exclude events.

- **Don't filter on Action Type when it's `click`.** Almost all telemetry events are `click` events — adding `Action Type is click` to every widget is noise. Only include an Action Type filter when the event uses a different type (`change`, `submit`, `view`, etc.). Same applies in SQL: skip `AND ACTION_TYPE = 'click'` unless the event is non-click.

- **Use `starts with` (Query Builder) or `startsWith` (Custom Expressions) for prefix matching, NOT `contains`.** If you want to match events starting with a specific term (e.g. `delete` or `delete_confirm`), suggest `starts with "delete"`. Do NOT use `contains "delete"`, as that will incorrectly match values like `abc_delete` or `system_delete`. Only use `contains` (Query Builder) or `contains` (Custom Expressions) if the term can legitimately appear anywhere in the string. In SQL, use `LIKE 'delete%'` or `ILIKE 'delete%'`.

## References

- `references/data-model.md` — read at the start of every invocation for table/column mapping
- `references/query-patterns.md` — read when deciding whether a question fits Tier 1 (basic builder) or needs SQL
- `references/advanced-operations.md` — read when building a Tier 2 widget (custom columns, custom filters, custom summaries, period-over-period)
- `references/chart-selection.md` — read when picking the visualization, especially for anything beyond a basic number / bar / line
- `references/review-file-format.md` — read whenever generating or re-reading `widget-review.md` (Stage 1 output and Stage 2 input)
- `references/api-integration.md` — read at the start of Stage 2 for configuration, authentication, endpoint payloads, and error handling
- `references/execution-flows.md` — read at the start of Stage 2 to pick the right flow (new dashboard / existing dashboard / questions only / markdown only)
- `references/dashboard-layout.md` — read when placing cards on a dashboard (18-column grid, sizing heuristic, auto-layout rules)

## Utility scripts

The skill ships with two helper scripts under `scripts/`. Prefer running these over hand-rolling API calls — they encapsulate auth, error handling, and the JSON payload shape.

**`scripts/metabase_api.py`** — Metabase REST API client. Subcommands:

```bash
# Verify connectivity and config
python scripts/metabase_api.py check

# Discover databases / collections / tables
python scripts/metabase_api.py list-databases
python scripts/metabase_api.py list-collections
python scripts/metabase_api.py list-tables --database-id 2

# Create a native SQL question (card)
python scripts/metabase_api.py create-card \
  --name "Save vs Save & Create" \
  --description-file desc.txt \
  --sql-file query.sql \
  --display bar \
  --collection-id 63

# Create a dashboard and add cards to it
python scripts/metabase_api.py create-dashboard \
  --name "Role Management — Telemetry" \
  --description "Telemetry widgets for the Role Management feature area." \
  --collection-id 63

python scripts/metabase_api.py add-cards \
  --dashboard-id 123 \
  --layout-file layout.json

# Look up an existing dashboard by name or URL
python scripts/metabase_api.py find-dashboard --query "Role Management"
python scripts/metabase_api.py find-dashboard --url "https://metabase.example.com/dashboard/45-role-management"
```

Run `python scripts/metabase_api.py --help` (and `<subcommand> --help`) for the full flag list.

**`scripts/widget_review.py`** — Parse and update `widget-review.md`. Subcommands:

```bash
# Parse a (possibly user-edited) review file into structured JSON
python scripts/widget_review.py parse widget-review.md > widgets.json

# Update the review file with API results after Stage 2
python scripts/widget_review.py update-results \
  --review widget-review.md \
  --results-file results.json
```

## Configuration

Stage 2 requires these environment variables (or values from a local `.env` file — see `.env.example`):

| Variable                         | Required | Description                                                          |
| -------------------------------- | -------- | -------------------------------------------------------------------- |
| `METABASE_BASE_URL`              | Yes      | Base URL, no trailing slash (e.g. `https://metabase.example.com`)    |
| `METABASE_API_KEY`               | Yes      | API key created in Admin → Settings → Authentication → API Keys      |
| `METABASE_DATABASE_ID`           | Yes      | Numeric ID of the database the queries run against                   |
| `METABASE_DEFAULT_COLLECTION_ID` | No       | Default collection for new cards/dashboards (omit for personal root) |
| `METABASE_DEFAULT_TABLE_NAME`    | No       | Default SQL table name (defaults to the flat telemetry view)         |

`references/api-integration.md` § "Setup checklist" walks through how to find each ID.

## Diagnostic-first when results are empty

If the user reports "no results," do not guess which filter is wrong. Produce a diagnostic SQL query that removes all filters except the event name match, groups by every filter column, and returns counts — so the user can see what values actually exist for those events. Then adjust filters based on the diagnostic output.
````
