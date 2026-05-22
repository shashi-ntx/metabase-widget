#!/usr/bin/env python3
"""
Create 21 Metabase cards from the storage telemetry requirement specs
and add them to dashboard #12 with auto-layout.

Sizes (user-specified):
  pie:    12 × 8
  bar:    12 × 8
  line:   12 × 7
  row:    12 × 7
  scalar: 6  × 5
  table:  18 × 8
"""

import json
import time
import urllib.request
import ssl

BASE_URL = "https://jerome-marshall-1.umsvm.nutanix.com:3300"
API_KEY = "mb_fofy95chH8koheUzMnlmA4xObA5dGx2zE2yc10rbYiY="
DATABASE_ID = 3
DASHBOARD_ID = 12
GRID_WIDTH = 18

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def api(method, path, body=None):
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("x-api-key", API_KEY)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, context=ctx) as resp:
        return json.loads(resp.read().decode())


WIDGETS = [
    {
        "num": "01",
        "name": "Column Sorting Distribution",
        "description": "\"Which columns do users sort on most in the storage container list?\"\nShows which table columns attract the most sorting activity, revealing data-access priorities.",
        "display": "pie",
        "size_x": 12, "size_y": 8,
        "sql": """SELECT
  REGEXP_SUBSTR(ACTION_TYPE, '[^.]+$') AS SORTED_COLUMN,
  COUNT(*) AS TOTAL_SORTS
FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
WHERE PAGE_SECTION = 'storage_container.eb'
  AND ACTION_TYPE LIKE 'sort_column.%'
  AND DESTINATION_NAME = 'storage_container/list'
GROUP BY SORTED_COLUMN
ORDER BY TOTAL_SORTS DESC""",
        "viz_settings": {}
    },
    {
        "num": "02",
        "name": "Row Link Clicks Over Time",
        "description": "\"How often do users click row links (e.g. container name) in the storage container list?\"\nShows the trend of row-click navigation.",
        "display": "line",
        "size_x": 12, "size_y": 7,
        "sql": """SELECT
  DATE_TRUNC('month', TIMESTAMP) AS MONTH,
  COUNT(*) AS TOTAL_CLICKS
FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
WHERE PAGE_SECTION = 'storage_container.eb'
  AND ACTION_TYPE = 'container_name.click'
  AND DESTINATION_NAME = 'storage_container/list'
GROUP BY MONTH
ORDER BY MONTH""",
        "viz_settings": {"graph.dimensions": ["MONTH"], "graph.metrics": ["TOTAL_CLICKS"]}
    },
    {
        "num": "03",
        "name": "Checkbox Selections Over Time",
        "description": "\"How often do users select checkboxes for multi-entity actions?\"\nShows the adoption trend of bulk-selection behavior.",
        "display": "line",
        "size_x": 12, "size_y": 7,
        "sql": """SELECT
  DATE_TRUNC('month', TIMESTAMP) AS MONTH,
  COUNT(*) AS TOTAL_SELECTIONS
FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
WHERE PAGE_SECTION = 'storage_container.eb'
  AND ACTION_TYPE = 'listview.select'
  AND DESTINATION_NAME = 'storage_container/list'
GROUP BY MONTH
ORDER BY MONTH""",
        "viz_settings": {"graph.dimensions": ["MONTH"], "graph.metrics": ["TOTAL_SELECTIONS"]}
    },
    {
        "num": "04",
        "name": "View Changes Over Time",
        "description": "\"How often do users change column views in the storage container list?\"\nShows the frequency trend of view switching.",
        "display": "line",
        "size_x": 12, "size_y": 7,
        "sql": """SELECT
  DATE_TRUNC('month', TIMESTAMP) AS MONTH,
  COUNT(*) AS TOTAL_CHANGES
FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
WHERE PAGE_SECTION = 'storage_container.eb'
  AND SUB_PAGE_SECTION = 'view_by_dropdown'
GROUP BY MONTH
ORDER BY MONTH""",
        "viz_settings": {"graph.dimensions": ["MONTH"], "graph.metrics": ["TOTAL_CHANGES"]}
    },
    {
        "num": "05",
        "name": "Custom View Creations",
        "description": "\"Do users create custom views in the storage container list?\"\nAnswers whether the custom-view feature is being adopted.",
        "display": "smartscalar",
        "size_x": 6, "size_y": 5,
        "sql": """SELECT
  DATE_TRUNC('month', TIMESTAMP) AS MONTH,
  COUNT(*) AS TOTAL_CREATIONS
FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
WHERE PAGE_SECTION = 'storage_container.eb'
  AND SUB_PAGE_SECTION = 'view_by_dropdown'
  AND ACTION_TYPE ILIKE '%custom%'
GROUP BY MONTH
ORDER BY MONTH""",
        "viz_settings": {}
    },
    {
        "num": "06",
        "name": "Most Added Columns in Custom Views",
        "description": "\"What columns are sought or added the most in custom views?\"\nReveals which data columns users value most.",
        "display": "row",
        "size_x": 12, "size_y": 7,
        "sql": """SELECT
  ACTION_TYPE AS VIEW_COLUMN,
  COUNT(*) AS TOTAL_SELECTIONS
FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
WHERE PAGE_SECTION = 'storage_container.eb'
  AND SUB_PAGE_SECTION = 'view_by_dropdown'
GROUP BY ACTION_TYPE
ORDER BY TOTAL_SELECTIONS DESC
LIMIT 15""",
        "viz_settings": {"graph.dimensions": ["VIEW_COLUMN"], "graph.metrics": ["TOTAL_SELECTIONS"]}
    },
    {
        "num": "07",
        "name": "Most Used Group-By Values",
        "description": "\"What are the most used group-by values in the storage container list?\"\nReveals which grouping dimensions users prefer.",
        "display": "row",
        "size_x": 12, "size_y": 7,
        "sql": """SELECT
  ACTION_TYPE AS GROUP_BY_VALUE,
  COUNT(*) AS TOTAL_SELECTIONS
FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
WHERE PAGE_SECTION = 'storage_container.eb'
  AND SUB_PAGE_SECTION = 'group_by_dropdown'
GROUP BY ACTION_TYPE
ORDER BY TOTAL_SELECTIONS DESC
LIMIT 15""",
        "viz_settings": {"graph.dimensions": ["GROUP_BY_VALUE"], "graph.metrics": ["TOTAL_SELECTIONS"]}
    },
    {
        "num": "08",
        "name": "Group-By Changes Over Time",
        "description": "\"How often do users change group-by values?\"\nShows the trend of group-by switching activity.",
        "display": "line",
        "size_x": 12, "size_y": 7,
        "sql": """SELECT
  DATE_TRUNC('month', TIMESTAMP) AS MONTH,
  COUNT(*) AS TOTAL_CHANGES
FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
WHERE PAGE_SECTION = 'storage_container.eb'
  AND SUB_PAGE_SECTION = 'group_by_dropdown'
GROUP BY MONTH
ORDER BY MONTH""",
        "viz_settings": {"graph.dimensions": ["MONTH"], "graph.metrics": ["TOTAL_CHANGES"]}
    },
    {
        "num": "09",
        "name": "Most Used Filters",
        "description": "\"What are the most commonly used filters in the storage container list?\"\nShows each filter's share of total interactions.",
        "display": "pie",
        "size_x": 12, "size_y": 8,
        "sql": """SELECT
  REGEXP_SUBSTR(ACTION_TYPE, '[^.]+$') AS FILTER_NAME,
  COUNT(*) AS TOTAL_USES
FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
WHERE PAGE_SECTION = 'storage_container.eb'
  AND ACTION_TYPE LIKE 'filter.%'
  AND SUB_PAGE_SECTION = 'list_filter'
  AND DESTINATION_NAME = 'storage_container/list'
GROUP BY FILTER_NAME
ORDER BY TOTAL_USES DESC""",
        "viz_settings": {}
    },
    {
        "num": "10",
        "name": "Filter Interactions Over Time",
        "description": "\"How often do users interact with filters?\"\nShows the monthly trend of filter usage.",
        "display": "line",
        "size_x": 12, "size_y": 7,
        "sql": """SELECT
  DATE_TRUNC('month', TIMESTAMP) AS MONTH,
  COUNT(*) AS TOTAL_INTERACTIONS
FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
WHERE PAGE_SECTION = 'storage_container.eb'
  AND ACTION_TYPE LIKE 'filter.%'
  AND SUB_PAGE_SECTION = 'list_filter'
  AND DESTINATION_NAME = 'storage_container/list'
GROUP BY MONTH
ORDER BY MONTH""",
        "viz_settings": {"graph.dimensions": ["MONTH"], "graph.metrics": ["TOTAL_INTERACTIONS"]}
    },
    {
        "num": "11",
        "name": "Multi-Entity Selections",
        "description": "\"Do users select multiple entities before clicking on Actions?\"\nShows whether bulk-action selection is actively used.",
        "display": "smartscalar",
        "size_x": 6, "size_y": 5,
        "sql": """SELECT
  DATE_TRUNC('month', TIMESTAMP) AS MONTH,
  COUNT(*) AS TOTAL_SELECTIONS
FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
WHERE PAGE_SECTION = 'storage_container.eb'
  AND ACTION_TYPE = 'listview.select'
  AND DESTINATION_NAME = 'storage_container/list'
GROUP BY MONTH
ORDER BY MONTH""",
        "viz_settings": {}
    },
    {
        "num": "12",
        "name": "Most Interacted Update Form Fields",
        "description": "\"What are the fields users interact with most in the Update form?\"\nShows each form field's share of interaction.",
        "display": "pie",
        "size_x": 12, "size_y": 8,
        "sql": """SELECT
  REGEXP_SUBSTR(ACTION_TYPE, '[^.]+$') AS FIELD_NAME,
  COUNT(*) AS TOTAL_INTERACTIONS
FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
WHERE PAGE_SECTION = 'update_storage_container'
  AND ACTION_TYPE LIKE 'input_change.%'
  AND DESTINATION_NAME = 'storage_container/update_form'
GROUP BY FIELD_NAME
ORDER BY TOTAL_INTERACTIONS DESC""",
        "viz_settings": {}
    },
    {
        "num": "13",
        "name": "Storage Container Creations Over Time",
        "description": "\"How frequently are users creating a storage container?\"\nShows the monthly creation trend.",
        "display": "line",
        "size_x": 12, "size_y": 7,
        "sql": """SELECT
  DATE_TRUNC('month', TIMESTAMP) AS MONTH,
  COUNT(*) AS TOTAL_CREATIONS
FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
WHERE PAGE_SECTION = 'storage_container.eb'
  AND ACTION_TYPE = 'create_storage_container.start'
GROUP BY MONTH
ORDER BY MONTH""",
        "viz_settings": {"graph.dimensions": ["MONTH"], "graph.metrics": ["TOTAL_CREATIONS"]}
    },
    {
        "num": "14",
        "name": "Most Used Advanced Settings",
        "description": "\"What advanced-settings options are used the most during storage container creation?\"\nShows which advanced configuration options users engage with.",
        "display": "pie",
        "size_x": 12, "size_y": 8,
        "sql": """SELECT
  REGEXP_SUBSTR(ACTION_TYPE, '[^.]+$') AS SETTING_NAME,
  COUNT(*) AS TOTAL_INTERACTIONS
FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
WHERE PAGE_SECTION = 'create_storage_container'
  AND ACTION_TYPE LIKE 'input_change.%'
  AND DESTINATION_NAME = 'storage_container/create_form'
GROUP BY SETTING_NAME
ORDER BY TOTAL_INTERACTIONS DESC""",
        "viz_settings": {}
    },
    {
        "num": "15",
        "name": "Reserved vs Advertised Capacity",
        "description": "\"Do users interact with reserved capacity and advertised capacity fields?\"\nShows which capacity field is used more.",
        "display": "bar",
        "size_x": 12, "size_y": 8,
        "sql": """WITH labels AS (
  SELECT 'Reserved Capacity' AS CAPACITY_TYPE, 'input_change.reserved_capacity' AS ACTION_KEY
  UNION ALL
  SELECT 'Advertised Capacity', 'input_change.advertised_capacity'
),
counts AS (
  SELECT
    ACTION_TYPE,
    COUNT(*) AS TOTAL_INTERACTIONS
  FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
  WHERE PAGE_SECTION = 'create_storage_container'
    AND ACTION_TYPE IN ('input_change.reserved_capacity', 'input_change.advertised_capacity')
    AND DESTINATION_NAME = 'storage_container/create_form'
  GROUP BY ACTION_TYPE
)
SELECT
  l.CAPACITY_TYPE,
  COALESCE(c.TOTAL_INTERACTIONS, 0) AS TOTAL_INTERACTIONS
FROM labels l
LEFT JOIN counts c ON l.ACTION_KEY = c.ACTION_TYPE
ORDER BY TOTAL_INTERACTIONS DESC""",
        "viz_settings": {"graph.dimensions": ["CAPACITY_TYPE"], "graph.metrics": ["TOTAL_INTERACTIONS"]}
    },
    {
        "num": "16",
        "name": "Filesystem Allowlist Interactions",
        "description": "\"Do users interact with Filesystem Allowlists?\"\nAnswers whether this feature is being used at all.",
        "display": "smartscalar",
        "size_x": 6, "size_y": 5,
        "sql": """SELECT
  DATE_TRUNC('month', TIMESTAMP) AS MONTH,
  COUNT(*) AS TOTAL_INTERACTIONS
FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
WHERE PAGE_SECTION = 'create_storage_container'
  AND ACTION_TYPE LIKE 'input_change.filesystem%'
  AND DESTINATION_NAME = 'storage_container/create_form'
GROUP BY MONTH
ORDER BY MONTH""",
        "viz_settings": {}
    },
    {
        "num": "17",
        "name": "Tooltip Icon Interactions",
        "description": "\"Do users interact with tooltip icons beside properties?\"\nShows how often users seek contextual help.",
        "display": "bar",
        "size_x": 12, "size_y": 8,
        "sql": """SELECT
  REPLACE(ACTION_TYPE, '.tooltip', '') AS PROPERTY_NAME,
  COUNT(*) AS TOTAL_INTERACTIONS
FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
WHERE PAGE_SECTION = 'create_storage_container'
  AND ACTION_TYPE ILIKE '%tooltip%'
  AND DESTINATION_NAME = 'storage_container/create_form'
GROUP BY PROPERTY_NAME
ORDER BY TOTAL_INTERACTIONS DESC""",
        "viz_settings": {"graph.dimensions": ["PROPERTY_NAME"], "graph.metrics": ["TOTAL_INTERACTIONS"]}
    },
    {
        "num": "18",
        "name": "Header Help Icon Clicks",
        "description": "\"Do users interact with the [?] help icon on the header?\"\nAnswers whether users seek header-level help.",
        "display": "smartscalar",
        "size_x": 6, "size_y": 5,
        "sql": """SELECT
  DATE_TRUNC('month', TIMESTAMP) AS MONTH,
  COUNT(*) AS TOTAL_CLICKS
FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
WHERE PAGE_SECTION = 'create_storage_container'
  AND ACTION_TYPE LIKE 'header.help%'
  AND DESTINATION_NAME = 'storage_container/create_form'
GROUP BY MONTH
ORDER BY MONTH""",
        "viz_settings": {}
    },
    {
        "num": "19",
        "name": "Modal Dismissals — Close vs Cancel",
        "description": "\"Do users click X or Cancel to close the modal without changes?\"\nShows which dismissal method is preferred.",
        "display": "bar",
        "size_x": 12, "size_y": 8,
        "sql": """WITH labels AS (
  SELECT 'X (Close)' AS DISMISS_METHOD, 'modal.close' AS ACTION_KEY
  UNION ALL
  SELECT 'Cancel Button', 'modal.cancel'
),
counts AS (
  SELECT
    ACTION_TYPE,
    COUNT(*) AS TOTAL_DISMISSALS
  FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
  WHERE PAGE_SECTION = 'create_storage_container'
    AND ACTION_TYPE IN ('modal.close', 'modal.cancel')
    AND DESTINATION_NAME = 'storage_container/create_form'
  GROUP BY ACTION_TYPE
)
SELECT
  l.DISMISS_METHOD,
  COALESCE(c.TOTAL_DISMISSALS, 0) AS TOTAL_DISMISSALS
FROM labels l
LEFT JOIN counts c ON l.ACTION_KEY = c.ACTION_TYPE
ORDER BY TOTAL_DISMISSALS DESC""",
        "viz_settings": {"graph.dimensions": ["DISMISS_METHOD"], "graph.metrics": ["TOTAL_DISMISSALS"]}
    },
    {
        "num": "20",
        "name": "Storage Container Creation Duration",
        "description": "\"How much time does the user spend creating a storage container (advanced settings opened vs not)?\"\nShows avg, median, min, max creation times segmented by advanced-settings usage.",
        "display": "table",
        "size_x": 18, "size_y": 8,
        "sql": """WITH starts AS (
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
  SETTINGS_GROUP,
  COUNT(*) AS TOTAL_SESSIONS,
  ROUND(AVG(duration_seconds), 0) AS AVG_DURATION_SECONDS,
  ROUND(MEDIAN(duration_seconds), 0) AS MEDIAN_DURATION_SECONDS,
  MIN(duration_seconds) AS MIN_DURATION_SECONDS,
  MAX(duration_seconds) AS MAX_DURATION_SECONDS
FROM paired
WHERE duration_seconds > 0
  AND duration_seconds < 3600
GROUP BY SETTINGS_GROUP
ORDER BY SETTINGS_GROUP""",
        "viz_settings": {}
    },
    {
        "num": "21",
        "name": "Replication Factor Info Banner Interactions",
        "description": "\"Do users hover or click the information banner around the Replication Factor field?\"\nShows whether users seek additional context about replication factor.",
        "display": "smartscalar",
        "size_x": 6, "size_y": 5,
        "sql": """SELECT
  DATE_TRUNC('month', TIMESTAMP) AS MONTH,
  COUNT(*) AS TOTAL_INTERACTIONS
FROM NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT
WHERE PAGE_SECTION = 'create_storage_container'
  AND ACTION_TYPE LIKE 'replication_factor.%'
  AND DESTINATION_NAME = 'storage_container/create_form'
GROUP BY MONTH
ORDER BY MONTH""",
        "viz_settings": {}
    },
]


def create_card(w):
    body = {
        "name": w["name"],
        "description": w["description"],
        "display": w["display"],
        "visualization_settings": w["viz_settings"],
        "dataset_query": {
            "database": DATABASE_ID,
            "type": "native",
            "native": {
                "query": w["sql"],
                "template-tags": {}
            }
        }
    }
    return api("POST", "/api/card", body)


def auto_layout(widgets_with_cards):
    """Pack widgets into an 18-column grid.
    
    Strategy: place left-to-right. When a widget doesn't fit
    in the remaining columns, wrap to the next row.
    Scalars (6 wide) naturally pair up 3-per-row or fill gaps
    beside 12-wide charts.
    """
    dashcards = []
    col_cursor = 0
    row_cursor = 0
    current_row_height = 0

    for idx, (w, card_id) in enumerate(widgets_with_cards):
        sx = w["size_x"]
        sy = w["size_y"]

        if col_cursor + sx > GRID_WIDTH:
            row_cursor += current_row_height
            col_cursor = 0
            current_row_height = 0

        dashcards.append({
            "id": -(idx + 1),
            "card_id": card_id,
            "row": row_cursor,
            "col": col_cursor,
            "size_x": sx,
            "size_y": sy,
            "parameter_mappings": [],
            "visualization_settings": {}
        })

        col_cursor += sx
        current_row_height = max(current_row_height, sy)

    return dashcards


def main():
    print("=" * 60)
    print("Storage Container Telemetry — Widget Creation (v2)")
    print("=" * 60)
    print(f"\nSizes: pie=12×8, bar=12×8, line=12×7, row=12×7, scalar=6×5, table=18×8")
    print(f"Target dashboard: {BASE_URL}/dashboard/{DASHBOARD_ID}")
    print(f"Creating {len(WIDGETS)} cards...\n")

    created = []
    errors = []

    for w in WIDGETS:
        try:
            result = create_card(w)
            card_id = result["id"]
            card_url = f"{BASE_URL}/question/{card_id}"
            print(f"  [OK] #{w['num']} {w['name']} → card #{card_id} ({w['display']} {w['size_x']}×{w['size_y']})")
            created.append((w, card_id))
            time.sleep(0.2)
        except Exception as e:
            print(f"  [FAIL] #{w['num']} {w['name']} → {e}")
            errors.append((w, str(e)))

    print(f"\nCreated {len(created)}/{len(WIDGETS)} cards. Errors: {len(errors)}")

    if not created:
        print("No cards created — skipping dashboard update.")
        return

    print(f"\nArranging {len(created)} cards on dashboard #{DASHBOARD_ID}...")

    existing = api("GET", f"/api/dashboard/{DASHBOARD_ID}")
    existing_dashcards = existing.get("dashcards", existing.get("ordered_cards", []))

    if existing_dashcards:
        max_row = max(dc["row"] + dc["size_y"] for dc in existing_dashcards)
    else:
        max_row = 0

    new_dashcards = auto_layout(created)
    for dc in new_dashcards:
        dc["row"] += max_row

    all_dashcards = list(existing_dashcards) + new_dashcards

    api("PUT", f"/api/dashboard/{DASHBOARD_ID}", {"dashcards": all_dashcards})

    total_height = max(dc["row"] + dc["size_y"] for dc in new_dashcards)

    print(f"\n{'='*60}")
    print(f"Dashboard updated with {len(new_dashcards)} cards!")
    print(f"View: {BASE_URL}/dashboard/{DASHBOARD_ID}")
    print(f"Total dashboard height: {total_height} grid rows")
    print(f"{'='*60}")

    if errors:
        print(f"\n--- Errors ({len(errors)}) ---")
        for w, err in errors:
            print(f"  #{w['num']} {w['name']}: {err}")

    print("\n--- Layout ---")
    for dc in new_dashcards:
        card_name = next((w["name"] for w, cid in created if cid == dc["card_id"]), "?")
        disp = next((w["display"] for w, cid in created if cid == dc["card_id"]), "?")
        print(f"  #{dc['card_id']:>3d}  col={dc['col']:>2d}  row={dc['row']:>2d}  {dc['size_x']:>2d}×{dc['size_y']}  {disp:<12s}  {card_name}")

    results = {
        "dashboard_url": f"{BASE_URL}/dashboard/{DASHBOARD_ID}",
        "cards_created": len(created),
        "cards_failed": len(errors),
        "cards": [{"num": w["num"], "name": w["name"], "card_id": cid, "display": w["display"],
                    "size_x": w["size_x"], "size_y": w["size_y"],
                    "url": f"{BASE_URL}/question/{cid}"} for w, cid in created],
        "layout": [{"card_id": dc["card_id"], "col": dc["col"], "row": dc["row"],
                     "size_x": dc["size_x"], "size_y": dc["size_y"]} for dc in new_dashcards],
        "errors": [{"num": w["num"], "name": w["name"], "error": err} for w, err in errors]
    }
    with open("creation_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to creation_results.json")


if __name__ == "__main__":
    main()
