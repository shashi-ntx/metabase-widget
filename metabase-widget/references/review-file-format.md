# `widget-review.md` — Format and Parsing Contract

`widget-review.md` is the single artefact produced in Stage 1 and the single input consumed in Stage 2. It must be readable by humans (so they can edit it) and parseable by the skill (so user edits drive Stage 2 deterministically).

This document defines:

1. The exact file structure the skill writes.
2. The status values and what they mean.
3. What the user is allowed to edit.
4. How the skill must re-read the file before Stage 2.
5. How the skill writes results back into the file after Stage 2.

## File location and name

- Default: `metabase-widget-suggestions/widget-review.md`
- Override: whatever path the user gives.
- One file per skill invocation. Do **not** split into one-file-per-widget — the whole point is a single editable review document.

## Top-of-file structure

```markdown
# Widget Review — <Feature Area / Project Name>

> Generated: <ISO-8601 timestamp> | Total: <N> | Ready: <R> | Flagged: <F> | Dropped: <D>

## Summary

| #   | Requirement | Widget Title | Recommended Approach | Tier | Visualization | Alternative Approach | Alt Tier | Alt Visualization | Status                          | Result      |
| --- | ----------- | ------------ | -------------------- | ---- | ------------- | -------------------- | -------- | ----------------- | ------------------------------- | ----------- |
| 1   | …           | …            | …                    | T1   | Bar           | …                    | T3       | Bar               | ✅ Ready                        | _(pending)_ |
| 2   | …           | …            | …                    | T2   | Row           | …                    | T3       | Row               | ✅ Ready                        | _(pending)_ |
| 3   | …           | …            | …                    | T3   | Funnel        | _(none — SQL only)_  | —        | —                 | ✅ Ready                        | _(pending)_ |
| 4   | …           | —            | —                    | —    | —             | —                    | —        | —                 | ⚠️ Flagged: no payload provided | —           |

### Status legend

- `✅ Ready` — will be created in Stage 2.
- `⚠️ Flagged: <reason>` — incomplete; skipped in Stage 2 until the user resolves it and changes the status to `✅ Ready`.
- `❌ Dropped` — user-removed; permanently skipped.

### Column meanings

- **#** — 1-based row number; matches the order in the original input.
- **Requirement** — the question, cleaned for grammar.
- **Widget Title** — the noun-phrase title that will be used as the Metabase card `name`.
- **Recommended Approach** — one-line description of the primary build path.
- **Tier** — `T1`, `T2`, or `T3`.
- **Visualization** — the Metabase `display` value for the recommended approach.
- **Alternative Approach** — one-line description of a fallback (often the SQL equivalent of a Query Builder approach, or vice versa).
- **Alt Tier / Alt Visualization** — same as above for the alternative; use `—` if none.
- **Status** — see status legend.
- **Result** — `_(pending)_` until Stage 2 runs. After Stage 2: a markdown link to the created card (`[#123](https://metabase.example.com/question/123)`), or an error message prefixed `❌ Error:`.
```

## Detailed per-widget sections

Below the summary table, write one section per `✅ Ready` widget — in row-number order — under a single `## Widget Details` heading.

```markdown
---

## Widget Details

### 1. <Widget Title>

#### Question

<corrected, grammatical question with trailing `?`>

#### Payload Context

<2–4 sentences describing the relevant events and key fields. Not the raw JSON.>

#### Recommended Approach

<Tier 1/2/3 build instructions in the format defined in SKILL.md.
For Tier 1/2: include the "SQL equivalent (used for Stage 2 API creation)" block at the bottom — this is what the skill will actually POST to /api/card.>

#### Alternative 1 — <short label>

<Same detail level as the recommended approach. Optional — omit the heading entirely if there is no alternative.>

#### Assumptions & Caveats

- <bullet list of assumptions>
- <data quality notes the user should verify>

#### Metabase Save Details

**Title:** <noun-phrase title — must match the Widget Title column in the summary table>

**Description:**
> "<the corrected question>"
>
> <one short sentence on what the widget helps the viewer understand>

**Display:** <Metabase API display value, e.g. `bar`, `row`, `line`, `scalar`, `funnel`>

**Visualization settings:** <optional JSON snippet for `visualization_settings`, if the chart needs explicit dimension/metric assignments — see `api-integration.md`>

---

### 2. <Widget Title>

…
```

The skill should write a `---` separator between widget sections so users can scan easily.

## What the user is allowed to edit

The user can edit `widget-review.md` between Stage 1 and Stage 2. The skill must respect every documented edit:

| Edit                                 | How the user does it                                                                                                                                                                                                        | How the skill responds                                                                                                                                |
| ------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Drop a widget**                    | Change the **Status** cell to `❌ Dropped`                                                                                                                                                                                  | Skip the widget entirely in Stage 2                                                                                                                   |
| **Swap to the alternative approach** | Either (a) change **Status** to `✅ Ready (use alternative)` _or_ (b) swap the **Recommended ↔ Alternative** column contents manually _or_ (c) edit the detailed section to put the alternative content under "Recommended" | Use the section currently labeled `Recommended Approach` in the detailed section as the source of truth                                               |
| **Resolve a flagged row**            | Add the missing payload/info in the detailed section, then change **Status** from `⚠️ Flagged` to `✅ Ready`                                                                                                                | Treat as Ready and build it like any other widget                                                                                                     |
| **Edit the title / description**     | Edit the **Widget Title** column AND/OR the `#### Metabase Save Details` block                                                                                                                                              | Use the edited values verbatim. If the summary table and the detailed section disagree, the **detailed section wins** (it's the more deliberate edit) |
| **Edit the SQL / filters / chart**   | Edit the recommended-approach code block or filter list in the detailed section                                                                                                                                             | Use the edited SQL / display value verbatim                                                                                                           |
| **Add a brand-new widget**           | Add a new row to the summary table and a new `### N. <Title>` section under `## Widget Details`                                                                                                                             | Treat it like any other Ready widget. Row numbers may be non-contiguous after edits — that's fine; sort by the **#** column                           |
| **Reorder widgets**                  | Reorder rows in the summary table and/or sections under Widget Details                                                                                                                                                      | Build in the order they appear in the summary table; this also drives dashboard layout order                                                          |
| **Change Display / Visualization**   | Edit the **Visualization** column and/or the `**Display:**` field in the detailed section                                                                                                                                   | Detailed section's `**Display:**` value wins                                                                                                          |

## Re-read protocol (Stage 2 entry point)

When the user confirms execution:

1. Re-open `widget-review.md` from disk — never reuse the in-memory data from Stage 1.
2. Run `python scripts/widget_review.py parse <path>` to convert to a structured JSON list. The script:
   - Parses the summary table by header names (not column position) — robust to user reordering columns.
   - Parses each detailed section by `### <N>. <Title>` heading.
   - Cross-references summary rows with detailed sections by widget number.
   - Reports parse errors (malformed table rows, missing sections, mismatched titles) with line numbers — exit code non-zero.
3. If the parser exits non-zero, **stop and surface the errors to the user**. Do not attempt to fix automatically; ask the user to fix the markdown and retry.
4. Filter to widgets where `status` starts with `✅ Ready` (case-sensitive emoji). All other statuses are skipped.
5. If zero widgets are Ready, warn the user and stop — don't create an empty dashboard.

## Write-back protocol (Stage 2 exit point)

After creating cards / dashboards in Metabase:

1. Build a `results.json` file with one entry per widget:

   ```json
   [
     {
       "number": 1,
       "status": "created",
       "card_id": 123,
       "card_url": "https://metabase.example.com/question/123",
       "error": null
     },
     {
       "number": 2,
       "status": "error",
       "card_id": null,
       "card_url": null,
       "error": "Snowflake compilation error: invalid identifier 'DESTINATION_NAMEE'"
     }
   ]
   ```

2. Run `python scripts/widget_review.py update-results --review widget-review.md --results-file results.json`. The script:
   - Updates the **Result** column in the summary table for each row (link or `❌ Error: <message>`).
   - Appends (or updates) a `## Results` section at the bottom containing:
     - Dashboard URL (if a dashboard was created/updated)
     - Totals: created, failed
     - A bulleted list of failures with the error messages

3. Surface the dashboard URL and totals in chat too, and link the user back to the updated `widget-review.md`.

## Per-requirement files (opt-in)

`widget-review.md` is always the single source of truth. Per-requirement markdown files are an **optional, opt-in** extra — generated only when the user explicitly asks (see SKILL.md § "Per-requirement markdown files"). They are documentation; Stage 2 ignores them entirely.

### Location

All per-requirement files go under an `output/` subfolder inside the chosen output directory:

```
metabase-widget-suggestions/
├── widget-review.md          ← always written
└── output/                   ← only when user opts in
    ├── _index.md
    ├── 01-save-vs-save-and-create.md
    ├── 02-top-operations-added.md
    ├── 03-role-creation-funnel.md
    ├── 04-no-payload-toggle-feature-x.md
    ├── 07-flagged-ambiguous-events-search-usage.md
    └── 09-dropped-old-metric.md
```

### Filename rules

- Always starts with the row number, zero-padded to 2 digits (3 digits if > 99 requirements).
- Lowercase, hyphen-separated slug; ASCII only; max ~50 chars after the row number.
- One file per requirement row, regardless of status:

| Row status               | Filename format                          | Example                             |
| ------------------------ | ---------------------------------------- | ----------------------------------- |
| `✅ Ready`               | `NN-<slug-of-widget-title>.md`           | `01-save-vs-save-and-create.md`     |
| `⚠️ Flagged: no payload` | `NN-no-payload-<slug-of-requirement>.md` | `04-no-payload-toggle-feature-x.md` |
| `⚠️ Flagged: <reason>`   | `NN-flagged-<short-reason>-<slug>.md`    | `07-flagged-ambiguous-events-...md` |
| `❌ Dropped`             | `NN-dropped-<slug>.md`                   | `09-dropped-old-metric.md`          |

### File contents by status

**`✅ Ready`** — copy the per-widget detailed section verbatim from `widget-review.md`:

```markdown
# <Widget Title>

## Question

…

## Payload Context

…

## Recommended Approach

…

## Alternative 1 — <label>

… (optional)

## Assumptions & Caveats

- …

## Metabase Save Details

**Title:** …

**Description:**

> "…"
>
> …

**Display:** …

**Visualization settings:**
\`\`\`json
{}
\`\`\`
```

**`⚠️ Flagged`** — explain what's missing and how to unblock:

```markdown
# ⚠️ Flagged — <original requirement text>

> Row: **4** | Page section: **<section>** | Status: **⚠️ Flagged: no payload provided**

## Original Requirement

<the original question, verbatim>

## Why this is flagged

No telemetry payload was provided for this requirement. Without an example event, the skill can't determine which event name, action type, or columns to filter on.

## What's needed to unblock

Please provide at least one of:

- A sample JSON event payload that fires when the action occurs.
- The event name (e.g. `toggle_feature_x`) and any relevant context columns.
- A pointer to the page or component in the product so the event can be looked up.

Once you add the payload, change this row's status in `widget-review.md` from `⚠️ Flagged: no payload provided` to `✅ Ready` and re-run the skill.
```

**`❌ Dropped`** — short note for documentation:

```markdown
# ❌ Dropped — <original requirement text>

> Row: **9** | Page section: **<section>** | Status: **❌ Dropped**

## Original Requirement

<the original question, verbatim>

## Note

This requirement was dropped during review and will not be created in Metabase.
```

### Index file (`output/_index.md`)

```markdown
# Widget Proposals — Index

> Processed: 42 | Ready: 36 | Flagged: 4 | Dropped: 2

## <Page Section / Feature Area>

| #   | Status   | Widget Title / Requirement | File                                                           |
| --- | -------- | -------------------------- | -------------------------------------------------------------- |
| 1   | ✅ Ready | Save vs Save & Create      | [01-save-vs-save-and-create.md](01-save-vs-save-and-create.md) |
| 2   | ✅ Ready | Top Operations Added       | [02-top-operations-added.md](02-top-operations-added.md)       |

## <Another Page Section>

| #   | Status   | Widget Title / Requirement | File                                                     |
| --- | -------- | -------------------------- | -------------------------------------------------------- |
| 3   | ✅ Ready | Role Creation Funnel       | [03-role-creation-funnel.md](03-role-creation-funnel.md) |

## Flagged / Skipped

| #   | Status                       | Original Requirement                 | File                                                                                       |
| --- | ---------------------------- | ------------------------------------ | ------------------------------------------------------------------------------------------ |
| 4   | ⚠️ Flagged: no payload       | How often do users toggle feature X? | [04-no-payload-toggle-feature-x.md](04-no-payload-toggle-feature-x.md)                     |
| 7   | ⚠️ Flagged: ambiguous events | How often is search used?            | [07-flagged-ambiguous-events-search-usage.md](07-flagged-ambiguous-events-search-usage.md) |
| 9   | ❌ Dropped                   | Old metric — replaced by row 3       | [09-dropped-old-metric.md](09-dropped-old-metric.md)                                       |
```

Group Ready rows by page section / feature area when that column is available in the input; collapse Flagged + Dropped into a single trailing "Flagged / Skipped" table.

## Parse-error policy

If `widget_review.py parse` finds malformed markdown:

- Report exact line numbers and what's wrong.
- Do **not** attempt to silently skip the malformed widget — the user may have intended to edit it and made a typo.
- Tell the user the specific fix needed (e.g. "row 3 has 10 columns but the header defines 11").
- Refuse to proceed to Stage 2 until the file parses cleanly.

## Example: minimal valid `widget-review.md`

````markdown
# Widget Review — Role Management

> Generated: 2026-05-21T15:00:00Z | Total: 2 | Ready: 2 | Flagged: 0 | Dropped: 0

## Summary

| #   | Requirement                               | Widget Title          | Recommended Approach                                                                                                   | Tier | Visualization | Alternative Approach                  | Alt Tier | Alt Visualization | Status   | Result      |
| --- | ----------------------------------------- | --------------------- | ---------------------------------------------------------------------------------------------------------------------- | ---- | ------------- | ------------------------------------- | -------- | ----------------- | -------- | ----------- |
| 1   | How often do users save vs save & create? | Save vs Save & Create | Query Builder — filter Destination Name is any of save_role, save_role_create_policy; Count; group by Destination Name | T1   | Bar           | SQL — CASE label + COUNT(\*) GROUP BY | T3       | Bar               | ✅ Ready | _(pending)_ |
| 2   | Funnel: role create → policy save         | Role Creation Funnel  | SQL — UNION ALL with per-step counts                                                                                   | T3   | Funnel        | _(none — SQL only)_                   | —        | —                 | ✅ Ready | _(pending)_ |

---

## Widget Details

### 1. Save vs Save & Create

#### Question

How often do users save their roles versus save and go to policy creation?

#### Payload Context

`save_role` and `save_role_create_policy` are two `click` events on the role-create form. Both populate `DESTINATION_NAME`; no other payload fields are needed.

#### Recommended Approach

**Tier:** 1 (Basic Query Builder)

**Pick data:** NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT

**Filter:**

- Destination Name is any of `save_role`, `save_role_create_policy`

**Summarize:**

- Metric: Count of rows
- Group by: Destination Name

**Visualization:** bar
**Why this chart:** Two-row comparison — bar makes the magnitude immediate.

**SQL equivalent (used for Stage 2 API creation):**

```sql
SELECT
  CASE
    WHEN DESTINATION_NAME = 'save_role' THEN 'Save'
    WHEN DESTINATION_NAME = 'save_role_create_policy' THEN 'Save & Create Policy'
  END AS ACTION_LABEL,
  COUNT(*) AS TOTAL_CLICKS
FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
WHERE DESTINATION_NAME IN ('save_role', 'save_role_create_policy')
GROUP BY ACTION_LABEL
ORDER BY TOTAL_CLICKS DESC;
```
````

#### Assumptions & Caveats

- Both events fire on the same form; if `save_role_create_policy` is also fired by an unrelated workflow, the comparison is biased.

#### Metabase Save Details

**Title:** Save vs Save & Create

**Description:**

> "How often do users save their roles versus save and go to policy creation?"
>
> Shows whether users typically finish at Save or continue into policy creation.

**Display:** bar

**Visualization settings:**

```json
{
  "graph.dimensions": ["ACTION_LABEL"],
  "graph.metrics": ["TOTAL_CLICKS"]
}
```

---

### 2. Role Creation Funnel

… (same structure)

```

```
