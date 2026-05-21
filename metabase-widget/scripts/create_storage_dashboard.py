#!/usr/bin/env python3
"""Create the shashi-storage-widget-automation dashboard with the first 5 widgets.

Reads config from .env and uses the metabase_api module to create cards + dashboard.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from metabase_api import get_config, load_dotenv, request_with_retry

load_dotenv(Path(__file__).parent.parent / ".env")

DASHBOARD_NAME = "shashi-storage-widget-automation"
DASHBOARD_DESCRIPTION = (
    "Automated dashboard for Storage Container telemetry — "
    "first 5 requirements from the storage telemetry requirement sheet."
)

TABLE_NAME = "NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT"

WIDGETS = [
    {
        "number": 1,
        "name": "Column Sorting Usage on Storage Container List",
        "description": (
            '"How often do users sort columns on the storage container list?"\n'
            "Shows which columns users sort by most frequently."
        ),
        "display": "row",
        "sql": f"""SELECT
  REGEXP_SUBSTR(ACTION_TYPE, '[^.]+$') AS SORTED_COLUMN,
  COUNT(*) AS TOTAL_SORTS
FROM {TABLE_NAME}
WHERE ACTION_TYPE LIKE 'sort\\_column.%'
  AND PAGE_SECTION = 'storage_container.eb'
  AND DESTINATION_NAME = 'storage_container/list'
GROUP BY 1
ORDER BY TOTAL_SORTS DESC
LIMIT 10""",
        "visualization_settings": {
            "graph.dimensions": ["SORTED_COLUMN"],
            "graph.metrics": ["TOTAL_SORTS"],
        },
    },
    {
        "number": 2,
        "name": "Row Link Clicks on Storage Container List",
        "description": (
            '"How often do users click row links (cluster names) in the storage container list?"\n'
            "Shows the volume of drill-through navigation from the list table."
        ),
        "display": "line",
        "sql": f"""SELECT
  DATE_TRUNC('week', TIMESTAMP) AS WEEK_START,
  COUNT(*) AS CLICK_COUNT
FROM {TABLE_NAME}
WHERE ACTION_TYPE = 'container_name.click'
  AND PAGE_SECTION = 'storage_container.eb'
  AND SUB_PAGE_SECTION = 'eb_list'
  AND DESTINATION_NAME = 'storage_container/list'
GROUP BY 1
ORDER BY WEEK_START""",
        "visualization_settings": {
            "graph.dimensions": ["WEEK_START"],
            "graph.metrics": ["CLICK_COUNT"],
        },
    },
    {
        "number": 3,
        "name": "Checkbox Selections on Storage Container List",
        "description": (
            '"How often do users select checkboxes on the storage container list?"\n'
            "Shows how frequently users signal intent to perform bulk actions."
        ),
        "display": "line",
        "sql": f"""SELECT
  DATE_TRUNC('week', TIMESTAMP) AS WEEK_START,
  COUNT(*) AS SELECT_COUNT
FROM {TABLE_NAME}
WHERE ACTION_TYPE = 'listview.select'
  AND PAGE_SECTION = 'storage_container.eb'
  AND SUB_PAGE_SECTION = 'eb_list'
  AND DESTINATION_NAME = 'storage_container/list'
GROUP BY 1
ORDER BY WEEK_START""",
        "visualization_settings": {
            "graph.dimensions": ["WEEK_START"],
            "graph.metrics": ["SELECT_COUNT"],
        },
    },
    {
        "number": 4,
        "name": "View-By Changes on Storage Container List",
        "description": (
            '"How often do users change column views on the storage container list?"\n'
            "Shows the frequency of view switching activity."
        ),
        "display": "line",
        "sql": f"""SELECT
  DATE_TRUNC('week', TIMESTAMP) AS WEEK_START,
  COUNT(*) AS VIEW_CHANGES
FROM {TABLE_NAME}
WHERE PAGE_SECTION = 'storage_container.eb'
  AND SUB_PAGE_SECTION = 'view_by_dropdown'
  AND DESTINATION_NAME ILIKE '%Storage Containers%'
GROUP BY 1
ORDER BY WEEK_START""",
        "visualization_settings": {
            "graph.dimensions": ["WEEK_START"],
            "graph.metrics": ["VIEW_CHANGES"],
        },
    },
    {
        "number": 5,
        "name": "Custom View Creations",
        "description": (
            '"Do users create custom views on the storage container list?"\n'
            "Shows whether custom view creation is happening and at what volume."
        ),
        "display": "smartscalar",
        "sql": f"""SELECT
  DATE_TRUNC('week', TIMESTAMP) AS WEEK_START,
  COUNT(*) AS CUSTOM_VIEW_COUNT
FROM {TABLE_NAME}
WHERE PAGE_SECTION = 'storage_container.eb'
  AND SUB_PAGE_SECTION = 'view_by_dropdown'
  AND ACTION_TYPE ILIKE '%custom%'
  AND DESTINATION_NAME ILIKE '%Storage Containers%'
GROUP BY 1
ORDER BY WEEK_START""",
        "visualization_settings": {
            "graph.dimensions": ["WEEK_START"],
            "graph.metrics": ["CUSTOM_VIEW_COUNT"],
        },
    },
]

LAYOUT_SIZING = {
    "row": (9, 5),
    "line": (9, 5),
    "bar": (9, 5),
    "smartscalar": (4, 3),
    "scalar": (4, 3),
}
GRID_COLS = 18


def create_card(widget: dict, cfg: dict) -> dict:
    payload = {
        "name": widget["name"],
        "description": widget["description"],
        "collection_id": cfg["default_collection_id"],
        "display": widget["display"],
        "visualization_settings": widget["visualization_settings"],
        "dataset_query": {
            "database": cfg["database_id"],
            "type": "native",
            "native": {
                "query": widget["sql"],
                "template-tags": {},
            },
        },
    }
    return request_with_retry("POST", "/api/card", body=payload)


def create_dashboard(cfg: dict) -> dict:
    payload = {
        "name": DASHBOARD_NAME,
        "description": DASHBOARD_DESCRIPTION,
        "collection_id": cfg["default_collection_id"],
        "parameters": [],
    }
    return request_with_retry("POST", "/api/dashboard", body=payload)


def compute_layout(cards: list[dict]) -> list[dict]:
    """Arrange cards on the 18-col grid."""
    dashcards = []
    col = 0
    row = 0
    row_height = 0

    for card in cards:
        display = card.get("display", "bar")
        size_x, size_y = LAYOUT_SIZING.get(display, (9, 5))

        if col + size_x > GRID_COLS:
            col = 0
            row += row_height
            row_height = 0

        dashcards.append({
            "id": -len(dashcards) - 1,
            "card_id": card["id"],
            "row": row,
            "col": col,
            "size_x": size_x,
            "size_y": size_y,
            "parameter_mappings": [],
        })

        col += size_x
        row_height = max(row_height, size_y)

    return dashcards


def main():
    cfg = get_config()
    print(f"→ Metabase: {cfg['base_url']}")
    print(f"→ Database ID: {cfg['database_id']}")
    print(f"→ Collection ID: {cfg['default_collection_id']}")
    print()

    created_cards = []
    for w in WIDGETS:
        print(f"  Creating card #{w['number']:02d}: {w['name']}...", end=" ")
        try:
            card = create_card(w, cfg)
            card["display"] = w["display"]
            created_cards.append(card)
            print(f"✓ id={card['id']}")
        except Exception as e:
            print(f"✗ {e}")
        time.sleep(0.3)

    if not created_cards:
        print("\n✗ No cards created. Aborting dashboard creation.")
        return 1

    print(f"\n→ Creating dashboard: {DASHBOARD_NAME}...", end=" ")
    try:
        dashboard = create_dashboard(cfg)
        print(f"✓ id={dashboard['id']}")
    except Exception as e:
        print(f"✗ {e}")
        print("\nCards were created but dashboard failed. Card URLs:")
        for c in created_cards:
            print(f"  - {cfg['base_url']}/question/{c['id']}")
        return 1

    dashcards = compute_layout(created_cards)
    print(f"→ Adding {len(dashcards)} cards to dashboard...", end=" ")
    try:
        result = request_with_retry(
            "PUT",
            f"/api/dashboard/{dashboard['id']}",
            body={"dashcards": dashcards},
        )
        print("✓")
    except Exception as e:
        print(f"✗ {e}")
        return 1

    dashboard_url = f"{cfg['base_url']}/dashboard/{dashboard['id']}"
    print("\n" + "=" * 60)
    print("  DONE")
    print("=" * 60)
    print(f"\n  Dashboard: {dashboard_url}")
    print(f"  Cards created: {len(created_cards)}")
    print()
    for c in created_cards:
        print(f"    - {c['name']}: {cfg['base_url']}/question/{c['id']}")
    print()

    summary = {
        "dashboard_id": dashboard["id"],
        "dashboard_url": dashboard_url,
        "dashboard_name": DASHBOARD_NAME,
        "cards": [
            {"id": c["id"], "name": c["name"], "url": f"{cfg['base_url']}/question/{c['id']}"}
            for c in created_cards
        ],
    }
    out_path = Path(__file__).parent.parent / "creation-results.json"
    out_path.write_text(json.dumps(summary, indent=2))
    print(f"  Results saved to: {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
