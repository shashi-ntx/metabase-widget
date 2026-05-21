# Stage 2 — Execution Flows

After the user confirms execution, ask which flow they want (unless they already said). Four flows are supported.

## Flow selection

If the confirmation message already names a flow, infer:

- "create a new dashboard" / "build a dashboard" / "make a dashboard called …" → **Flow 1**
- "add to <name>" / "add to https://…/dashboard/…" / "add to existing dashboard" → **Flow 2**
- "just save the questions" / "questions only" / "no dashboard" → **Flow 3**
- "stop after the review" / "markdown only" / never confirmed → **Flow 4** (the default if the user never enters Stage 2)

Otherwise ask once, with these three options (Flow 4 is implicit — if the user never confirms, they get it automatically):

> You've confirmed the widget review. How would you like me to create these in Metabase?
>
> 1. **Create a new dashboard** — I'll create the questions, build a new dashboard, and arrange the widgets on it.
> 2. **Add to an existing dashboard** — Tell me the dashboard name, ID, or URL, and I'll add the new widgets to it.
> 3. **Save as questions only** — I'll create the saved questions; you'll add them to dashboards yourself.

Use `AskQuestion` to present these as single-select if the tool is available.

## Flow 1 — Create new dashboard + widgets from scratch

```
1. Re-read widget-review.md, parse, filter to ✅ Ready rows.
2. Ask (if not already provided): dashboard name, description, collection ID.
   - Default name: derive from the H1 of widget-review.md.
   - Default description: "Generated from <review file name> on <date>."
   - Default collection: METABASE_DEFAULT_COLLECTION_ID.
3. For each Ready widget: POST /api/card with the SQL + display + viz settings.
   - Collect created card IDs + URLs into a results array.
   - On failure: record the error in the results array, continue.
4. POST /api/dashboard to create the empty dashboard. Capture its ID.
5. Build the dashcards array using the layout heuristic in dashboard-layout.md.
6. PUT /api/dashboard/{id} with the dashcards array.
7. Run scripts/widget_review.py update-results to write URLs + dashboard link back into widget-review.md.
8. Report to user: dashboard URL, totals, any failures.
```

## Flow 2 — Add widgets to an existing dashboard

```
1. Re-read widget-review.md, parse, filter to ✅ Ready rows.
2. Resolve the target dashboard:
   - If user provided a URL like .../dashboard/45-role-management → extract ID = 45.
   - If user provided a numeric ID → use directly.
   - If user provided a name → GET /api/search?q=<name>&models=dashboard.
     - 0 matches: tell the user, ask for a different name or offer Flow 1.
     - 1 match: confirm "Found 'Role Management — Telemetry' (id 45). Use it?".
     - 2+ matches: list them with IDs and collection paths; let the user pick.
3. GET /api/dashboard/{id} to read existing dashcards. Compute next free grid position
   (see dashboard-layout.md § "Adding to an existing dashboard").
4. For each Ready widget: POST /api/card. Record results.
5. PUT /api/dashboard/{id} with the existing dashcards (real positive IDs) + new
   dashcards (negative IDs, positioned below the existing grid).
6. update-results → widget-review.md.
7. Report: dashboard URL, what was added, any failures.
```

## Flow 3 — Save as questions only (no dashboard)

```
1. Re-read widget-review.md, parse, filter to ✅ Ready rows.
2. Ask (if not already provided): collection ID. Default: METABASE_DEFAULT_COLLECTION_ID.
3. For each Ready widget: POST /api/card with collection_id set.
4. update-results → widget-review.md (no dashboard URL, just card URLs).
5. Report: list of created cards with URLs, any failures.
```

## Flow 4 — Markdown only (Stage 1 only, no API calls)

This is the default when the user never confirms Stage 2. The `widget-review.md` file is the entire deliverable. No additional action needed.

If the user later returns and confirms, re-enter Stage 2 with one of Flows 1–3.

## Decision matrix

| User said in confirmation                            | Flow | Need to ask?                                     |
| ---------------------------------------------------- | ---- | ------------------------------------------------ |
| "proceed", "execute", "go ahead" (no flow mentioned) | ?    | Yes — ask which of Flows 1–3                     |
| "create a new dashboard"                             | 1    | Ask for dashboard name + collection if not given |
| "create a dashboard called <name>"                   | 1    | Confirm collection only                          |
| "add to <name>" or "add to <URL>"                    | 2    | Resolve dashboard; confirm match                 |
| "just save the questions" / "questions only"         | 3    | Ask for collection if not given                  |
| User edited the file but never confirmed             | 4    | No — wait for explicit confirmation              |

## Partial failure handling

A failure in step 3 (card creation) must never block the rest of the flow:

- Continue creating remaining cards.
- In Flow 1: still create the dashboard with only the successful cards.
- In Flow 2: still update the existing dashboard with only the successful cards.
- In Flow 3: just report the successes and failures.

After all API calls finish, surface in chat:

```
✅ Created N of M widgets.
   Dashboard: <URL or "no dashboard requested">

❌ Failed:
   - Row 4 "<Title>": Snowflake compilation error: invalid identifier 'BAD_COL'
   - Row 7 "<Title>": Permission denied for collection 99

📝 Updated review file: <path to widget-review.md>
```

Then offer: "Want me to retry the failed ones after you fix the SQL?" — on yes, re-read the file, filter to rows whose Result column starts with `❌ Error`, and rerun for just those.
