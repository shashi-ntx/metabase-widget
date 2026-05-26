# Storage Container Telemetry — Widget Specs

Source file: `storage telemetry requirement.csv` · **21 logical requirements** from 7 input rows.

The **summary table** gives a scannable overview of every widget (type, tier, grid size, key telemetry fields). The **detailed table** below it has full paste-ready Query Builder / SQL specs for both the Suggested and Alternative approaches. Each spec includes a **SQL equivalent** block for API-based card creation and the **Grid size** for dashboard placement.

---

## Summary

| #   | Source row | Page / Subpage                              | Question                                                                  | Suggested Widget                            | Alternative Widget                                                    | Grid Size | Telemetry Payload                                                                                                                                    |
| --- | ---------- | ------------------------------------------- | ------------------------------------------------------------------------- | ------------------------------------------- | --------------------------------------------------------------------- | --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| 01  | Row 1 · Q1 | Storage Container - List / Table            | Which columns do users sort on most?                                      | Tier 2 · Pie chart                          | Tier 2 · Line chart                                                   | 12 × 8    | `actionType: sort_column.<column key>`, `pageSection: storage_container.eb`, `destinationName: storage_container/list`                               |
| 02  | Row 1 · Q2 | Storage Container - List / Table            | How often do users click row links in the list?                           | Tier 1 · Bar chart (grouped by month)       | Tier 1 · Line chart                                                   | 12 × 8    | `actionType: container_name.click / cluster_name.click`, `pageSection: storage_container.eb`, `destinationName: storage_container/list`              |
| 03  | Row 1 · Q3 | Storage Container - List / Table            | How often do users select checkboxes for multi-entity actions?            | Tier 1 · Line chart                         | Tier 1 · Scalar (trend)                                               | 12 × 7    | `actionType: listview.select`, `pageSection: storage_container.eb`, `subPageSection: eb_list`, `destinationName: storage_container/list`             |
| 04  | Row 2 · Q1 | Storage Container - List / View By          | How often do users change column views?                                   | Tier 1 · Line chart                         | Tier 1 · Scalar (trend)                                               | 12 × 7    | `actionType: <selected view>`, `pageSection: storage_container.eb`, `subPageSection: view_by_dropdown`, `destinationName: "Storage Containers"/List` |
| 05  | Row 2 · Q2 | Storage Container - List / View By          | Do users create custom views?                                             | Tier 1 · Scalar (trend)                     | Tier 1 · Line chart                                                   | 6 × 5     | `actionType: <custom view action>`, `pageSection: storage_container.eb`, `subPageSection: view_by_dropdown`                                          |
| 06  | Row 2 · Q3 | Storage Container - List / View By          | What columns are added the most in custom views?                          | Tier 1 · Row chart                          | Tier 1 · Pie chart                                                    | 12 × 7    | `actionType: <selected view>`, `pageSection: storage_container.eb`, `subPageSection: view_by_dropdown`                                               |
| 07  | Row 3 · Q1 | Storage Container - List / Group By         | What are the most used group-by values?                                   | Tier 1 · Row chart                          | Tier 1 · Pie chart                                                    | 12 × 7    | `actionType: <selected group-by>`, `pageSection: storage_container.eb`, `subPageSection: group_by_dropdown`                                          |
| 08  | Row 3 · Q2 | Storage Container - List / Group By         | How often do users change group-by values?                                | Tier 1 · Line chart                         | Tier 1 · Scalar (trend)                                               | 12 × 7    | `actionType: <selected group-by>`, `pageSection: storage_container.eb`, `subPageSection: group_by_dropdown`                                          |
| 09  | Row 4 · Q1 | Storage Container - List / Filter           | What are the most commonly used filters?                                  | Tier 2 · Pie chart                          | Tier 2 · Row chart                                                    | 12 × 8    | `actionType: filter.<filter name>`, `pageSection: storage_container.eb`, `subPageSection: list_filter`, `destinationName: storage_container/list`    |
| 10  | Row 4 · Q2 | Storage Container - List / Filter           | How often do users interact with filters?                                 | Tier 1 · Line chart                         | Tier 1 · Scalar (trend)                                               | 12 × 7    | `actionType: filter.<filter name>`, `pageSection: storage_container.eb`, `subPageSection: list_filter`, `destinationName: storage_container/list`    |
| 11  | Row 5 · Q1 | Storage Container - List / Actions          | Do users select multiple entities before clicking on Actions?             | Tier 1 · Scalar (trend)                     | Tier 1 · Line chart                                                   | 6 × 5     | `actionType: listview.select`, `pageSection: storage_container.eb`, `subPageSection: eb_list`, `destinationName: storage_container/list`             |
| 12  | Row 6 · Q1 | Storage Container - List / Actions : Update | What are the fields users interact with most in the Update form?          | Tier 2 · Pie chart                          | Tier 2 · Row chart                                                    | 12 × 8    | `actionType: input_change.<input key>`, `pageSection: update_storage_container`, `destinationName: storage_container/update_form`                    |
| 13  | Row 7 · Q1 | Storage Container - Create                  | How frequently are users creating a storage container?                    | Tier 1 · Line chart                         | Tier 1 · Scalar (trend)                                               | 12 × 7    | `actionType: create_storage_container.start`, `pageSection: storage_container.eb`, `subPageSection: actions_view`                                    |
| 14  | Row 7 · Q2 | Storage Container - Create                  | What advanced-settings options are used the most?                         | Tier 2 · Pie chart                          | Tier 2 · Row chart                                                    | 12 × 8    | `actionType: input_change.<input key>`, `pageSection: create_storage_container`, `destinationName: storage_container/create_form`                    |
| 15  | Row 7 · Q3 | Storage Container - Create                  | Do users interact with reserved capacity and advertised capacity fields?  | Tier 1 · Bar chart (grouped by month)       | Tier 1 · Line chart                                                   | 12 × 8    | `actionType: input_change.reserved_capacity / input_change.advertised_capacity`, `pageSection: create_storage_container`                             |
| 16  | Row 7 · Q4 | Storage Container - Create                  | Do users interact with Filesystem Allowlists?                             | Tier 1 · Scalar (trend)                     | Tier 1 · Line chart                                                   | 6 × 5     | `actionType: input_change.filesystem*`, `pageSection: create_storage_container`                                                                      |
| 17  | Row 7 · Q5 | Storage Container - Create                  | Do users interact with the tooltip icons beside properties?               | Tier 1 · Bar chart (grouped by month)       | Tier 1 · Line chart                                                   | 12 × 8    | `actionType: *.tooltip`, `pageSection: create_storage_container`                                                                                     |
| 18  | Row 7 · Q6 | Storage Container - Create                  | Do users interact with the [?] help icon on the header?                   | Tier 1 · Scalar (trend)                     | Tier 1 · Line chart                                                   | 6 × 5     | `actionType: header.help*`, `pageSection: create_storage_container`                                                                                  |
| 19  | Row 7 · Q7 | Storage Container - Create                  | Do users click X or Cancel to close the modal without changes?            | Tier 1 · Bar chart (grouped by month)       | Tier 1 · Line chart                                                   | 12 × 8    | `actionType: modal.close / modal.cancel`, `pageSection: create_storage_container`                                                                    |
| 20  | Row 7 · Q8 | Storage Container - Create                  | How much time does the user spend creating the storage container?         | Tier 3 · Line chart (avg duration by month) | Tier 3 · Bar chart (grouped by month, with/without advanced settings) | 12 × 7    | `actionType: create_storage_container.start + .submit`, `pageSection: create_storage_container`                                                      |
| 21  | Row 7 · Q9 | Storage Container - Create                  | Do users hover or click the information banner around Replication Factor? | Tier 1 · Scalar (trend)                     | Tier 1 · Line chart                                                   | 6 × 5     | `actionType: replication_factor.*`, `pageSection: create_storage_container`                                                                          |

---

## Detailed Widget Specs

### 01 — Column Sorting Distribution

> "Which columns do users sort on most in the storage container list?"
>
> Shows which table columns attract the most sorting activity, revealing data-access priorities.

**Suggested Approach (Tier 2 · Pie chart)**

**Pick data:** Nusights Events Activitytype Default Historical Tbl Flat

**Custom columns:**

- `Sorted Column` = `regexextract([Action Type], "[^.]+$")`

**Filter:**

- `Page Section` is `storage_container.eb`
- `Action Type` starts with `sort_column.`
- `Destination Name` is `storage_container/list`

**Summarize:**

- Metric: Count of rows
- Group by: `Sorted Column`

**Sort:** Count descending

**Visualization:** Pie chart with segment labels showing name and percentage. Sorting distribution is a composition question — pie makes the dominant columns immediately visible.

**Grid size:** 12 × 8

**Why these filters:** `starts with sort_column.` isolates sorting events; `pageSection` + `destinationName` scope to the list page.

**SQL equivalent (used for API creation):**

```sql
SELECT
  REGEXP_SUBSTR(ACTION_TYPE, '[^.]+$') AS SORTED_COLUMN,
  COUNT(*) AS TOTAL_SORTS
FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
WHERE PAGE_SECTION = 'storage_container.eb'
  AND ACTION_TYPE LIKE 'sort_column.%'
  AND DESTINATION_NAME = 'storage_container/list'
GROUP BY SORTED_COLUMN
ORDER BY TOTAL_SORTS DESC
```

---

**Alternative Approach (Tier 2 · Line chart)**

**Title:** Column Sorting Trend

**Pick data:** Nusights Events Activitytype Default Historical Tbl Flat

**Custom columns:**

- `Sorted Column` = `regexextract([Action Type], "[^.]+$")`

**Filter:**

- `Page Section` is `storage_container.eb`
- `Action Type` starts with `sort_column.`
- `Destination Name` is `storage_container/list`

**Summarize:**

- Metric: Count of rows
- Group by: `Sorted Column`, `Timestamp` (Month)

**Visualization:** Line chart with one series per sorted column. Shows whether certain columns gain or lose sorting popularity over time.

**Grid size:** 12 × 7

---

### 02 — Row Link Clicks by Entity

> "How often do users click row links (e.g. container name, cluster name) in the storage container list?"
>
> Shows which clickable entities in the table get the most clicks and how the pattern evolves over time.

**Suggested Approach (Tier 1 · Bar chart, grouped by month)**

**Pick data:** Nusights Events Activitytype Default Historical Tbl Flat

**Filter:**

- `Page Section` is `storage_container.eb`
- `Action Type` is any of `container_name.click`, `cluster_name.click`
- `Destination Name` is `storage_container/list`

**Summarize:**

- Metric: Count of rows
- Group by: `Timestamp` (Month), `Action Type`

**Visualization:** Bar chart (vertical, grouped) with months on the x-axis and one colored bar per entity per month. Shows both relative magnitude and temporal trends side-by-side — the viewer can see which entity is clicked more and whether that pattern is shifting over time.

**Grid size:** 12 × 8

**Why these filters:** Multi-value filter on `Action Type` captures all row-link click events (container name, cluster name). Grouping by `Timestamp` + `Action Type` creates the monthly comparison.

**SQL equivalent (used for API creation):**

```sql
SELECT
  DATE_TRUNC('month', TIMESTAMP) AS MONTH,
  REPLACE(REPLACE(ACTION_TYPE, '.click', ''), '_', ' ') AS LINK_TYPE,
  COUNT(*) AS TOTAL_CLICKS
FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
WHERE PAGE_SECTION = 'storage_container.eb'
  AND ACTION_TYPE LIKE '%.click'
  AND DESTINATION_NAME = 'storage_container/list'
GROUP BY MONTH, LINK_TYPE
ORDER BY MONTH
```

---

**Alternative Approach (Tier 1 · Line chart)**

**Title:** Row Link Clicks Over Time

**Pick data:** Nusights Events Activitytype Default Historical Tbl Flat

**Filter:**

- `Page Section` is `storage_container.eb`
- `Action Type` is any of `container_name.click`, `cluster_name.click`
- `Destination Name` is `storage_container/list`

**Summarize:**

- Metric: Count of rows
- Group by: `Action Type`, `Timestamp` (Month)

**Visualization:** Line chart with one series per entity. Shows how click patterns for each entity trend over time — useful if you prefer trend lines over side-by-side bars.

**Grid size:** 12 × 7

---

### 03 — Checkbox Selections Over Time

> "How often do users select checkboxes to perform multi-entity actions in the storage container list?"
>
> Shows the adoption trend of bulk-selection behavior, indicating multi-entity action intent.

**Suggested Approach (Tier 1 · Line chart)**

**Pick data:** Nusights Events Activitytype Default Historical Tbl Flat

**Filter:**

- `Page Section` is `storage_container.eb`
- `Action Type` is `listview.select`
- `Destination Name` is `storage_container/list`

**Summarize:**

- Metric: Count of rows
- Group by: `Timestamp` (Month)

**Visualization:** Line chart grouped by month. "How often" implies a time-series — line chart shows the adoption trajectory of checkbox usage.

**Grid size:** 12 × 7

**Why these filters:** `listview.select` captures every checkbox toggle; scoped to the list page.

**SQL equivalent (used for API creation):**

```sql
SELECT
  DATE_TRUNC('month', TIMESTAMP) AS MONTH,
  COUNT(*) AS TOTAL_SELECTIONS
FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
WHERE PAGE_SECTION = 'storage_container.eb'
  AND ACTION_TYPE = 'listview.select'
  AND DESTINATION_NAME = 'storage_container/list'
GROUP BY MONTH
ORDER BY MONTH
```

---

**Alternative Approach (Tier 1 · Scalar/Trend)**

**Title:** Total Checkbox Selections

**Visualization:** Trend (scalar + previous-period delta). Quick pulse on whether bulk-selection is actively used.

**Grid size:** 6 × 5

---

### 04 — View Changes Over Time

> "How often do users change column views in the storage container list?"
>
> Shows the frequency trend of view switching, indicating whether users explore different data arrangements.

**Suggested Approach (Tier 1 · Line chart)**

**Pick data:** Nusights Events Activitytype Default Historical Tbl Flat

**Filter:**

- `Page Section` is `storage_container.eb`
- `Sub Page Section` is `view_by_dropdown`

**Summarize:**

- Metric: Count of rows
- Group by: `Timestamp` (Month)

**Visualization:** Line chart grouped by month. "How often" implies a time dimension.

**Grid size:** 12 × 7

**Why these filters:** `subPageSection: view_by_dropdown` scopes to all view-selection events regardless of which view was chosen.

**SQL equivalent (used for API creation):**

```sql
SELECT
  DATE_TRUNC('month', TIMESTAMP) AS MONTH,
  COUNT(*) AS TOTAL_CHANGES
FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
WHERE PAGE_SECTION = 'storage_container.eb'
  AND SUB_PAGE_SECTION = 'view_by_dropdown'
GROUP BY MONTH
ORDER BY MONTH
```

---

**Alternative Approach (Tier 1 · Scalar/Trend)**

**Title:** Total View Changes

**Visualization:** Trend (scalar + previous-period delta).

**Grid size:** 6 × 5

---

### 05 — Custom View Creations

> "Do users create custom views in the storage container list?"
>
> Answers whether the custom-view feature is being adopted at all.

**Suggested Approach (Tier 1 · Scalar/Trend)**

**Pick data:** Nusights Events Activitytype Default Historical Tbl Flat

**Filter:**

- `Page Section` is `storage_container.eb`
- `Sub Page Section` is `view_by_dropdown`
- `Action Type` contains `custom`

**Summarize:**

- Metric: Count of rows

**Visualization:** Trend (scalar + previous-period delta). "Do users...?" is a binary-existence question — zero means no, non-zero means yes.

**Grid size:** 6 × 5

**Why these filters:** `contains custom` isolates custom-view creation events from standard view selections. **Note:** Verify the exact `actionType` value.

**SQL equivalent (used for API creation):**

```sql
SELECT
  DATE_TRUNC('month', TIMESTAMP) AS MONTH,
  COUNT(*) AS TOTAL_CREATIONS
FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
WHERE PAGE_SECTION = 'storage_container.eb'
  AND SUB_PAGE_SECTION = 'view_by_dropdown'
  AND ACTION_TYPE ILIKE '%custom%'
GROUP BY MONTH
ORDER BY MONTH
```

---

**Alternative Approach (Tier 1 · Line chart)**

**Title:** Custom View Creations Over Time

**Visualization:** Line chart grouped by month. If adoption exists, shows whether it's growing, flat, or declining.

**Grid size:** 12 × 7

---

### 06 — Most Added Columns in Custom Views

> "What columns are sought or added the most in custom views?"
>
> Reveals which data columns users value enough to add to their custom view configurations.

**Suggested Approach (Tier 1 · Row chart)**

**Pick data:** Nusights Events Activitytype Default Historical Tbl Flat

**Filter:**

- `Page Section` is `storage_container.eb`
- `Sub Page Section` is `view_by_dropdown`

**Summarize:**

- Metric: Count of rows
- Group by: `Action Type`

**Sort:** Count descending

**Row limit:** 15

**Visualization:** Row chart (horizontal bar), sorted descending. "Most added" is a ranking question — row chart puts the top column at the top with readable labels.

**Grid size:** 12 × 7

**Why these filters:** Grouping by `Action Type` surfaces each selected view/column name.

**SQL equivalent (used for API creation):**

```sql
SELECT
  ACTION_TYPE AS VIEW_COLUMN,
  COUNT(*) AS TOTAL_SELECTIONS
FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
WHERE PAGE_SECTION = 'storage_container.eb'
  AND SUB_PAGE_SECTION = 'view_by_dropdown'
GROUP BY ACTION_TYPE
ORDER BY TOTAL_SELECTIONS DESC
LIMIT 15
```

---

**Alternative Approach (Tier 1 · Pie chart)**

**Title:** Column Selection Distribution in Views

**Visualization:** Pie chart with segment labels. Composition view — highlights whether one column dominates or usage is evenly spread.

**Grid size:** 12 × 8

---

### 07 — Most Used Group-By Values

> "What are the most used group-by values in the storage container list?"
>
> Reveals which grouping dimensions users prefer, informing default configurations.

**Suggested Approach (Tier 1 · Row chart)**

**Pick data:** Nusights Events Activitytype Default Historical Tbl Flat

**Filter:**

- `Page Section` is `storage_container.eb`
- `Sub Page Section` is `group_by_dropdown`

**Summarize:**

- Metric: Count of rows
- Group by: `Action Type`

**Sort:** Count descending

**Row limit:** 15

**Visualization:** Row chart (horizontal bar), sorted descending. "Most used" is a ranking question.

**Grid size:** 12 × 7

**Why these filters:** `subPageSection: group_by_dropdown` isolates group-by selection events.

**SQL equivalent (used for API creation):**

```sql
SELECT
  ACTION_TYPE AS GROUP_BY_VALUE,
  COUNT(*) AS TOTAL_SELECTIONS
FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
WHERE PAGE_SECTION = 'storage_container.eb'
  AND SUB_PAGE_SECTION = 'group_by_dropdown'
GROUP BY ACTION_TYPE
ORDER BY TOTAL_SELECTIONS DESC
LIMIT 15
```

---

**Alternative Approach (Tier 1 · Pie chart)**

**Title:** Group-By Value Distribution

**Visualization:** Pie chart with segment labels. Composition view.

**Grid size:** 12 × 8

---

### 08 — Group-By Changes Over Time

> "How often do users change group-by values in the storage container list?"
>
> Shows the trend of group-by switching activity.

**Suggested Approach (Tier 1 · Line chart)**

**Pick data:** Nusights Events Activitytype Default Historical Tbl Flat

**Filter:**

- `Page Section` is `storage_container.eb`
- `Sub Page Section` is `group_by_dropdown`

**Summarize:**

- Metric: Count of rows
- Group by: `Timestamp` (Month)

**Visualization:** Line chart grouped by month.

**Grid size:** 12 × 7

**Why these filters:** Captures all group-by selections regardless of value; time grouping shows frequency trend.

**SQL equivalent (used for API creation):**

```sql
SELECT
  DATE_TRUNC('month', TIMESTAMP) AS MONTH,
  COUNT(*) AS TOTAL_CHANGES
FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
WHERE PAGE_SECTION = 'storage_container.eb'
  AND SUB_PAGE_SECTION = 'group_by_dropdown'
GROUP BY MONTH
ORDER BY MONTH
```

---

**Alternative Approach (Tier 1 · Scalar/Trend)**

**Title:** Total Group-By Changes

**Visualization:** Trend (scalar + previous-period delta).

**Grid size:** 6 × 5

---

### 09 — Most Used Filters

> "What are the most commonly used filters in the storage container list?"
>
> Shows each filter's share of total filter interactions, revealing which data-narrowing options users rely on.

**Suggested Approach (Tier 2 · Pie chart)**

**Pick data:** Nusights Events Activitytype Default Historical Tbl Flat

**Custom columns:**

- `Filter Name` = `regexextract([Action Type], "[^.]+$")`

**Filter:**

- `Page Section` is `storage_container.eb`
- `Action Type` starts with `filter.`
- `Sub Page Section` is `list_filter`
- `Destination Name` is `storage_container/list`

**Summarize:**

- Metric: Count of rows
- Group by: `Filter Name`

**Sort:** Count descending

**Visualization:** Pie chart with segment labels showing name and percentage. Composition question — shows each filter's proportional share.

**Grid size:** 12 × 8

**Why these filters:** `starts with filter.` isolates filter interactions; `regexextract` strips the prefix for clean labels.

**SQL equivalent (used for API creation):**

```sql
SELECT
  REGEXP_SUBSTR(ACTION_TYPE, '[^.]+$') AS FILTER_NAME,
  COUNT(*) AS TOTAL_USES
FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
WHERE PAGE_SECTION = 'storage_container.eb'
  AND ACTION_TYPE LIKE 'filter.%'
  AND SUB_PAGE_SECTION = 'list_filter'
  AND DESTINATION_NAME = 'storage_container/list'
GROUP BY FILTER_NAME
ORDER BY TOTAL_USES DESC
```

---

**Alternative Approach (Tier 2 · Row chart)**

**Title:** Filter Usage Ranking

**Visualization:** Row chart (horizontal bar), sorted descending. Ranking view.

**Grid size:** 12 × 7

---

### 10 — Filter Interactions Over Time

> "How often do users interact with filters in the storage container list?"
>
> Shows the monthly trend of filter usage.

**Suggested Approach (Tier 1 · Line chart)**

**Pick data:** Nusights Events Activitytype Default Historical Tbl Flat

**Filter:**

- `Page Section` is `storage_container.eb`
- `Action Type` starts with `filter.`
- `Sub Page Section` is `list_filter`
- `Destination Name` is `storage_container/list`

**Summarize:**

- Metric: Count of rows
- Group by: `Timestamp` (Month)

**Visualization:** Line chart grouped by month. "How often" implies a time-series.

**Grid size:** 12 × 7

**Why these filters:** `starts with filter.` captures all filter interactions.

**SQL equivalent (used for API creation):**

```sql
SELECT
  DATE_TRUNC('month', TIMESTAMP) AS MONTH,
  COUNT(*) AS TOTAL_INTERACTIONS
FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
WHERE PAGE_SECTION = 'storage_container.eb'
  AND ACTION_TYPE LIKE 'filter.%'
  AND SUB_PAGE_SECTION = 'list_filter'
  AND DESTINATION_NAME = 'storage_container/list'
GROUP BY MONTH
ORDER BY MONTH
```

---

**Alternative Approach (Tier 1 · Scalar/Trend)**

**Title:** Total Filter Interactions

**Visualization:** Trend (scalar + previous-period delta).

**Grid size:** 6 × 5

---

### 11 — Multi-Entity Selections

> "Do users select multiple entities before clicking on Actions?"
>
> Shows whether bulk-action selection is actively used.

**Suggested Approach (Tier 1 · Scalar/Trend)**

**Pick data:** Nusights Events Activitytype Default Historical Tbl Flat

**Filter:**

- `Page Section` is `storage_container.eb`
- `Action Type` is `listview.select`
- `Destination Name` is `storage_container/list`

**Summarize:**

- Metric: Count of rows

**Visualization:** Trend (scalar + previous-period delta). "Do users...?" is a binary-existence question.

**Grid size:** 6 × 5

**Why these filters:** `listview.select` fires on each checkbox toggle.

**SQL equivalent (used for API creation):**

```sql
SELECT
  DATE_TRUNC('month', TIMESTAMP) AS MONTH,
  COUNT(*) AS TOTAL_SELECTIONS
FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
WHERE PAGE_SECTION = 'storage_container.eb'
  AND ACTION_TYPE = 'listview.select'
  AND DESTINATION_NAME = 'storage_container/list'
GROUP BY MONTH
ORDER BY MONTH
```

---

**Alternative Approach (Tier 1 · Line chart)**

**Title:** Multi-Entity Selections Over Time

**Visualization:** Line chart grouped by month.

**Grid size:** 12 × 7

---

### 12 — Most Interacted Update Form Fields

> "What are the fields that users interact with most in the Update Storage Container form?"
>
> Shows each form field's share of interaction, revealing which properties users change most during updates.

**Suggested Approach (Tier 2 · Pie chart)**

**Pick data:** Nusights Events Activitytype Default Historical Tbl Flat

**Custom columns:**

- `Field Name` = `regexextract([Action Type], "[^.]+$")`

**Filter:**

- `Page Section` is `update_storage_container`
- `Action Type` starts with `input_change.`
- `Destination Name` is `storage_container/update_form`

**Summarize:**

- Metric: Count of rows
- Group by: `Field Name`

**Sort:** Count descending

**Visualization:** Pie chart with segment labels showing name and percentage.

**Grid size:** 12 × 8

**Why these filters:** `starts with input_change.` isolates field-change events; `regexextract` strips the prefix.

**SQL equivalent (used for API creation):**

```sql
SELECT
  REGEXP_SUBSTR(ACTION_TYPE, '[^.]+$') AS FIELD_NAME,
  COUNT(*) AS TOTAL_INTERACTIONS
FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
WHERE PAGE_SECTION = 'update_storage_container'
  AND ACTION_TYPE LIKE 'input_change.%'
  AND DESTINATION_NAME = 'storage_container/update_form'
GROUP BY FIELD_NAME
ORDER BY TOTAL_INTERACTIONS DESC
```

---

**Alternative Approach (Tier 2 · Row chart)**

**Title:** Update Form Field Ranking

**Visualization:** Row chart (horizontal bar), sorted descending.

**Grid size:** 12 × 7

---

### 13 — Storage Container Creations Over Time

> "How frequently are users creating a storage container?"
>
> Shows the monthly creation trend.

**Suggested Approach (Tier 1 · Line chart)**

**Pick data:** Nusights Events Activitytype Default Historical Tbl Flat

**Filter:**

- `Page Section` is `storage_container.eb`
- `Action Type` is `create_storage_container.start`

**Summarize:**

- Metric: Count of rows
- Group by: `Timestamp` (Month)

**Visualization:** Line chart grouped by month.

**Grid size:** 12 × 7

**Why these filters:** `create_storage_container.start` captures every creation initiation.

**SQL equivalent (used for API creation):**

```sql
SELECT
  DATE_TRUNC('month', TIMESTAMP) AS MONTH,
  COUNT(*) AS TOTAL_CREATIONS
FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
WHERE PAGE_SECTION = 'storage_container.eb'
  AND ACTION_TYPE = 'create_storage_container.start'
GROUP BY MONTH
ORDER BY MONTH
```

---

**Alternative Approach (Tier 1 · Scalar/Trend)**

**Title:** Total Storage Container Creations

**Visualization:** Trend (scalar + previous-period delta).

**Grid size:** 6 × 5

---

### 14 — Most Used Advanced Settings

> "What advanced-settings options are used the most during storage container creation?"
>
> Shows which advanced configuration options users engage with.

**Suggested Approach (Tier 2 · Pie chart)**

**Pick data:** Nusights Events Activitytype Default Historical Tbl Flat

**Custom columns:**

- `Setting Name` = `regexextract([Action Type], "[^.]+$")`

**Filter:**

- `Page Section` is `create_storage_container`
- `Action Type` starts with `input_change.`
- `Destination Name` is `storage_container/create_form`

**Summarize:**

- Metric: Count of rows
- Group by: `Setting Name`

**Sort:** Count descending

**Visualization:** Pie chart with segment labels.

**Grid size:** 12 × 8

**Why these filters:** `starts with input_change.` captures all field-change events in the create form.

**SQL equivalent (used for API creation):**

```sql
SELECT
  REGEXP_SUBSTR(ACTION_TYPE, '[^.]+$') AS SETTING_NAME,
  COUNT(*) AS TOTAL_INTERACTIONS
FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
WHERE PAGE_SECTION = 'create_storage_container'
  AND ACTION_TYPE LIKE 'input_change.%'
  AND DESTINATION_NAME = 'storage_container/create_form'
GROUP BY SETTING_NAME
ORDER BY TOTAL_INTERACTIONS DESC
```

---

**Alternative Approach (Tier 2 · Row chart)**

**Title:** Advanced Settings Interaction Ranking

**Visualization:** Row chart (horizontal bar), sorted descending.

**Grid size:** 12 × 7

---

### 15 — Reserved vs Advertised Capacity Interactions

> "Do users interact with the reserved capacity and advertised capacity fields during storage container creation?"
>
> Shows whether both capacity fields see engagement and how the pattern evolves over time.

**Suggested Approach (Tier 1 · Bar chart, grouped by month)**

**Pick data:** Nusights Events Activitytype Default Historical Tbl Flat

**Filter:**

- `Page Section` is `create_storage_container`
- `Action Type` is any of `input_change.reserved_capacity`, `input_change.advertised_capacity`
- `Destination Name` is `storage_container/create_form`

**Summarize:**

- Metric: Count of rows
- Group by: `Timestamp` (Month), `Action Type`

**Visualization:** Bar chart (vertical, grouped) with months on the x-axis and one colored bar per capacity field per month. Shows both relative magnitude and temporal trends — the viewer can see which capacity field is used more and whether usage is growing or declining.

**Grid size:** 12 × 8

**Why these filters:** Multi-value filter captures both capacity events. Grouping by `Timestamp` + `Action Type` creates the monthly comparison.

**SQL equivalent (used for API creation):**

```sql
SELECT
  DATE_TRUNC('month', TIMESTAMP) AS MONTH,
  CASE
    WHEN ACTION_TYPE = 'input_change.reserved_capacity' THEN 'Reserved Capacity'
    WHEN ACTION_TYPE = 'input_change.advertised_capacity' THEN 'Advertised Capacity'
  END AS CAPACITY_TYPE,
  COUNT(*) AS TOTAL_INTERACTIONS
FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
WHERE PAGE_SECTION = 'create_storage_container'
  AND ACTION_TYPE IN ('input_change.reserved_capacity', 'input_change.advertised_capacity')
  AND DESTINATION_NAME = 'storage_container/create_form'
GROUP BY MONTH, CAPACITY_TYPE
ORDER BY MONTH
```

---

**Alternative Approach (Tier 1 · Line chart)**

**Title:** Capacity Field Interactions Over Time

**Pick data:** Nusights Events Activitytype Default Historical Tbl Flat

**Filter:**

- `Page Section` is `create_storage_container`
- `Action Type` is any of `input_change.reserved_capacity`, `input_change.advertised_capacity`
- `Destination Name` is `storage_container/create_form`

**Summarize:**

- Metric: Count of rows
- Group by: `Action Type`, `Timestamp` (Month)

**Visualization:** Line chart with two series. Useful if you prefer trend lines over side-by-side bars.

**Grid size:** 12 × 7

---

### 16 — Filesystem Allowlist Interactions

> "Do users interact with the Filesystem Allowlists feature during storage container creation?"
>
> Answers whether this feature is being used at all.

**Suggested Approach (Tier 1 · Scalar/Trend)**

**Pick data:** Nusights Events Activitytype Default Historical Tbl Flat

**Filter:**

- `Page Section` is `create_storage_container`
- `Action Type` starts with `input_change.filesystem`
- `Destination Name` is `storage_container/create_form`

**Summarize:**

- Metric: Count of rows

**Visualization:** Trend (scalar + previous-period delta).

**Grid size:** 6 × 5

**Why these filters:** `starts with input_change.filesystem` broadly captures any filesystem allowlist field interaction.

**SQL equivalent (used for API creation):**

```sql
SELECT
  DATE_TRUNC('month', TIMESTAMP) AS MONTH,
  COUNT(*) AS TOTAL_INTERACTIONS
FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
WHERE PAGE_SECTION = 'create_storage_container'
  AND ACTION_TYPE LIKE 'input_change.filesystem%'
  AND DESTINATION_NAME = 'storage_container/create_form'
GROUP BY MONTH
ORDER BY MONTH
```

---

**Alternative Approach (Tier 1 · Line chart)**

**Title:** Filesystem Allowlist Usage Over Time

**Visualization:** Line chart grouped by month.

**Grid size:** 12 × 7

---

### 17 — Tooltip Icon Interactions

> "Do users interact with the [i] and [?] tooltip icons beside properties in the create storage container form?"
>
> Shows how often users seek contextual help for each property and how the pattern evolves over time.

**Suggested Approach (Tier 1 · Bar chart, grouped by month)**

**Pick data:** Nusights Events Activitytype Default Historical Tbl Flat

**Filter:**

- `Page Section` is `create_storage_container`
- `Action Type` contains `tooltip`
- `Destination Name` is `storage_container/create_form`

**Summarize:**

- Metric: Count of rows
- Group by: `Timestamp` (Month), `Action Type`

**Visualization:** Bar chart (vertical, grouped) with months on the x-axis and one colored bar per tooltip property per month. Shows which tooltip properties attract the most help-seeking and whether that changes over time.

**Grid size:** 12 × 8

**Why these filters:** `contains tooltip` captures all tooltip events. Grouping by `Timestamp` + `Action Type` creates the monthly comparison across tooltip properties.

**SQL equivalent (used for API creation):**

```sql
SELECT
  DATE_TRUNC('month', TIMESTAMP) AS MONTH,
  REPLACE(ACTION_TYPE, '.tooltip', '') AS PROPERTY_NAME,
  COUNT(*) AS TOTAL_INTERACTIONS
FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
WHERE PAGE_SECTION = 'create_storage_container'
  AND ACTION_TYPE ILIKE '%tooltip%'
  AND DESTINATION_NAME = 'storage_container/create_form'
GROUP BY MONTH, PROPERTY_NAME
ORDER BY MONTH
```

---

**Alternative Approach (Tier 1 · Line chart)**

**Title:** Tooltip Interactions Over Time

**Pick data:** Nusights Events Activitytype Default Historical Tbl Flat

**Filter:**

- `Page Section` is `create_storage_container`
- `Action Type` contains `tooltip`
- `Destination Name` is `storage_container/create_form`

**Summarize:**

- Metric: Count of rows
- Group by: `Action Type`, `Timestamp` (Month)

**Visualization:** Line chart with one series per tooltip property. Useful if you prefer trend lines over side-by-side bars.

**Grid size:** 12 × 7

---

### 18 — Header Help Icon Clicks

> "Do users interact with the [?] help icon on the header of the create storage container form?"
>
> Answers whether users seek header-level help.

**Suggested Approach (Tier 1 · Scalar/Trend)**

**Pick data:** Nusights Events Activitytype Default Historical Tbl Flat

**Filter:**

- `Page Section` is `create_storage_container`
- `Action Type` starts with `header.help`
- `Destination Name` is `storage_container/create_form`

**Summarize:**

- Metric: Count of rows

**Visualization:** Trend (scalar + previous-period delta).

**Grid size:** 6 × 5

**Why these filters:** `starts with header.help` isolates header help-icon events.

**SQL equivalent (used for API creation):**

```sql
SELECT
  DATE_TRUNC('month', TIMESTAMP) AS MONTH,
  COUNT(*) AS TOTAL_CLICKS
FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
WHERE PAGE_SECTION = 'create_storage_container'
  AND ACTION_TYPE LIKE 'header.help%'
  AND DESTINATION_NAME = 'storage_container/create_form'
GROUP BY MONTH
ORDER BY MONTH
```

---

**Alternative Approach (Tier 1 · Line chart)**

**Title:** Header Help Icon Clicks Over Time

**Visualization:** Line chart grouped by month.

**Grid size:** 12 × 7

---

### 19 — Modal Dismissals — Close vs Cancel

> "Do users click 'X' or 'Cancel' to close the create storage container modal without making changes?"
>
> Shows whether users prefer the X button or the Cancel button, and how the pattern evolves over time.

**Suggested Approach (Tier 1 · Bar chart, grouped by month)**

**Pick data:** Nusights Events Activitytype Default Historical Tbl Flat

**Filter:**

- `Page Section` is `create_storage_container`
- `Action Type` is any of `modal.close`, `modal.cancel`
- `Destination Name` is `storage_container/create_form`

**Summarize:**

- Metric: Count of rows
- Group by: `Timestamp` (Month), `Action Type`

**Visualization:** Bar chart (vertical, grouped) with months on the x-axis and one colored bar per dismissal method per month. Shows both relative preference and temporal trends — the viewer can see which dismissal method is used more and whether that pattern is shifting.

**Grid size:** 12 × 8

**Why these filters:** Multi-value filter captures both dismissal methods. Grouping by `Timestamp` + `Action Type` creates the monthly comparison.

**SQL equivalent (used for API creation):**

```sql
SELECT
  DATE_TRUNC('month', TIMESTAMP) AS MONTH,
  CASE
    WHEN ACTION_TYPE = 'modal.close' THEN 'X (Close)'
    WHEN ACTION_TYPE = 'modal.cancel' THEN 'Cancel Button'
  END AS DISMISS_METHOD,
  COUNT(*) AS TOTAL_DISMISSALS
FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
WHERE PAGE_SECTION = 'create_storage_container'
  AND ACTION_TYPE IN ('modal.close', 'modal.cancel')
  AND DESTINATION_NAME = 'storage_container/create_form'
GROUP BY MONTH, DISMISS_METHOD
ORDER BY MONTH
```

---

**Alternative Approach (Tier 1 · Line chart)**

**Title:** Modal Dismissals Over Time

**Pick data:** Nusights Events Activitytype Default Historical Tbl Flat

**Filter:**

- `Page Section` is `create_storage_container`
- `Action Type` is any of `modal.close`, `modal.cancel`
- `Destination Name` is `storage_container/create_form`

**Summarize:**

- Metric: Count of rows
- Group by: `Action Type`, `Timestamp` (Month)

**Visualization:** Line chart with two series. Useful if you prefer trend lines over side-by-side bars.

**Grid size:** 12 × 7

---

### 20 — Storage Container Creation Duration

> "How much time does the user spend creating the storage container, comparing when advanced settings are opened versus when they are not?"
>
> Shows how the average creation time trends over months, revealing whether the experience is getting faster or slower.

**Suggested Approach (Tier 3 · Line chart, avg duration by month)**

**SQL:**

```sql
WITH starts AS (
  SELECT
    SESSION_ID,
    TIMESTAMP AS start_ts
  FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
  WHERE PAGE_SECTION = 'storage_container.eb'
    AND ACTION_TYPE = 'create_storage_container.start'
    AND DESTINATION_NAME = 'storage_container/list'
),
submits AS (
  SELECT
    SESSION_ID,
    TIMESTAMP AS submit_ts
  FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
  WHERE PAGE_SECTION = 'create_storage_container'
    AND ACTION_TYPE = 'create_storage_container.submit'
    AND DESTINATION_NAME = 'storage_container/create_form'
),
paired AS (
  SELECT
    s.SESSION_ID,
    s.start_ts,
    sub.submit_ts,
    TIMESTAMPDIFF('second', s.start_ts, sub.submit_ts) AS duration_seconds
  FROM starts s
  INNER JOIN submits sub ON s.SESSION_ID = sub.SESSION_ID
    AND sub.submit_ts > s.start_ts
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY s.SESSION_ID ORDER BY sub.submit_ts ASC
  ) = 1
)
SELECT
  DATE_TRUNC('month', start_ts) AS MONTH,
  ROUND(AVG(duration_seconds), 0) AS AVG_DURATION_SECONDS
FROM paired
WHERE duration_seconds > 0
  AND duration_seconds < 3600
GROUP BY MONTH
ORDER BY MONTH
```

**What this returns:** One row per month showing the average creation duration in seconds, revealing whether the creation experience is getting faster or slower over time.

**Assumptions:**

- `create_storage_container.submit` fires on form submission (may be `.save` or `.complete` — verify).
- Duration > 3600s excluded as outlier.

**Visualization:** Line chart with months on the x-axis and average duration in seconds on the y-axis. Duration questions are time-series questions — the user wants to see whether the experience is improving or degrading, not a one-shot statistical summary.

**Grid size:** 12 × 7

---

**Alternative Approach (Tier 3 · Bar chart, grouped by month, with/without advanced settings)**

**Title:** Creation Duration by Advanced Settings Usage

**SQL:**

```sql
WITH starts AS (
  SELECT
    SESSION_ID,
    TIMESTAMP AS start_ts
  FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
  WHERE PAGE_SECTION = 'storage_container.eb'
    AND ACTION_TYPE = 'create_storage_container.start'
    AND DESTINATION_NAME = 'storage_container/list'
),
submits AS (
  SELECT
    SESSION_ID,
    TIMESTAMP AS submit_ts
  FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
  WHERE PAGE_SECTION = 'create_storage_container'
    AND ACTION_TYPE = 'create_storage_container.submit'
    AND DESTINATION_NAME = 'storage_container/create_form'
),
advanced AS (
  SELECT DISTINCT SESSION_ID
  FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
  WHERE PAGE_SECTION = 'create_storage_container'
    AND ACTION_TYPE = 'input_change.advanced_settings'
    AND DESTINATION_NAME = 'storage_container/create_form'
),
paired AS (
  SELECT
    s.SESSION_ID,
    s.start_ts,
    sub.submit_ts,
    TIMESTAMPDIFF('second', s.start_ts, sub.submit_ts) AS duration_seconds,
    CASE WHEN a.SESSION_ID IS NOT NULL THEN 'With Advanced Settings'
         ELSE 'Without Advanced Settings'
    END AS SETTINGS_GROUP
  FROM starts s
  INNER JOIN submits sub ON s.SESSION_ID = sub.SESSION_ID
    AND sub.submit_ts > s.start_ts
  LEFT JOIN advanced a ON s.SESSION_ID = a.SESSION_ID
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY s.SESSION_ID ORDER BY sub.submit_ts ASC
  ) = 1
)
SELECT
  DATE_TRUNC('month', start_ts) AS MONTH,
  SETTINGS_GROUP,
  ROUND(AVG(duration_seconds), 0) AS AVG_DURATION_SECONDS
FROM paired
WHERE duration_seconds > 0
  AND duration_seconds < 3600
GROUP BY MONTH, SETTINGS_GROUP
ORDER BY MONTH
```

**What this returns:** One row per month per settings group, showing the average creation duration — the viewer can compare "with advanced settings" vs "without" side-by-side over time.

**Assumptions:**

- `input_change.advanced_settings` fires when the user toggles advanced settings (may be `toggle.advanced_settings`).
- Duration > 3600s excluded as outlier.

**Visualization:** Bar chart (vertical, grouped) with months on the x-axis and one colored bar per settings group per month. Shows whether advanced settings usage makes creation significantly slower, and how both groups trend over time.

**Grid size:** 12 × 8

---

### 21 — Replication Factor Info Banner Interactions

> "Do users hover or click on the information banner around the Replication Factor field?"
>
> Shows whether users seek additional context about replication factor.

**Suggested Approach (Tier 1 · Scalar/Trend)**

**Pick data:** Nusights Events Activitytype Default Historical Tbl Flat

**Filter:**

- `Page Section` is `create_storage_container`
- `Action Type` starts with `replication_factor.`
- `Destination Name` is `storage_container/create_form`

**Summarize:**

- Metric: Count of rows

**Visualization:** Trend (scalar + previous-period delta).

**Grid size:** 6 × 5

**Why these filters:** `starts with replication_factor.` captures both tooltip and banner interactions.

**SQL equivalent (used for API creation):**

```sql
SELECT
  DATE_TRUNC('month', TIMESTAMP) AS MONTH,
  COUNT(*) AS TOTAL_INTERACTIONS
FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
WHERE PAGE_SECTION = 'create_storage_container'
  AND ACTION_TYPE LIKE 'replication_factor.%'
  AND DESTINATION_NAME = 'storage_container/create_form'
GROUP BY MONTH
ORDER BY MONTH
```

---

**Alternative Approach (Tier 1 · Line chart)**

**Title:** Replication Factor Banner Interactions Over Time

**Visualization:** Line chart grouped by month.

**Grid size:** 12 × 7

---

## Dashboard Layout Plan

Using the 18-column grid with user-preferred sizing: `pie=12×8`, `bar=12×8`, `line=12×7`, `row=12×7`, `scalar=6×5`, `table=18×8`.

All 12-wide charts occupy col 0–11, leaving col 12–17 free for scalar widgets (6×5).

```
Row  0: #01 Column Sorting (pie 12×8)     + #05 Custom Views (scalar 6×5)
Row  5:                                    + #11 Multi-Entity (scalar 6×5)
Row  8: #02 Row Link Clicks (line 12×7)    + #16 Filesystem Allowlist (scalar 6×5)
Row 15: #03 Checkbox Selections (line 12×7)+ #18 Header Help (scalar 6×5)
Row 22: #04 View Changes (line 12×7)       + #21 Replication Factor (scalar 6×5)
Row 29: #06 Most Added Columns (row 12×7)
Row 36: #07 Most Used Group-By (row 12×7)
Row 43: #08 Group-By Changes (line 12×7)
Row 50: #09 Most Used Filters (pie 12×8)
Row 58: #10 Filter Interactions (line 12×7)
Row 65: #12 Update Form Fields (pie 12×8)
Row 73: #13 Creations Over Time (line 12×7)
Row 80: #14 Advanced Settings (pie 12×8)
Row 88: #15 Capacity Comparison (bar 12×8)
Row 96: #17 Tooltip Interactions (bar 12×8)
Row104: #19 Modal Dismissals (bar 12×8)
Row112: #20 Creation Duration (table 18×8)
```

Total height: 120 grid rows. All 5 scalars packed into gaps beside 12-wide charts.

---

## Inferred Event Names

| #   | Inferred `ACTION_TYPE`                                               | Confidence | Notes                                       |
| --- | -------------------------------------------------------------------- | ---------- | ------------------------------------------- |
| 05  | `*custom*` (contains match)                                          | Low        | Custom view creation actionType unconfirmed |
| 15  | `input_change.reserved_capacity`, `input_change.advertised_capacity` | Medium     | Suffix names inferred from field labels     |
| 16  | `input_change.filesystem*` (starts-with)                             | Medium     | Exact suffix unknown                        |
| 18  | `header.help*` (starts-with)                                         | Low        | Could be `header_help`, `help.click`, etc.  |
| 19  | `modal.close`, `modal.cancel`                                        | Medium     | Could be `close_modal`, `cancel`, etc.      |
| 20  | `create_storage_container.submit`, `input_change.advanced_settings`  | Medium     | Submit event may be `.save` or `.complete`  |
| 21  | `replication_factor.*` (starts-with)                                 | Medium     | May be `.tooltip`, `.banner`, `.info`       |

### Diagnostic Query

```sql
SELECT
  ACTION_TYPE, PAGE_SECTION, SUB_PAGE_SECTION, DESTINATION_NAME,
  COUNT(*) AS EVENT_COUNT
FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
WHERE PAGE_SECTION IN ('create_storage_container', 'update_storage_container', 'storage_container.eb')
GROUP BY ACTION_TYPE, PAGE_SECTION, SUB_PAGE_SECTION, DESTINATION_NAME
ORDER BY EVENT_COUNT DESC
LIMIT 100
```
