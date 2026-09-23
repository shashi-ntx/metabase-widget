# Migrating an Existing Dashboard into Metabase

Read this when the user wants to rebuild a dashboard from another tool in Metabase. The main case so far is a Snowflake legacy dashboard exported as JSON; Snowflake is retiring legacy dashboards. The same approach works for any export that contains SQL plus chart settings.

The goal is **faithful reproduction first**: the Metabase numbers should match what the old dashboard showed. Only fix logic the user explicitly asks you to fix. Record any suspected logic bugs as caveats instead.

## What to ask the user (and what not to)

Ask only for what you can't discover yourself:

- The target collection. A pasted collection URL gives the ID (`…/collection/26-foo` → `26`).
- Whether to reproduce the old logic exactly or "fix" it. Default: reproduce exactly.
- Whether they have reference numbers or screenshots from the old dashboard. Often they don't, because the source tool has already retired it. In that case, the export itself is the spec.

Discover the rest yourself: database ID (`list-databases`), table ID (`find-table`), field IDs (`list-fields`), and Metabase version (`check`).

## Snowflake dashboard JSON shape

```json
{
  "name": "Storage-VGs",
  "warehouse": "PROD_EXPLORE_WH",
  "role": "PROD_EXPLORE_ROLE",
  "cells": [                       // rows of the dashboard grid
    [                              // one row
      {
        "name": "Customers using VGs",
        "display": "chart" | "table",
        "query": "<full worksheet text, may contain SEVERAL statements>",
        "queryRange": {"start": 0, "end": 334},   // the statement that actually ran
        "chart": {
          "type": "scorecard" | "bar" | "line" | …,
          "steps": [ {"type": "hideCols", …}, {"type": "group", "combineFns": […]} ],
          "primary":   [{"key": "COL"}],          // x-axis / dimensions
          "secondary": {"columns": [{"key": "COL", "aggregation": "sum|count"}], "label": "…"},
          "barStyle":  {"horizontal": true, "orderBy": "size|label", "reverseOrder": true, "stack": "disabled"}
        }
      }
    ]
  ],
  "params": []
}
```

## Translation rules

1. **Use `queryRange` to pick the executed statement.** When a `query` contains several statements, `query[start:end]` is the one the card ran. If there is no `queryRange`, the whole query ran.
2. **Reproduce the chart's client-side aggregation.** Snowflake charts re-aggregate the query result: `steps` of type `group` with `combineFns`, or `secondary.columns[].aggregation`. A scorecard over a per-customer query with `count` of `CUSTOMER_NAME` means "count of result rows". A `sum` of `CLUSTER_COUNT` means "sum of that column". Wrap the original statement unchanged as a CTE and apply that aggregation outside:

   ```sql
   WITH src AS (
     <executed statement, trailing semicolon removed>
   )
   SELECT SUM(CLUSTER_COUNT) AS CLUSTERS_WITH_VGS FROM src
   ```

   This avoids re-deriving the logic by hand, and keeps quirks such as grouping by two columns or summing per-customer distinct counts exactly as the old dashboard had them.

3. **Map the chart type:**

   | Snowflake                                       | Metabase `display`                                                    |
   | ----------------------------------------------- | --------------------------------------------------------------------- |
   | `scorecard`                                     | `scalar`                                                              |
   | `bar`                                           | `bar`                                                                 |
   | `bar` + `barStyle.horizontal: true`             | `row`                                                                 |
   | `bar` with two `primary` keys                   | `bar` with the second key as series (`graph.dimensions: [x, series]`) |
   | `line`                                          | `line`                                                                |
   | `display: "table"` (whatever `chart.type` says) | `table`                                                               |

4. **Map ordering.** `orderBy: "size"` + `reverseOrder: true` → `ORDER BY <metric> DESC`. `orderBy: "label"` → order by the dimension. Metabase keeps the SQL row order for categorical bar charts.
5. **Rename duplicate card names.** Exports often reuse a name (e.g. a KPI "Total VGs" and a table "Total VGs"). Give each card a distinct title.
6. **Layout.** Keep the export's row structure on the 24-column grid. Divide 24 by the number of cells in each row (3 cells → 8 wide, 2 → 12, 1 → 24). Heights: scalars 3–4, charts 7, tables 8–9.
7. **Snowflake SQL runs as-is** through the Metabase Snowflake connection, including `//` comments and fully qualified `"DB"."SCHEMA"."TABLE"` names. The Metabase connection's role must be able to read those objects. Check with a dry run.

## Build order

1. `check`, then dry-run every translated query with `run-query`. Fix failures before creating anything.
2. Create all cards as SQL (the faithful baseline), create the dashboard, and place the cards.
3. **Offer to convert simple cards to the Query Builder**, so designers can edit them. Classify each card:
   - **Easy:** one filter + summarize + group-by (KPIs, counts by a dimension, counts by year, per-customer tables). Convert these.
   - **Medium:** summarize → bucket with `case` → summarize again. Only convert on request, using nested MBQL stages.
   - **Hard:** multiple nested aggregations plus complex bucketing. Keep as SQL.
4. For each conversion, build the MBQL, run `compare` against the SQL card's query, and only on `MATCH` create the MBQL card and swap it into the dashcard (same position, new `card_id`). Offer to archive the replaced SQL cards so designers don't open the wrong copy.

## Report back

- The dashboard URL.
- Headline numbers (the KPI values), so the user can sanity-check them.
- Every inherited quirk or suspected logic bug, stated plainly (e.g. "'Clusters with VGs' sums per-customer counts, so shared clusters count twice").
- Which cards are Query Builder and which are SQL.
