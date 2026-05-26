# Dashboard Layout

Metabase dashboards use a **24-column grid**. Cards are placed with `(col, row)` as the top-left origin and `(size_x, size_y)` for dimensions. Rows are unbounded.

## Sizing heuristic

Use the widget's `display` value to pick a default size. Two 12-column widgets fill a row (12 + 12 = 24).

| Display                                        | `size_x` | `size_y` | Cards per row |
| ---------------------------------------------- | -------- | -------- | ------------- |
| `scalar`, `smartscalar`, `gauge`, `progress`   | 8        | 4        | 3             |
| `bar`, `row`, `line`, `area`, `pie`, `scatter` | 12       | 7        | 2             |
| `funnel`, `combo`, `waterfall`                 | 12       | 7        | 2             |
| `table`, `pivot`                               | 24       | 8        | 1             |
| `map`                                          | 12       | 8        | 2             |

Override when:

- The widget title is unusually long → bump `size_x` to keep labels readable.
- The user explicitly asked for a specific layout (e.g. "make the funnel full-width").

## Auto-layout algorithm (new dashboard)

Place widgets in the order they appear in the summary table of `widget-review.md`.

```
state: col_cursor = 0, row_cursor = 0, current_row_height = 0
for each widget in order:
    (sx, sy) = size_for(display)
    if col_cursor + sx > 24:
        # wrap to next row
        row_cursor += current_row_height
        col_cursor = 0
        current_row_height = 0
    emit dashcard at (col=col_cursor, row=row_cursor, size_x=sx, size_y=sy)
    col_cursor += sx
    current_row_height = max(current_row_height, sy)
```

Groups of similarly-sized widgets pack neatly; oversized widgets (like 24-wide tables) flush to a new full row.

### Grouping by section (optional)

If `widget-review.md` rows have a "Page Section" or "Feature Area" attribute (from the original spreadsheet), and the user wants section headers on the dashboard:

- Insert a heading-style dashcard (`virtual_card` with `display: "heading"`) at the start of each section, full width (`size_x: 24`, `size_y: 1`).
- Reset `col_cursor = 0` and bump `row_cursor` before placing the section's widgets.

Only do this if the user asks — default is no headings, just packed widgets.

## Adding to an existing dashboard (Flow 2)

1. `GET /api/dashboard/{id}` and read the current `dashcards` array.
2. Compute `max_row = max(dc.row + dc.size_y for dc in existing)` — this is the first free row below the existing content.
3. Start the auto-layout algorithm at `row_cursor = max_row`, `col_cursor = 0`.
4. Build the final `dashcards` payload as the **union** of:
   - Existing dashcards, unchanged (keep their positive `id`s and positions).
   - New dashcards with negative `id`s (`-1`, `-2`, …) at the computed positions.
5. `PUT /api/dashboard/{id}` with that combined array.

Do **not** rearrange existing cards — preserve the user's curated layout above the new content.

## Heading / virtual cards

A heading dashcard isn't a real card — it's a `virtual_card` embedded in the dashcards array:

```json
{
  "id": -10,
  "card_id": null,
  "row": 0,
  "col": 0,
  "size_x": 24,
  "size_y": 1,
  "visualization_settings": {
    "text": "## Role Management",
    "virtual_card": {
      "name": null,
      "display": "heading",
      "visualization_settings": {},
      "dataset_query": {},
      "archived": false
    }
  }
}
```

## Worked example

Suppose the review file has these `✅ Ready` widgets in order:

| #   | Title                 | Display       |
| --- | --------------------- | ------------- |
| 1   | Active Users (MAU)    | `smartscalar` |
| 2   | Save vs Save & Create | `bar`         |
| 3   | Top Operations Added  | `row`         |
| 4   | Role Creation Funnel  | `funnel`      |
| 5   | All Role Events       | `table`       |

Auto-layout produces:

```
Row 0 (height 7):
  col  0–7:  Active Users (8×4)
  col  8–19: Save vs Save & Create (12×7)
  → col 20 + 12 > 24 ⇒ wrap

Row 7 (height 7):
  col  0–11: Top Operations Added (12×7)
  col 12–23: Role Creation Funnel (12×7)

Row 14 (height 8):
  col 0–23:  All Role Events (24×8)
```

The resulting `dashcards`:

```json
[
  { "id": -1, "card_id": 101, "col": 0, "row": 0, "size_x": 8, "size_y": 4 },
  { "id": -2, "card_id": 102, "col": 8, "row": 0, "size_x": 12, "size_y": 7 },
  { "id": -3, "card_id": 103, "col": 0, "row": 7, "size_x": 12, "size_y": 7 },
  { "id": -4, "card_id": 104, "col": 12, "row": 7, "size_x": 12, "size_y": 7 },
  { "id": -5, "card_id": 105, "col": 0, "row": 14, "size_x": 24, "size_y": 8 }
]
```

## Constraints and quirks

- `col` is 0–23 inclusive. `col + size_x` must be ≤ 24.
- `size_x` minimum is 1; `size_y` minimum is 1. Practical minimums for legibility: 4×3 for scalars, 6×4 otherwise.
- New dashcards **must** have negative integer `id`s (`-1`, `-2`, …). Existing ones keep their positive IDs.
- `parameter_mappings` is optional; default `[]`. Only populate when the dashboard has parameters and the card consumes them.
- `visualization_settings` on the dashcard overrides the card's own settings for that placement — leave as `{}` unless the user asks for a dashboard-specific override.
