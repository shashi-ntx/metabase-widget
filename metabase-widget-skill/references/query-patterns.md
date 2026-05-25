# Metabase Query Patterns for Telemetry Data

A practical guide for which telemetry questions Metabase can answer with the visual builder and which ones need handwritten SQL. The main takeaway: simple counting and trend questions work well in the visual query builder, while multi-step funnels and time-between-events analysis need SQL.

## Data model that worked

There are two useful shapes in Snowflake:

| Table | Purpose |
|---|---|
| `NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL` | Raw events table with `PAYLOAD` stored as JSON / `VARIANT` |
| `NUSIGHTS_EVENTS_FLAT` | Flattened view that pulls JSON keys into regular columns |

For Metabase questions, the reliable choice is `NUSIGHTS_EVENTS_FLAT` because its columns can be filtered directly in the UI.

### Important field mapping

| Telemetry event field | Snowflake / Metabase column |
|---|---|
| `actionName` | `DESTINATIONNAME` |
| `actionType` | `ACTIONTYPE` |
| `featName` | `FEATNAME` |
| `pageSection` | `PAGESECTION` |
| `subPageSection` | `SUBPAGESECTION` |

## Metric selection

The question's wording tells you which metric to use. Apply the first matching rule:

| Question phrasing | Metric | Query Builder equivalent |
|---|---|---|
| "how many users", "who uses", "adoption", "unique users" | `COUNT(DISTINCT HASHED_ACCOUNTID)` | Number of distinct values of → Hashed Accountid |
| "how many sessions", "session-level", "per session" | `COUNT(DISTINCT SESSION_ID)` | Number of distinct values of → Session ID |
| "how often", "how many times", "frequency", "total clicks" | `COUNT(*)` | Count of rows |
| "most used", "top", "ranking" | `COUNT(*)` + `GROUP BY` + `ORDER BY DESC` | Count of rows, grouped, sorted descending |
| "trend", "over time", "growing" | `COUNT(*)` + `GROUP BY timestamp` | Count of rows, grouped by Timestamp (default: Month; day/week are options) |
| "drop off", "funnel", "conversion" | Per-step counts (usually SQL) | Tier 3 |

**Default to `COUNT(*)`** (total events) when the question doesn't signal a specific unit. Only use distinct user or session counts when the question explicitly asks for unique users, adoption, or session-level behavior — over-counting is less misleading than silently deduplicating when the user expects raw volume.

When the metric is ambiguous after reading the question, ask the user: "Should this count total events or unique users?"

## Quick decision guide

| If the question is about... | Best tool |
|---|---|
| A single filtered count | Query Builder |
| Counts over time | Query Builder |
| Comparing values in the same column | Query Builder |
| Funnel steps with different filters | SQL |
| Time between two event types | SQL |
| Average / median time across matched events | SQL |

## Patterns that work in the visual builder

### 1. Simple count

Good for: "How many times did users click X?"

Working setup:
1. Pick `NUSIGHTS_EVENTS_FLAT`
2. Add the needed filters
3. Summarize with `Count`

### 2. Count over time

Good for: "How often does X happen each month?"

Working setup:
1. Pick `NUSIGHTS_EVENTS_FLAT`
2. Filter to the event you care about
3. Summarize with `Count`
4. Group by `TIMESTAMP` set to Month granularity (default to Month for trend lines)

### 3. Compare values in the same column

Good for: "How many people saved vs exited?"

Working setup:
1. Filter on the shared context, such as `PAGESECTION`
2. Put multiple values into one filter for the comparison column
3. Summarize with `Count`
4. Group by that same comparison column

Important rule of thumb:
- **Do NOT suggest "COLUMN is in {values}".** There is no "is in" operator in Metabase's visual filter UI. To match multiple values, use "COLUMN is any of `value1`, `value2`" by selecting multiple checkboxes in a single filter pill (which behaves as an OR).
- For custom filter expressions, use `in([Column], "val1", "val2")` or `[Column] = "val1" OR [Column] = "val2"`.
- Separate filter pills behave like AND.
- **Prefer `starts with` over `contains` for matching event name prefixes.** To match prefix `delete` (such as `delete` and `delete_confirm`), filter with `starts with "delete"` or use Custom Expression `startsWith([Column], "delete")`. Do NOT use `contains "delete"`, because it would incorrectly match substrings like `abc_delete`.

## Patterns that need SQL

### 4. Funnel analysis

Use SQL when each funnel step has different filters and you need one combined result. The practical pattern is `UNION ALL`, one `SELECT` per step.

### 5. Time between two events

Use SQL when you need to pair a start event and an end event from the same session. The working pattern is:

1. Pull start events into one CTE
2. Pull end events into another CTE
3. Join on `SESSIONID`
4. Keep only starts that happened before the end
5. Pick the most recent valid start
6. Calculate the time difference with `TIMESTAMPDIFF`

### 6. Average time between events

Same pairing pattern as above, but finish with an aggregate like `AVG(...)` instead of listing every matched session.

## Metabase-specific lessons

### Sync after schema changes

If a new table or view is created in Snowflake, Metabase will not pick it up until you run:

1. **Admin -> Databases**
2. Open the Snowflake connection
3. **Sync database schema now**
4. **Re-scan field values**

### JSON columns are not query-builder friendly

Metabase cannot use the visual builder to filter deeply inside Snowflake `VARIANT` / JSON columns. That is why the `NUSIGHTS_EVENTS_FLAT` view matters so much: it turns payload keys into normal columns.

### Save useful questions clearly

Questions are much easier to reuse when they are saved with direct names like:

- `Create Role Clicks`
- `Save Role - create only`
- `Role Creation Funnel`
