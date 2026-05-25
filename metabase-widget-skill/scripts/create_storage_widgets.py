#!/usr/bin/env python3
"""Create all 21 storage-container telemetry widgets and add them to dashboard 12.

Reads config from .env, creates each card via POST /api/card (native SQL),
then places them all on the target dashboard via PUT /api/dashboard/{id}.

Usage:
    python3 scripts/create_storage_widgets.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from metabase_api import get_config, request_with_retry, load_dotenv, ApiError

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DASHBOARD_ID = 12
TABLE = "NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT"


def widget_definitions() -> list[dict]:
    """Return all 21 widget specs with updated chart types per user preferences."""
    return [
        {
            "number": 1,
            "name": "Column Sorting Distribution",
            "description": (
                '"How often do users sort columns in the storage container list?"\n'
                "Shows which columns users sort on most frequently, revealing which data attributes drive decision-making."
            ),
            "display": "pie",
            "visualization_settings": {},
            "sql": f"""
SELECT
  REGEXP_SUBSTR(ACTION_TYPE, '[^.]+$') AS SORTED_COLUMN,
  COUNT(*) AS TOTAL_SORTS
FROM {TABLE}
WHERE PAGE_SECTION = 'storage_container.eb'
  AND DESTINATION_NAME = 'storage_container/list'
  AND ACTION_TYPE LIKE 'sort\\_column.%'
GROUP BY SORTED_COLUMN
ORDER BY TOTAL_SORTS DESC
""",
        },
        {
            "number": 2,
            "name": "Row Link Click Volume",
            "description": (
                '"How often do users click row links (e.g. cluster name) in the storage container list?"\n'
                "Measures how actively users navigate into container details from the list."
            ),
            "display": "bar",
            "visualization_settings": {
                "graph.dimensions": ["CLICK_MONTH"],
                "graph.metrics": ["TOTAL_CLICKS"],
            },
            "sql": f"""
SELECT
  DATE_TRUNC('month', TIMESTAMP) AS CLICK_MONTH,
  COUNT(*) AS TOTAL_CLICKS
FROM {TABLE}
WHERE PAGE_SECTION = 'storage_container.eb'
  AND SUB_PAGE_SECTION = 'eb_list'
  AND ACTION_TYPE = 'container_name.click'
  AND DESTINATION_NAME = 'storage_container/list'
GROUP BY CLICK_MONTH
ORDER BY CLICK_MONTH ASC
""",
        },
        {
            "number": 3,
            "name": "Checkbox Selection Volume",
            "description": (
                '"How often do users select checkboxes in the storage container list?"\n'
                "Indicates how frequently users intend to perform bulk actions."
            ),
            "display": "scalar",
            "visualization_settings": {},
            "sql": f"""
SELECT COUNT(*) AS TOTAL_SELECTIONS
FROM {TABLE}
WHERE PAGE_SECTION = 'storage_container.eb'
  AND SUB_PAGE_SECTION = 'eb_list'
  AND ACTION_TYPE = 'listview.select'
  AND DESTINATION_NAME = 'storage_container/list'
""",
        },
        {
            "number": 4,
            "name": "View-By Selections by Type",
            "description": (
                '"How often do users change column views?"\n'
                "Shows which views users select and how frequently each is used."
            ),
            "display": "row",
            "visualization_settings": {
                "graph.dimensions": ["VIEW_SELECTED"],
                "graph.metrics": ["TOTAL_USES"],
            },
            "sql": f"""
SELECT
  ACTION_TYPE AS VIEW_SELECTED,
  COUNT(*) AS TOTAL_USES
FROM {TABLE}
WHERE PAGE_SECTION = 'storage_container.eb'
  AND SUB_PAGE_SECTION = 'view_by_dropdown'
GROUP BY ACTION_TYPE
ORDER BY TOTAL_USES DESC
""",
        },
        {
            "number": 5,
            "name": "Custom View Creation Count",
            "description": (
                '"Do users create custom views?"\n'
                "Answers whether the custom-view feature sees real adoption."
            ),
            "display": "scalar",
            "visualization_settings": {},
            "sql": f"""
SELECT COUNT(*) AS CUSTOM_VIEW_EVENTS
FROM {TABLE}
WHERE PAGE_SECTION = 'storage_container.eb'
  AND SUB_PAGE_SECTION = 'view_by_dropdown'
  AND ACTION_TYPE ILIKE '%custom%'
""",
        },
        {
            "number": 6,
            "name": "Most Added Columns in Custom Views",
            "description": (
                '"What columns are sought or added the most in custom views?"\n'
                "Reveals which data attributes users prioritize when customizing their list view."
            ),
            "display": "row",
            "visualization_settings": {
                "graph.dimensions": ["VIEW_SELECTED"],
                "graph.metrics": ["TOTAL_SELECTIONS"],
            },
            "sql": f"""
SELECT
  ACTION_TYPE AS VIEW_SELECTED,
  COUNT(*) AS TOTAL_SELECTIONS
FROM {TABLE}
WHERE PAGE_SECTION = 'storage_container.eb'
  AND SUB_PAGE_SECTION = 'view_by_dropdown'
GROUP BY ACTION_TYPE
ORDER BY TOTAL_SELECTIONS DESC
LIMIT 15
""",
        },
        {
            "number": 7,
            "name": "Most Used Group-By Values",
            "description": (
                '"What are the most-used group-by values?"\n'
                "Shows which grouping dimensions users find most useful for organizing their storage container list."
            ),
            "display": "row",
            "visualization_settings": {
                "graph.dimensions": ["GROUP_BY_VALUE"],
                "graph.metrics": ["TOTAL_USES"],
            },
            "sql": f"""
SELECT
  ACTION_TYPE AS GROUP_BY_VALUE,
  COUNT(*) AS TOTAL_USES
FROM {TABLE}
WHERE PAGE_SECTION = 'storage_container.eb'
  AND SUB_PAGE_SECTION = 'group_by_dropdown'
GROUP BY ACTION_TYPE
ORDER BY TOTAL_USES DESC
LIMIT 10
""",
        },
        {
            "number": 8,
            "name": "Group-By Changes by Value",
            "description": (
                '"How often do users change group-by values?"\n'
                "Shows which group-by values users switch to most frequently."
            ),
            "display": "row",
            "visualization_settings": {
                "graph.dimensions": ["GROUP_BY_VALUE"],
                "graph.metrics": ["TOTAL_CHANGES"],
            },
            "sql": f"""
SELECT
  ACTION_TYPE AS GROUP_BY_VALUE,
  COUNT(*) AS TOTAL_CHANGES
FROM {TABLE}
WHERE PAGE_SECTION = 'storage_container.eb'
  AND SUB_PAGE_SECTION = 'group_by_dropdown'
GROUP BY ACTION_TYPE
ORDER BY TOTAL_CHANGES DESC
""",
        },
        {
            "number": 9,
            "name": "Most Used List Filters",
            "description": (
                '"What are the most commonly used filters?"\n'
                "Reveals which filter criteria users rely on most when narrowing their storage container list."
            ),
            "display": "pie",
            "visualization_settings": {},
            "sql": f"""
SELECT
  REGEXP_SUBSTR(ACTION_TYPE, '[^.]+$') AS FILTER_NAME,
  COUNT(*) AS TOTAL_USES
FROM {TABLE}
WHERE PAGE_SECTION = 'storage_container.eb'
  AND SUB_PAGE_SECTION = 'list_filter'
  AND DESTINATION_NAME = 'storage_container/list'
  AND ACTION_TYPE LIKE 'filter.%'
GROUP BY FILTER_NAME
ORDER BY TOTAL_USES DESC
""",
        },
        {
            "number": 10,
            "name": "Filter Interaction over Time",
            "description": (
                '"How often do users interact with filters?"\n'
                "Shows whether filter usage is growing or stable over time."
            ),
            "display": "line",
            "visualization_settings": {
                "graph.dimensions": ["INTERACTION_MONTH"],
                "graph.metrics": ["TOTAL_INTERACTIONS"],
            },
            "sql": f"""
SELECT
  DATE_TRUNC('month', TIMESTAMP) AS INTERACTION_MONTH,
  COUNT(*) AS TOTAL_INTERACTIONS
FROM {TABLE}
WHERE PAGE_SECTION = 'storage_container.eb'
  AND SUB_PAGE_SECTION = 'list_filter'
  AND DESTINATION_NAME = 'storage_container/list'
  AND ACTION_TYPE LIKE 'filter.%'
GROUP BY INTERACTION_MONTH
ORDER BY INTERACTION_MONTH ASC
""",
        },
        {
            "number": 11,
            "name": "Multi-Entity Checkbox Selections",
            "description": (
                '"Do users select multiple entities before clicking on Actions?"\n'
                "Indicates whether users actively engage with bulk-action workflows."
            ),
            "display": "scalar",
            "visualization_settings": {},
            "sql": f"""
SELECT COUNT(*) AS TOTAL_MULTI_SELECTIONS
FROM {TABLE}
WHERE PAGE_SECTION = 'storage_container.eb'
  AND SUB_PAGE_SECTION = 'eb_list'
  AND ACTION_TYPE = 'listview.select'
  AND DESTINATION_NAME = 'storage_container/list'
""",
        },
        {
            "number": 12,
            "name": "Most Interacted Fields in Update Form",
            "description": (
                '"What fields do users interact with most in the Update form?"\n'
                "Reveals which properties users actually modify when updating storage containers."
            ),
            "display": "pie",
            "visualization_settings": {},
            "sql": f"""
SELECT
  INITCAP(REPLACE(REGEXP_SUBSTR(ACTION_TYPE, '[^.]+$'), '_', ' ')) AS FIELD_NAME,
  COUNT(*) AS TOTAL_INTERACTIONS
FROM {TABLE}
WHERE PAGE_SECTION = 'update_storage_container'
  AND DESTINATION_NAME = 'storage_container/update_form'
  AND ACTION_TYPE LIKE 'input\\_change.%'
GROUP BY FIELD_NAME
ORDER BY TOTAL_INTERACTIONS DESC
""",
        },
        {
            "number": 13,
            "name": "Storage Container Creation over Time",
            "description": (
                '"How frequently are users creating a storage container?"\n'
                "Shows the volume and trend of storage container creation activity."
            ),
            "display": "line",
            "visualization_settings": {
                "graph.dimensions": ["CREATED_MONTH"],
                "graph.metrics": ["CREATION_COUNT"],
            },
            "sql": f"""
SELECT
  DATE_TRUNC('month', TIMESTAMP) AS CREATED_MONTH,
  COUNT(*) AS CREATION_COUNT
FROM {TABLE}
WHERE PAGE_SECTION = 'storage_container.eb'
  AND SUB_PAGE_SECTION = 'actions_view'
  AND ACTION_TYPE = 'create_storage_container.start'
  AND DESTINATION_NAME = 'storage_container/list'
GROUP BY CREATED_MONTH
ORDER BY CREATED_MONTH ASC
""",
        },
        {
            "number": 14,
            "name": "Most Used Advanced Settings in Create Form",
            "description": (
                '"What options in advanced settings are used the most?"\n'
                "Reveals which advanced configuration knobs users actually touch during storage container creation."
            ),
            "display": "pie",
            "visualization_settings": {},
            "sql": f"""
SELECT
  INITCAP(REPLACE(REGEXP_SUBSTR(ACTION_TYPE, '[^.]+$'), '_', ' ')) AS SETTING_NAME,
  COUNT(*) AS TOTAL_INTERACTIONS
FROM {TABLE}
WHERE PAGE_SECTION = 'create_storage_container'
  AND DESTINATION_NAME = 'storage_container/create_form'
  AND ACTION_TYPE LIKE 'input\\_change.%'
GROUP BY SETTING_NAME
ORDER BY TOTAL_INTERACTIONS DESC
""",
        },
        {
            "number": 15,
            "name": "Capacity Field Interactions",
            "description": (
                '"Do users interact with reserved capacity and advertised capacity fields?"\n'
                "Shows whether these capacity fields see real engagement and how they compare."
            ),
            "display": "pie",
            "visualization_settings": {},
            "sql": f"""
SELECT
  INITCAP(REPLACE(REGEXP_SUBSTR(ACTION_TYPE, '[^.]+$'), '_', ' ')) AS CAPACITY_FIELD,
  COUNT(*) AS TOTAL_INTERACTIONS
FROM {TABLE}
WHERE PAGE_SECTION = 'create_storage_container'
  AND DESTINATION_NAME = 'storage_container/create_form'
  AND ACTION_TYPE LIKE 'input\\_change.%'
  AND ACTION_TYPE ILIKE '%capacity%'
GROUP BY CAPACITY_FIELD
ORDER BY TOTAL_INTERACTIONS DESC
""",
        },
        {
            "number": 16,
            "name": "Filesystem Allowlists Interaction Count",
            "description": (
                '"Do users interact with Filesystem Allowlists?"\n'
                "Answers whether the allowlists feature sees real usage during container creation."
            ),
            "display": "scalar",
            "visualization_settings": {},
            "sql": f"""
SELECT COUNT(*) AS ALLOWLIST_INTERACTIONS
FROM {TABLE}
WHERE PAGE_SECTION = 'create_storage_container'
  AND DESTINATION_NAME = 'storage_container/create_form'
  AND ACTION_TYPE LIKE 'input\\_change.%'
  AND ACTION_TYPE ILIKE '%allowlist%'
""",
        },
        {
            "number": 17,
            "name": "Property Tooltip Interactions by Field",
            "description": (
                '"Do users interact with the [i] and [?] mark icons beside properties?"\n'
                "Shows which fields\u2019 tooltips users click most, indicating where they need more guidance."
            ),
            "display": "row",
            "visualization_settings": {
                "graph.dimensions": ["TOOLTIP_FIELD"],
                "graph.metrics": ["TOTAL_INTERACTIONS"],
            },
            "sql": f"""
SELECT
  INITCAP(REPLACE(SPLIT_PART(ACTION_TYPE, '.', 1), '_', ' ')) AS TOOLTIP_FIELD,
  COUNT(*) AS TOTAL_INTERACTIONS
FROM {TABLE}
WHERE PAGE_SECTION = 'create_storage_container'
  AND DESTINATION_NAME = 'storage_container/create_form'
  AND ACTION_TYPE ILIKE '%tooltip%'
GROUP BY TOOLTIP_FIELD
ORDER BY TOTAL_INTERACTIONS DESC
LIMIT 15
""",
        },
        {
            "number": 18,
            "name": "Header Help Icon Clicks",
            "description": (
                '"Do users interact with the [?] help icon on the header?"\n'
                "Measures whether users seek contextual help from the form header."
            ),
            "display": "scalar",
            "visualization_settings": {},
            "sql": f"""
SELECT COUNT(*) AS HEADER_HELP_CLICKS
FROM {TABLE}
WHERE PAGE_SECTION = 'create_storage_container'
  AND DESTINATION_NAME = 'storage_container/create_form'
  AND ACTION_TYPE ILIKE '%header%'
  AND ACTION_TYPE ILIKE '%tooltip%'
""",
        },
        {
            "number": 19,
            "name": "Cancel vs Close (X) on Create Modal",
            "description": (
                '"Do users click \'X\' or \'Cancel\' to close the create modal without changes?"\n'
                "Shows whether users abandon the creation flow and which exit method they prefer."
            ),
            "display": "bar",
            "visualization_settings": {
                "graph.dimensions": ["EXIT_METHOD"],
                "graph.metrics": ["TOTAL_EVENTS"],
            },
            "sql": f"""
WITH labels AS (
  SELECT 'Cancel Button' AS EXIT_METHOD
  UNION ALL
  SELECT 'Close (X)' AS EXIT_METHOD
),
counts AS (
  SELECT
    CASE
      WHEN ACTION_TYPE ILIKE '%cancel%' THEN 'Cancel Button'
      WHEN ACTION_TYPE ILIKE '%close%' THEN 'Close (X)'
    END AS EXIT_METHOD,
    COUNT(*) AS TOTAL_EVENTS
  FROM {TABLE}
  WHERE PAGE_SECTION = 'create_storage_container'
    AND DESTINATION_NAME = 'storage_container/create_form'
    AND (ACTION_TYPE ILIKE '%cancel%' OR ACTION_TYPE ILIKE '%close%')
  GROUP BY 1
)
SELECT
  l.EXIT_METHOD,
  COALESCE(c.TOTAL_EVENTS, 0) AS TOTAL_EVENTS
FROM labels l
LEFT JOIN counts c ON l.EXIT_METHOD = c.EXIT_METHOD
ORDER BY TOTAL_EVENTS DESC
""",
        },
        {
            "number": 20,
            "name": "Time to Create Storage Container",
            "description": (
                '"How much time do users spend creating a storage container, with versus without advanced settings?"\n'
                "Shows whether advanced settings significantly lengthen the creation workflow."
            ),
            "display": "table",
            "visualization_settings": {},
            "sql": f"""
WITH create_start AS (
  SELECT
    SESSION_ID,
    TIMESTAMP AS START_TS
  FROM {TABLE}
  WHERE PAGE_SECTION = 'storage_container.eb'
    AND ACTION_TYPE = 'create_storage_container.start'
),
create_submit AS (
  SELECT
    SESSION_ID,
    TIMESTAMP AS END_TS
  FROM {TABLE}
  WHERE PAGE_SECTION = 'create_storage_container'
    AND ACTION_TYPE ILIKE '%submit%'
),
adv_settings AS (
  SELECT DISTINCT SESSION_ID
  FROM {TABLE}
  WHERE PAGE_SECTION = 'create_storage_container'
    AND ACTION_TYPE ILIKE '%advanced%'
),
paired AS (
  SELECT
    s.SESSION_ID,
    s.START_TS,
    e.END_TS,
    TIMESTAMPDIFF('second', s.START_TS, e.END_TS) AS DURATION_SECONDS,
    CASE WHEN a.SESSION_ID IS NOT NULL THEN 'With Advanced Settings'
         ELSE 'Without Advanced Settings'
    END AS SETTINGS_GROUP
  FROM create_start s
  INNER JOIN create_submit e
    ON s.SESSION_ID = e.SESSION_ID
    AND e.END_TS > s.START_TS
  LEFT JOIN adv_settings a
    ON s.SESSION_ID = a.SESSION_ID
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY s.SESSION_ID ORDER BY e.END_TS ASC
  ) = 1
)
SELECT
  SETTINGS_GROUP,
  COUNT(*) AS SESSIONS,
  ROUND(AVG(DURATION_SECONDS), 0) AS AVG_SECONDS,
  ROUND(MEDIAN(DURATION_SECONDS), 0) AS MEDIAN_SECONDS,
  MIN(DURATION_SECONDS) AS MIN_SECONDS,
  MAX(DURATION_SECONDS) AS MAX_SECONDS
FROM paired
WHERE DURATION_SECONDS > 0
  AND DURATION_SECONDS < 3600
GROUP BY SETTINGS_GROUP
ORDER BY SETTINGS_GROUP
""",
        },
        {
            "number": 21,
            "name": "Replication Factor Info Banner Interactions",
            "description": (
                '"Do users hover or click the information banner around the Replication Factor field?"\n'
                "Measures whether users seek additional guidance on replication factor configuration."
            ),
            "display": "scalar",
            "visualization_settings": {},
            "sql": f"""
SELECT COUNT(*) AS REPLICATION_INFO_INTERACTIONS
FROM {TABLE}
WHERE PAGE_SECTION = 'create_storage_container'
  AND DESTINATION_NAME = 'storage_container/create_form'
  AND ACTION_TYPE ILIKE '%replication_factor%'
""",
        },
    ]


SIZE_MAP = {
    "scalar": (4, 3),
    "smartscalar": (4, 3),
    "bar": (6, 4),
    "row": (6, 4),
    "line": (6, 4),
    "pie": (6, 4),
    "table": (18, 6),
    "funnel": (9, 5),
}


def layout_dashcards(cards: list[dict], existing_dashcards: list[dict]) -> list[dict]:
    max_row = 0
    for dc in existing_dashcards:
        bottom = dc["row"] + dc["size_y"]
        if bottom > max_row:
            max_row = bottom

    col_cursor = 0
    row_cursor = max_row
    current_row_height = 0
    dashcards = list(existing_dashcards)

    for i, card in enumerate(cards):
        display = card["display"]
        sx, sy = SIZE_MAP.get(display, (6, 4))
        if col_cursor + sx > 18:
            row_cursor += current_row_height
            col_cursor = 0
            current_row_height = 0
        dashcards.append({
            "id": -(i + 1),
            "card_id": card["card_id"],
            "row": row_cursor,
            "col": col_cursor,
            "size_x": sx,
            "size_y": sy,
            "parameter_mappings": [],
            "visualization_settings": {},
        })
        col_cursor += sx
        current_row_height = max(current_row_height, sy)

    return dashcards


def main() -> int:
    cfg = get_config()
    db_id = cfg["database_id"]
    collection_id = cfg["default_collection_id"]

    widgets = widget_definitions()
    results: list[dict] = []
    created_cards: list[dict] = []

    print(f"Creating {len(widgets)} cards on {cfg['base_url']} (db={db_id})...\n")

    for w in widgets:
        num = w["number"]
        name = w["name"]
        print(f"  [{num:02d}/21] Creating: {name} ({w['display']}) ...", end=" ", flush=True)

        payload = {
            "name": name,
            "description": w["description"],
            "collection_id": collection_id,
            "display": w["display"],
            "visualization_settings": w["visualization_settings"],
            "dataset_query": {
                "database": db_id,
                "type": "native",
                "native": {
                    "query": w["sql"].strip(),
                    "template-tags": {},
                },
            },
        }

        try:
            card = request_with_retry("POST", "/api/card", body=payload)
            card_id = card["id"]
            card_url = f"{cfg['base_url']}/question/{card_id}"
            print(f"OK (card #{card_id})")
            results.append({
                "number": num,
                "status": "created",
                "card_id": card_id,
                "card_url": card_url,
            })
            created_cards.append({
                "card_id": card_id,
                "display": w["display"],
                "name": name,
            })
        except ApiError as e:
            err_msg = str(e)[:300]
            print(f"FAILED: {err_msg}")
            results.append({
                "number": num,
                "status": "failed",
                "error": err_msg,
            })

        time.sleep(0.2)

    created_count = sum(1 for r in results if r["status"] == "created")
    failed_count = sum(1 for r in results if r["status"] != "created")

    print(f"\n--- Card creation: {created_count} created, {failed_count} failed ---\n")

    if not created_cards:
        print("No cards created. Skipping dashboard update.")
        _write_results(results)
        return 1

    print(f"Clearing dashboard {DASHBOARD_ID} and adding {len(created_cards)} new cards...")
    try:
        # Clear existing dashcards first (fresh layout)
        request_with_retry("PUT", f"/api/dashboard/{DASHBOARD_ID}", body={"dashcards": []})
        all_dashcards = layout_dashcards(created_cards, [])

        updated_dash = request_with_retry(
            "PUT",
            f"/api/dashboard/{DASHBOARD_ID}",
            body={"dashcards": all_dashcards},
        )
        dash_url = f"{cfg['base_url']}/dashboard/{DASHBOARD_ID}"
        dc_count = len(updated_dash.get("dashcards", []))
        print(f"Dashboard updated: {dc_count} total dashcards")
        print(f"Dashboard URL: {dash_url}")

        results.append({
            "dashboard_id": DASHBOARD_ID,
            "dashboard_url": dash_url,
            "dashboard_name": updated_dash.get("name", ""),
        })
    except ApiError as e:
        print(f"FAILED to update dashboard: {e}", file=sys.stderr)
        results.append({
            "dashboard_id": DASHBOARD_ID,
            "dashboard_error": str(e)[:500],
        })

    _write_results(results)

    print(f"\n{'='*60}")
    print(f"  Created: {created_count} of {len(widgets)} widgets")
    print(f"  Failed:  {failed_count}")
    if any("dashboard_url" in r for r in results):
        dash_url = next(r["dashboard_url"] for r in results if "dashboard_url" in r)
        print(f"  Dashboard: {dash_url}")
    print(f"{'='*60}")

    return 0 if failed_count == 0 else 1


def _write_results(results: list[dict]) -> None:
    out_path = str(Path(__file__).resolve().parent.parent / "creation-results.json")
    Path(out_path).write_text(json.dumps(results, indent=2) + "\n")
    print(f"Results written to: {out_path}")


if __name__ == "__main__":
    sys.exit(main())
