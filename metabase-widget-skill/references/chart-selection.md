# Chart selection

How to pick the visualization for a Metabase widget. Distilled from Metabase's [Which chart should you use?](https://www.metabase.com/learn/metabase-basics/querying-and-dashboards/visualization/chart-guide) and adapted for telemetry widgets.

Always state which visualization to use in the output, with one sentence on why. Never leave it as "table" by default — tables are appropriate sometimes, but only when justified.

## General principle: chart choice depends on three things

Every chart recommendation must account for all three factors together — not just one:

1. **Data shape** — one number, a category × measure, a time series, two measures, a part-of-whole, a sequence of steps, geographic?
2. **Intent** — current state, change over time, comparison, composition, distribution, correlation, drop-off?
3. **Result cardinality** — how many rows/categories will the query return? A chart that's perfect for 5 categories can be unreadable at 50. When cardinality is unknown at authoring time, give two conditional recommendations (one for small results, one for large).

No single chart type is correct for all sizes of the same data shape. A row chart works for 8 categories but not 40. A pie chart is bad for 2 precise comparisons but excellent for 30+ categories because Metabase auto-groups the tail into "Other". A table is the right call when the user wants to scan all rows. Pick intentionally for the specific combination of shape, intent, and expected size — don't default to the same chart every time.

## Decision tree

Use the first row that matches the question's shape.

| Data shape | Intent | Pick |
| --- | --- | --- |
| One number, static | "How many right now?" | **Number** (single scalar) |
| One number, with a target | "How close are we to X?" | **Progress bar** |
| One number, position in a range | "Where does this fall in [min, max]?" | **Gauge** |
| One number, with a previous period | "Up or down vs. last month?" | **Trend** (current value + delta) |
| 1 measure × 1 categorical dim, small N (2–8 categories) | "How does X compare across categories?" | **Bar** (vertical) or **Row** (horizontal — better for long labels or N > 6) |
| 1 measure × 1 categorical dim, 2–3 categories, part-of-whole | "What share does each piece have?" | **Pie / Donut** |
| 1 measure × 1 categorical dim, > 3 categories, part-of-whole | "What share does each piece have?" | **Bar** (not pie — humans can't compare > 3 slices) |
| 1 measure × time | "How is X trending?" | **Line** (default), or **Bar** if intervals are discrete (daily counts, monthly totals) |
| 1 measure × time, with a target | "Are we beating the goal over time?" | **Line + goal line** |
| 2+ measures × time, same scale | "How do these series move together?" | **Line** (overlaid series) |
| 2+ measures × time, different scales (e.g. count vs. dollars) | "How do these series move together when scales differ?" | **Combo chart** (two y-axes) |
| 1 measure × time × categorical breakout | "How does the total split among categories over time?" | **Stacked area** (continuous flow) or **Stacked bar** (discrete intervals) |
| 1 measure × time × categorical breakout, relative shares only | "How does the mix shift over time, regardless of total?" | **100% stacked bar** |
| Sequential drop-off through steps | "Where do users fall out of the funnel?" | **Funnel** |
| Cumulative value with positive and negative components | "How do additions and subtractions sum to a total?" | **Waterfall** |
| 2 numeric measures, one row per record | "Do X and Y correlate?" | **Scatter** |
| 2 numeric measures + a third dimension | "Do X and Y correlate, weighted by Z?" | **Bubble** (scatter with sized dots) |
| 1 numeric measure binned into ranges | "How is X distributed?" | **Histogram** (bar over binned numeric x-axis) |
| Geographic, individual points | "Where are these located?" | **Pin map** |
| Geographic, by region | "How does X vary by country/state?" | **Region map** (choropleth) |
| Geographic, density | "Where are the hot spots?" | **Grid map** |
| Many measures, exact values matter, sorting/filtering matters | "Let me look up specific rows." | **Table** (or **Pivot table** if subtotals needed) |

## Telemetry-specific guidance

Most telemetry widgets fall into a small set of buckets. Default picks:

- **"How often does action X happen?"** (single count) → **Number** if it's a KPI tile; **Trend** if there's a previous period to compare against.
- **"X vs Y" comparison** (e.g. save vs save-and-continue) → **Bar**. Two-row tables are almost never the right call when the user wants a comparison — a bar makes the magnitude immediate.
- **"Top N items chosen"** (e.g. most-added operations) → **Row chart** sorted descending (horizontal bars handle long action names better than vertical bars).
- **"How does feature usage trend?"** → **Line** with Month as the default granularity (or day/week depending on requested timeframe and history). Add a goal line if there's a target.
- **"How does usage split across product areas over time?"** → **Stacked bar** if intervals are monthly (or weekly if requested); **Stacked area** if it's a continuous daily series.
- **"Funnel: of users who started X, how many completed Y, then Z?"** → **Funnel**. (The underlying query is usually Tier 3 SQL — one count per step.)
- **"Distribution of session lengths / time-on-page"** → **Histogram** with sensible bins.
- **"Counts by country / region"** → **Region map** for at-a-glance; **Table** if the user needs to sort or look up specific values.
- **"Single KPI with last-period delta"** (e.g. monthly active users vs last month) → **Trend**.

## When a table is the right call

Tables are not a fallback — they are the right answer when:

- The user needs to **look up specific values** (e.g. "show me each role and how many times it was saved").
- There are **many measures per row** that all matter (e.g. count, distinct users, last-seen timestamp, all together).
- The output is meant to be **sorted, filtered, or scanned** interactively rather than read as a shape.
- The result is **inherently row-oriented** (e.g. a list of recent events for debugging).

Use a **pivot table** when the user needs subtotals or wants to flip rows ↔ columns (e.g. "actions across product areas, with row + column totals").

## Result cardinality affects chart choice

The number of rows a query returns matters as much as the data shape. General thresholds for categorical dimensions:

- **1 row** — Number, Trend, Gauge, or Progress bar. Never a chart with an axis.
- **2–15 rows** — Bar or Row chart works well. Pie/Donut works for composition questions with ≤ 6 slices.
- **15+ rows** — Bar/Row charts become unreadable. Use **Pie/Donut** (Metabase auto-groups the long tail into "Other", showing only the top ~8–10 slices), or a **Table** sorted descending if the user wants to scan all values.
- **Time series** — Line or bar over time handles any cardinality because the x-axis is temporal. The thresholds above apply to categorical dimensions only.

### When the agent can't predict cardinality

The agent often doesn't know how many distinct values a `GROUP BY` will produce. In that case, **give two conditional recommendations**:

1. **If results are small (≤ ~10 rows):** the chart that best fits the question's intent — row chart for ranking, pie/donut for composition, bar for comparison.
2. **If results are large (many categories):** a different chart that handles high cardinality — pie/donut (auto-groups long tail into "Other"), table (for exhaustive lookup), or row chart with a Row limit.

Don't default to the same chart type for both. Pick intentionally based on what the question is asking and how many results there are. The cardinality table above has the full mapping.

Format in the output:

> **Visualization (≤ 10 results):** Row chart (horizontal bars), sorted descending by count.
>
> **Visualization (many results):** Pie chart — Metabase auto-groups smaller slices into "Other", giving a clean visual summary of the top contributors without needing a Row limit.
>
> **Why:** The question asks "which operations are clicked most" — with few results, a row chart makes the ranking scannable; with many results, a pie chart collapses the long tail and highlights the leaders.

## Anti-patterns

- **Don't pick a table just because Metabase defaults to one for SQL questions.** Native queries always render as table first — actively choose the visualization.
- **Don't use pie/donut for precise side-by-side ranking of similarly-sized categories** — humans can't reliably compare adjacent slice sizes. But pie/donut is excellent for high-cardinality data where Metabase's auto-grouping collapses the long tail into "Other".
- **Don't use a vertical bar chart when labels are long.** Switch to a row chart so labels stay horizontal and readable.
- **Don't use a line chart for discrete daily totals if the user reads them as "this day's count"** — bar is clearer. Lines imply continuous interpolation between points.
- **Don't pick a single number when the value is meaningless without context.** Pair it with a previous-period delta (trend), a goal (progress), or a time series (line).
- **Don't overlay two series with wildly different scales on one y-axis.** Use a combo chart with dual axes.
- **Don't ship raw event-name values as axis labels.** Clean them first (see "Make the widget human-readable" in `SKILL.md`).
- **Don't pick a funnel when the steps aren't strictly sequential.** Funnels imply each step is a subset of the previous; use a bar chart for independent step counts.

## Output requirement

Every widget recommendation must include:

1. **The chart type** (e.g. `bar (horizontal / row)`, `line`, `trend`, `funnel`).
2. **One sentence of justification** tied to the question — what shape the data has and what the chart makes immediately visible.

Example:

> **Visualization:** bar (horizontal / row), sorted descending.
> **Why this chart:** The question asks "which operations are added most" — a row chart sorted descending puts the highest-count operations at the top and keeps long operation names readable, making the ranking obvious at a glance.
