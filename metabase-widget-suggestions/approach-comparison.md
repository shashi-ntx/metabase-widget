# Approach Comparison: Automated Skill vs Manual Dashboard

**Source:** Comparing the automated `shashi-storage-widget-automation` dashboard (rows 01–05) against the manually-built `Storage Dashboard` (dashboard/6).

**Automated dashboard:** [shashi-storage-widget-automation](https://jerome-marshall-1.umsvm.nutanix.com:3300/dashboard/12) — 5 cards, rows 01–05 only  
**Your manual dashboard:** [Storage Dashboard](https://jerome-marshall-1.umsvm.nutanix.com:3300/dashboard/6-storage-dashboard) — 13 cards, covering rows 01–05 plus rows 07–09, 11–14, 17–18, 20

---

## Summary of Differences

| Aspect                    | Your Approach (Manual)                                            | Automated Skill Approach                                 |
| ------------------------- | ----------------------------------------------------------------- | -------------------------------------------------------- |
| **Query type**            | MBQL (Query Builder) via a saved model (source-card: 73)          | Native SQL directly against the flat table               |
| **Data source**           | Model/question #73 as a pre-filtered source card                  | Raw `NUSIGHTS_EVENTS_FLAT` table                         |
| **Label cleaning**        | Raw `ACTION_TYPE` values shown (e.g. `sort_column.cluster_name`)  | SQL `REGEXP_SUBSTR` strips prefix → shows `cluster_name` |
| **Time granularity**      | Month (dashboard-level temporal-unit parameter, default: month)   | Week (hardcoded `DATE_TRUNC('week', ...)`)               |
| **Dashboard filter**      | Temporal-unit filter (`?time=month`) applied globally             | No dashboard-level filter                                |
| **Scope**                 | 13 cards covering requirements 01–05 + 07–09 + 11–14 + 17–18 + 20 | 5 cards covering requirements 01–05 only                 |
| **Visualization variety** | Pie, bar, scalar, line, table, funnel, object (detail)            | Row chart, line chart, trend (smartscalar)               |

---

## Per-Requirement Comparison

| Req #  | Requirement Question                                           | Your Card Name                                                                      | Your Approach                                                                                                                                                                                                                                                                                      | Automated Approach                                                                                                                                                                                             | Key Differences                                                                                                                                                                                                                                   |
| ------ | -------------------------------------------------------------- | ----------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **01** | How often do users sort columns on the storage container list? | "Use of sorting on columns" (card #76)                                              | **MBQL** · Query Builder from model #73 · Filter: `ACTION_TYPE starts with "sort_column"` + `PAGE_SECTION = storage_container.eb` · Group by: `ACTION_TYPE` · Viz: **Pie chart** (on dashboard, overridden from card's bar) with custom labels renaming `sort_column.X` → `X` in pie segment names | **SQL** · `REGEXP_SUBSTR(ACTION_TYPE, '[^.]+$')` to strip prefix · Filter: `LIKE 'sort\_column.%'` + `PAGE_SECTION` + `DESTINATION_NAME` · Group by: cleaned column name · Viz: **Row chart** (horizontal bar) | You used a pie chart with raw `sort_column.*` values as labels; I stripped the prefix in SQL for cleaner labels and used a row chart for ranking. You did NOT filter on `DESTINATION_NAME`.                                                       |
| **02** | How often do users click row links (cluster names)?            | "Use of links in rows" (card #77)                                                   | **MBQL** · Filter: `ACTION_TYPE IN ('container_name.click', 'cluster_name.click')` + `PAGE_SECTION = storage_container.eb` · Group by: `ACTION_TYPE` · Viz: **Bar chart** (vertical)                                                                                                               | **SQL** · Filter: `ACTION_TYPE = 'container_name.click'` + `PAGE_SECTION` + `SUB_PAGE_SECTION = eb_list` + `DESTINATION_NAME` · Group by: `WEEK` · Viz: **Line chart** (time series)                           | You included `cluster_name.click` as an additional event (broader scope). You showed a category breakdown (bar), not a time trend. I showed weekly trend with stricter filters (`SUB_PAGE_SECTION`, `DESTINATION_NAME`).                          |
| **03** | How often do users select checkboxes (multi-entity intent)?    | "Checkbox Clicks" (card #78)                                                        | **MBQL** · Filter: `ACTION_TYPE = listview.select` + `PAGE_SECTION = storage_container.eb` · No breakout (aggregate only) · Viz: **Scalar** (single number)                                                                                                                                        | **SQL** · Same filters + `SUB_PAGE_SECTION = eb_list` + `DESTINATION_NAME = storage_container/list` · Group by: `WEEK` · Viz: **Line chart** (time series)                                                     | You showed a single total count (scalar). I showed a weekly trend line. You omitted `SUB_PAGE_SECTION` and `DESTINATION_NAME` filters.                                                                                                            |
| **04** | How often do users change column views?                        | "View By" (card #137)                                                               | **MBQL** · Filter: `PAGE_SECTION = storage_container.eb` + `SUB_PAGE_SECTION = view_by_dropdown` + `DESTINATION_NAME = "Storage Containers"/List` + `ACTION_TYPE contains "General", "Performance", "Optimization"` · Group by: `ACTION_TYPE` · Viz: **Bar chart**                                 | **SQL** · Filter: `PAGE_SECTION = storage_container.eb` + `SUB_PAGE_SECTION = view_by_dropdown` + `DESTINATION_NAME ILIKE '%Storage Containers%'` · Group by: `WEEK` · Viz: **Line chart** (time series)       | You filtered ACTION_TYPE to only known view names (`General`, `Performance`, `Optimization`) — this is a curated list. I captured ALL view changes as a time series without restricting action types. You grouped by category; I grouped by time. |
| **05** | Do users create custom views?                                  | _(Not a separate card — subsumed into card #137's scope or not explicitly present)_ | Not explicitly addressed as a standalone widget. The "View By" card captures all view_by_dropdown interactions including custom views, but doesn't isolate "custom" views specifically.                                                                                                            | **SQL** · Filter: same as #04 but adds `ACTION_TYPE ILIKE '%custom%'` · Group by: `WEEK` · Viz: **Trend** (smartscalar with period-over-period delta)                                                          | You did not create a dedicated custom-view widget. I isolated custom views with an `ILIKE '%custom%'` filter and used a trend card to show whether adoption is growing.                                                                           |

---

## Additional Cards in Your Dashboard (Beyond Rows 01–05)

| Your Card Name                     | Card ID | Maps to Req #                                 | Approach                                                                                                                       | Viz           |
| ---------------------------------- | ------- | --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ | ------------- |
| "Multiselect Actions"              | #135    | Row 5 · Q1 (Req #11)                          | MBQL · Filter: `listview.select` + all 4 filter columns · Group by: `TIMESTAMP` (month) · Line chart                           | Line          |
| "Grouped By"                       | #138    | Row 3 · Q1 (Req #07)                          | MBQL · Filter: `ACTION_TYPE contains` specific group-by values + `group_by_dropdown` · Group by: `ACTION_TYPE` · Bar chart     | Bar           |
| "Filter Usage"                     | #139    | Row 4 · Q1 (Req #09)                          | MBQL · Filter: `ACTION_TYPE starts with "filter"` + `list_filter` + `DESTINATION_NAME` · Group by: `ACTION_TYPE` · Pie chart   | Pie           |
| "Update flow field interaction"    | #140    | Row 6 · Q1 (Req #12)                          | MBQL · Filter: `input_change.` + `update_storage_container` · Group by: `ACTION_TYPE` · Table                                  | Table         |
| "Create Flow field interaction"    | #89     | Row 7 · Q2 (Req #14)                          | MBQL · Filter: `input_change` + `create_storage_container` + `storage_container/create_form` · Group by: `ACTION_TYPE` · Table | Table         |
| "Tooltip usage"                    | #141    | Row 7 · Q5 (Req #17)                          | MBQL · Filter: `ACTION_TYPE = advertised_capacity.tooltip` + `create_storage_container` · Scalar (single number: 686)          | Scalar        |
| "Replication factor tooltip usage" | #142    | Row 7 · Q5 (Req #17, part 2)                  | MBQL · Filter: `ACTION_TYPE = replication_factor.tooltip` + `create_storage_container` · Scalar (single number: 464)           | Scalar        |
| "Modal Help icon usage"            | #144    | Row 7 · Q6 (Req #18)                          | MBQL · Filter: `ACTION_TYPE = help_icon.click` + `SUB_PAGE_SECTION = modal_header` · Scalar                                    | Scalar        |
| "Create Storage Container"         | #143    | Row 7 · Q7-Q8 (Req #13 funnel + Req #20 time) | **Native SQL** · Funnel with 2 steps: opened form → clicked save · `COUNT(DISTINCT SESSION_ID)` per step                       | Funnel        |
| "Create flow time taken"           | #145    | Row 7 · Q8 (Req #20)                          | **Native SQL** · CTE pairing start/save events · `AVG`, `MEDIAN`, `MIN`, `MAX` duration in minutes                             | Object/Detail |
| "Update flow time taken"           | #146    | _(extra, not in first 21 reqs)_               | **Native SQL** · Same pattern as create flow but for update flow                                                               | Object/Detail |

---

## Key Takeaways

1. **Model as source vs direct table** — You built your widgets on top of a pre-filtered model (card #73), giving you a cleaner data-picker experience and centralized filter logic. The automated approach queries the raw flat table directly.

2. **Category breakdown vs time trend** — For requirements 01–04, you primarily answered "what are the most used X?" (category bars/pies), while the automated approach more often answered "how is usage trending over time?" (weekly line charts). Both are valid interpretations of "how often" — yours shows proportion, mine shows trajectory.

3. **Filter precision** — You generally used 2 filter columns (`ACTION_TYPE` + `PAGE_SECTION`). The automated approach used 3–4 filter columns (adding `SUB_PAGE_SECTION` + `DESTINATION_NAME`) for stricter scoping. This could mean the automated approach returns fewer results but with higher confidence in relevance.

4. **Label cleaning** — You kept raw `ACTION_TYPE` values in most charts (e.g., `sort_column.cluster_name`). The automated approach stripped prefixes via `REGEXP_SUBSTR` or `ILIKE` for cleaner user-facing labels.

5. **Visualization choices** — You used pie charts for distributions (sorting, filters) which work well for showing relative proportions. The automated approach preferred row charts (horizontal bars) for ranked lists — better for readability with longer labels.

6. **Dashboard-level filter** — Your dashboard has a temporal-unit parameter (`?time=month`) that applies globally. The automated dashboard has no such parameter — each card is self-contained with its own time grouping.

7. **Scope** — You covered significantly more ground (13 cards spanning ~12 distinct requirements + extras like time-to-complete), while the automated run only processed the first 5 rows as requested.

8. **Complex analytics** — For funnel and time-between-events questions (Reqs #13, #20), you correctly used native SQL with CTEs (`TIMESTAMPDIFF`, `COUNT(DISTINCT SESSION_ID)`) — the same tier the skill would recommend (Tier 3). This shows alignment on when SQL is necessary.
