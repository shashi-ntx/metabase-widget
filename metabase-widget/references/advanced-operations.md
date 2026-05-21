# Metabase Advanced Operations

Reference for the advanced features available in Metabase's Query Builder. Covers custom expressions (columns, filters, summaries), text cleaning and formatting, period-over-period time series comparisons, and the complete expression function catalog. All examples assume a Snowflake backend unless noted.

For basic query patterns (visual builder vs SQL) see `query-patterns.md` in the same folder.

---

## Custom Expressions Overview

Custom expressions are formulas you write inside the Query Builder's expression editor — equivalent to spreadsheet formulas or SQL column expressions. They appear in three places, each with different capabilities.

| Context | Where in Query Builder | What it does | Example |
|---|---|---|---|
| **Custom column** | Data section → Custom column | Computes a new column per row | `[Discount] / [Subtotal]` |
| **Custom filter** | Filter → Custom Expression | Boolean expression to include/exclude rows | `startsWith([Title], "Enormous") OR endsWith([Title], "Computer")` |
| **Custom summary** | Summarize → Custom Expression | Aggregation over all matching rows | `Share(contains([Title], "Paper"))` |

**Why use the Query Builder over SQL?** Two advantages that SQL questions lack: (1) anyone can read and extend your question without knowing SQL, and (2) drill-through works fully — click to break out by category, zoom in, or x-ray data. SQL questions only get limited drill-through. You can always convert a Query Builder question to SQL later via the editor's "View SQL" option.

### Expression Editor Basics

- Reference columns with brackets: `[Column Name]`, or `[Table → Column]` for joined tables (foreign-key relationships).
- Reference saved Segments and Metrics the same way: `[Valid User Sessions]`.
- Use `+`, `-`, `*`, `/` for arithmetic; parentheses for grouping.
- Boolean operators: `AND`, `OR`, `NOT`.
- Comparison operators: `>`, `>=`, `<`, `<=`, `=`, `!=`.
- The editor offers autocomplete when you type `[` and a function browser (the **f** button).

---

## Custom Columns

Custom columns add a derived field to your result set — computed per row, not aggregated.

### Use Case: Compute a Derived Metric

Calculate discount percentage from existing Subtotal and Discount columns:

```
[Discount] / [Subtotal]
```

Name it `Discount %`, format as Percent with 2 decimal places in the column formatting sidebar.

### Use Case: Extract Date Parts

Extract the hour from a timestamp to analyze activity distribution throughout the day:

```
hour([Timestamp])
```

The **Shortcuts** panel (Extract columns) prefills these for you — works on timestamp columns (hour, day, month, year, etc.) and URL columns (host, domain, subdomain).

### Use Case: Extract URL Paths

When the domain is constant, strip it to keep just the path for analysis:

```
regexextract([Page URL], "/.*")
```

This grabs everything starting from the first `/`.

### Use Case: Date Differences

Compute days between account creation and an event:

```
datetimeDiff([Account → Created At], [Timestamp], "day")
```

The `→` syntax references a column from a related table via foreign key.

### Use Case: Math on Custom Columns

Custom columns can reference other custom columns. If `Days since creation` already exists:

```
[Days since creation] / 7
```

yields weeks (with fractional precision, unlike `datetimeDiff` with `"week"` which truncates).

### Use Case: If-Then Logic with `case`

Bucket accounts into categories based on computed values:

```
case([Weeks since creation] < 52, "New", "Existing")
```

The `case` function (alias: `if`) evaluates conditions in order and returns the first match. The last argument is the default.

### Use Case: Strip Prefixes from Event Names

When telemetry event names carry prefixes like `add_operation:View Virtual Machine`, extract just the operation name:

```
regexextract([Destination Name], "[^:]+$")
```

To append a label for group operations:

```
case(
  contains([Destination Name], "operation_group"),
  concat(regexextract([Destination Name], "[^:]+$"), " (Group)"),
  regexextract([Destination Name], "[^:]+$")
)
```

Note: Metabase's `regexextract` does not support capture-group extraction (group 1 syntax) — it returns the full match. Use patterns that match only the desired substring. Metabase also lacks `indexOf`, `replace` in the custom column editor for older versions — use `regexextract` or `splitPart` instead.

### Note for SQL Experts

In SQL, column-level operations and aggregations both live in `SELECT`. In the Query Builder they're separate: column operations go in Custom Column blocks; aggregations go in Summarize. You cannot use `Sum`, `Count`, etc. in custom columns.

---

## Custom Filters

Filter expressions must resolve to a Boolean (true/false). The Query Builder implicitly ANDs multiple filters together, but custom filter expressions let you use `OR`.

### Use Case: OR Conditions

Find products starting with "Enormous" or ending with "Computer":

```
startsWith([Title], "Enormous") OR endsWith([Title], "Computer")
```

### Use Case: startsWith vs contains for Prefix Matching

Always use `startsWith` for prefix matching. Do NOT use `contains` for prefixes, as it will cause false positive matches with substrings. For example, if you want to find delete events (such as `delete` and `delete_confirm`), use `startsWith`:

```
startsWith([Destination Name], "delete")
```

If you used `contains([Destination Name], "delete")`, it would incorrectly match values like `abc_delete` or `system_delete`. Only use `contains` if the term can legitimately appear anywhere in the middle or end of the string.

### Use Case: Membership Checks with `in` (Do NOT use "is in")

When writing a custom filter expression to check if a column matches one of several values, use the `in` function:

```
in([Category], "Paper", "Packaging", "Office Supplies")
```

Or write out the OR conditions explicitly:

```
[Category] = "Paper" OR [Category] = "Packaging" OR [Category] = "Office Supplies"
```

Never write "is in" in a custom expression, as it is not a valid Metabase function or operator.

### Use Case: Nested Functions in Filters

The outermost function must return Boolean, but inner functions can return any type:

```
contains(concat([First Name], [Last Name]), "Wizard")
```

`concat` returns a string, but `contains` wraps it into a Boolean.

### Working with Dates in Filters

Dates must follow `"YYYY-MM-DD"` format (quoted, dash-separated):

```
between([Created At], "2020-01-01", "2020-03-31") OR [Received At] > "2019-12-25"
```

---

## Custom Summaries (Aggregations)

Aggregation expressions operate on all rows in a group. They can only be used in the Summarize section.

### Use Case: Share of a Category

What percentage of the product line is paper products?

```
Share(contains([Title], "Paper"))
```

Returns a decimal (format as Percent in column settings).

### Use Case: Conditional Counting and Summing

Count only rows meeting a condition:

```
CountIf([Subtotal] > 100)
```

Sum a column conditionally:

```
SumIf([Subtotal], [Order Status] = "Valid")
```

### Use Case: Combining All Three

A complex question using all three expression types together:

1. **Custom column:** `[Subtotal] / [Quantity]` → `Unit price`
2. **Custom filter:** `contains([Products → Title], "Wool") OR contains([Products → Title], "Cotton")`
3. **Custom summary:** `Average([Unit price] - [Products → Price] / 2)` grouped by month

---

## Text Cleaning and Formatting

Practical patterns for cleaning messy text data using custom columns.

### Searching and Extracting Valid Values

Use `regexextract` with case-insensitive regex to find valid entries in a freeform column:

```
regexextract([Main], "(?i)(beef tibs)")
```

`(?i)` makes the match case-insensitive. Combine with `coalesce` to pick the first non-null extracted value.

### Consolidating with `coalesce` and `lower`

After extracting valid values into separate columns (`[Beef]`, `[Chickpea]`), merge them:

```
lower(coalesce([Beef], [Chickpea], ""))
```

`coalesce` returns the first non-null value; `lower` standardizes case.

### Combining Columns with `case` and `concat`

Build complete values from multiple cleaned columns:

```
case(
    (isempty([Main (Clean)]) AND isempty([Side (Clean)])), "",
    isempty([Side (Clean)]), concat([Main (Clean)], " only"),
    isempty([Main (Clean)]), concat([Side (Clean)], " only"),
    concat([Main (Clean)], " with ", [Side (Clean)])
)
```

Order matters in `case` — it evaluates top-to-bottom and stops at the first match. Check the "both empty" condition before individual checks.

### Labeling Rows with Missing Data

Flag rows that need follow-up:

```
case(
    (isempty([Order]) OR isempty([Main (Clean)]) OR isempty([Side (Clean)])),
    "yes",
    "no"
)
```

### Best Practice

Create a new custom column for each function with multiple parameters (`case`, `regexextract`, `coalesce`). This makes expressions easier to debug and lets you verify intermediate results.

---

## Period-Over-Period Comparisons

Techniques for comparing metrics across time periods using the Query Builder.

### Trend Charts (Latest Period vs Previous)

For a quick latest-month comparison:

1. Summarize: `Sum of Total`, grouped by `Created At: Month`
2. Visualize → change to **Trend**
3. In visualization settings → Data tab → **Add comparison** → pick "Previous period" and/or "12 months ago"

Supports multiple comparisons and static goal values.

### Year-over-Year with the `Offset` Function

`Offset` returns a value from a different row, specified by row offset. It translates to SQL `LAG`/`LEAD` window functions.

Compare each month to the same month last year:

```
Offset(Sum([Total]), -12)
```

Name it `1 year ago`. Add a filter *after* the Summarize step for `Created At: Current Year` (filtering before summarizing would exclude last year's data needed by `Offset`).

For two years back, add another expression:

```
Offset(Sum([Total]), -24)
```

### Measuring Change (Absolute and Percentage)

YoY absolute change:

```
Sum([Total]) - Offset(Sum([Total]), -12)
```

YoY percentage change:

```
(Sum([Total]) - Offset(Sum([Total]), -12)) / Offset(Sum([Total]), -12)
```

Format the percentage column via column header → gear icon → Style → Percentage. Use conditional formatting (green for positive, red for negative) for readability.

### Visualization Tips

- Turn off "Split y-axis when necessary" in Axes settings so bars are comparable on the same scale.
- Reorder bars by dragging series in the Data tab (or reordering expressions in the Summarize block).
- `Offset` generates SQL window functions — click "View SQL" to inspect the generated query.

---

## Complete Expression Reference

Every function available in Metabase's expression editor, organized by category.

### Aggregations (Summarize only)

| Function | Syntax | Notes |
|---|---|---|
| `Average` | `Average(column)` | |
| `Count` | `Count()` | |
| `CountIf` | `CountIf(condition)` | |
| `Distinct` | `Distinct(column)` | |
| `DistinctIf` | `DistinctIf(column, condition)` | |
| `Max` | `Max(column)` | |
| `Median` | `Median(column)` | Not on Druid, MariaDB, MongoDB, MySQL, SQLite, Vertica, SQL Server |
| `Min` | `Min(column)` | |
| `Percentile` | `Percentile(column, value)` | Not on Druid, H2, MariaDB, MySQL, MongoDB, SQL Server, SQLite, Vertica |
| `Share` | `Share(condition)` | Returns decimal |
| `StandardDeviation` | `StandardDeviation(column)` | Not on Druid, SQLite |
| `Sum` | `Sum(column)` | |
| `SumIf` | `SumIf(column, condition)` | |
| `Variance` | `Variance(column)` | Not on Druid, SQLite |

### Window Functions (Summarize only)

| Function | Syntax | Notes |
|---|---|---|
| `CumulativeCount` | `CumulativeCount()` | |
| `CumulativeSum` | `CumulativeSum(column)` | |
| `Offset` | `Offset(expression, rowOffset)` | Not on MySQL/MariaDB, ClickHouse, MongoDB, Druid |

### Logical Functions

| Function | Syntax | Use Case |
|---|---|---|
| `between` | `between(column, start, end)` | Date/number range check |
| `case` / `if` | `case(cond, output, …)` | Multi-branch conditional |
| `coalesce` | `coalesce(val1, val2, …)` | First non-null value |
| `in` | `in(value, v2, v3, …)` | Membership check |
| `notIn` | `notIn(value, v2, v3, …)` | Exclusion check |
| `isNull` | `isNull(column)` | |
| `notNull` | `notNull(column)` | |

### Math Functions

| Function | Syntax | Notes |
|---|---|---|
| `abs` | `abs(column)` | |
| `ceil` | `ceil(column)` | |
| `exp` | `exp(column)` | Not on SQLite |
| `floor` | `floor(column)` | |
| `log` | `log(column)` | Not on SQLite |
| `power` | `power(column, exp)` | Not on SQLite |
| `round` | `round(column)` | `round(val * 10) / 10` for 1 decimal |
| `sqrt` | `sqrt(column)` | Not on SQLite |

### String Functions

| Function | Syntax | Notes |
|---|---|---|
| `concat` | `concat(v1, v2, …)` | |
| `contains` | `contains(str, search)` | Optional `"case-insensitive"` third arg |
| `doesNotContain` | `doesNotContain(str, search)` | Optional case-insensitive mode |
| `domain` | `domain(urlOrEmail)` | Extracts domain name |
| `endsWith` | `endsWith(text, comp)` | Optional case-insensitive mode |
| `host` | `host(urlOrEmail)` | Domain + TLD |
| `isEmpty` | `isEmpty(column)` | String columns only; use `isNull` for others |
| `notEmpty` | `notEmpty(column)` | String columns only |
| `length` | `length(text)` | |
| `lower` | `lower(text)` | |
| `upper` | `upper(text)` | |
| `lTrim` / `rTrim` / `trim` | `trim(text)` | Whitespace removal |
| `path` | `path(url)` | Extracts URL pathname |
| `regexExtract` | `regexExtract(text, regex)` | Not on H2, SQL Server, SQLite. **Works on Snowflake.** |
| `replace` | `replace(text, find, repl)` | |
| `splitPart` | `splitPart(text, delim, pos)` | Position is 1-indexed. **Works on Snowflake.** |
| `startsWith` | `startsWith(text, comp)` | Optional case-insensitive mode |
| `subdomain` | `subdomain(url)` | Ignores `www` |
| `substring` | `substring(text, pos, len)` | 1-indexed |
| `text` | `text(value)` | Convert number/date to string |
| `float` | `float(value)` | **Works on Snowflake.** |
| `integer` | `integer(value)` | **Works on Snowflake.** |

### Date Functions

| Function | Syntax | Notes |
|---|---|---|
| `convertTimezone` | `convertTimezone(col, target, source)` | |
| `datetimeAdd` | `datetimeAdd(col, amount, unit)` | Integer amounts only |
| `datetimeDiff` | `datetimeDiff(dt1, dt2, unit)` | |
| `datetimeSubtract` | `datetimeSubtract(col, amount, unit)` | |
| `day` / `hour` / `minute` / `month` / `quarter` / `second` / `week` / `weekday` / `year` | `day([col])` | Extract date parts |
| `dayName` / `monthName` / `quarterName` | `dayName(num)` | Localized names |
| `now` / `today` | `now()` / `today()` | Current datetime / date |
| `relativeDateTime` | `relativeDateTime(num, unit)` | Relative to now |
| `timeSpan` | `timeSpan(num, unit)` | Interval value for arithmetic |
| `interval` | `interval(col, num, unit)` | Relative range check |
| `date` | `date(value)` | ISO 8601 string → date |
| `datetime` | `datetime(value, mode)` | **Works on Snowflake.** Modes: `"iso"`, `"simple"`, `"unixSeconds"`, etc. |

### Snowflake Compatibility Summary

Most expressions work on Snowflake. Key ones confirmed available: `regexExtract`, `splitPart`, `float`, `integer`, `datetime`, `Offset`, `Median`, `Percentile`, `StandardDeviation`, `Variance`, `power`, `exp`, `log`, `sqrt`.

---

