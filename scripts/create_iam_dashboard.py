#!/usr/bin/env python3
"""
Create the shashi-iam-automated-dashboard with 3 tabs:
  1. Roles (25 widgets)
  2. Policies (17 widgets)
  3. Identities (3 widgets)

Uses the Metabase REST API with credentials from .env.
All cards and the dashboard are created under the AI Generated Dashboard collection (id=26).
"""

import json
import os
import time
import urllib.request
import ssl
from pathlib import Path

# Load env
env_path = Path(__file__).resolve().parent.parent / "metabase-widget-skill" / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

BASE_URL = os.environ["METABASE_BASE_URL"].rstrip("/")
API_KEY = os.environ["METABASE_API_KEY"]
DB_ID = int(os.environ["METABASE_DATABASE_ID"])
TABLE = os.environ.get("METABASE_DEFAULT_TABLE_NAME", "NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT")
COLLECTION_ID = int(os.environ.get("METABASE_DEFAULT_COLLECTION_ID", "26"))

DASHBOARD_NAME = "shashi-iam-automated-dashboard"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def api(method, path, body=None):
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("X-API-Key", API_KEY)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        print(f"  ERROR {e.code}: {error_body[:500]}")
        raise


def create_card(name, description, display, sql, viz_settings=None, dashboard_id=None):
    """Create a native SQL card scoped to a dashboard and return its ID."""
    payload = {
        "name": name,
        "description": description,
        "display": display,
        "visualization_settings": viz_settings or {},
        "dataset_query": {
            "database": DB_ID,
            "type": "native",
            "native": {
                "query": sql,
                "template-tags": {}
            }
        }
    }
    if dashboard_id:
        payload["dashboard_id"] = dashboard_id
    else:
        payload["collection_id"] = COLLECTION_ID
    result = api("POST", "/api/card", payload)
    return result["id"]


# User-preferred sizes from SKILL.md — 2 charts per row (12+12=24)
SIZES = {
    "line": (12, 7),
    "bar": (12, 8),
    "row": (12, 7),
    "pie": (12, 8),
    "scalar": (8, 4),
    "smartscalar": (8, 4),
    "table": (24, 8),
    "funnel": (12, 7),
}
GRID_COLUMNS = 24


def get_size(display):
    return SIZES.get(display, (12, 7))


# ─────────────────────────────────────────────────────────────────────────────
# ROLES TAB WIDGETS (25 cards)
# ─────────────────────────────────────────────────────────────────────────────
roles_widgets = [
    {
        "name": "Role Page Visits over Time",
        "description": '"How often do users visit the Roles page?"\nShows the trend of navigation to the Roles page over time.',
        "display": "line",
        "sql": f"""SELECT DATE_TRUNC('month', TIMESTAMP) AS MONTH, COUNT(*) AS VISITS
FROM {TABLE}
WHERE DESTINATION_NAME = 'nav_item.roles'
  AND PAGE_SECTION = 'roles'
GROUP BY 1 ORDER BY 1""",
        "viz": {"graph.dimensions": ["MONTH"], "graph.metrics": ["VISITS"]}
    },
    {
        "name": "Role Creation over Time",
        "description": '"How often do users create roles?"\nShows the trend of role creation button clicks over time.',
        "display": "line",
        "sql": f"""SELECT DATE_TRUNC('month', TIMESTAMP) AS MONTH, COUNT(*) AS CREATIONS
FROM {TABLE}
WHERE DESTINATION_NAME = 'create_role.newRole'
  AND PAGE_SECTION = 'Roles'
  AND SUB_PAGE_SECTION = 'list_view'
GROUP BY 1 ORDER BY 1""",
        "viz": {"graph.dimensions": ["MONTH"], "graph.metrics": ["CREATIONS"]}
    },
    {
        "name": "Role Creation Funnel",
        "description": '"How often do users complete the role creation process versus dropping before saving?"\nShows the drop-off between starting and completing role creation.',
        "display": "funnel",
        "sql": f"""WITH labels AS (
  SELECT 1 AS STEP_ORDER, 'Start Role Creation' AS STEP_LABEL
  UNION ALL SELECT 2, 'Save Role'
  UNION ALL SELECT 3, 'Exit Without Saving'
),
start_events AS (SELECT COUNT(*) AS CNT FROM {TABLE} WHERE DESTINATION_NAME = 'create_role.newRole' AND PAGE_SECTION = 'Roles'),
save_events AS (SELECT COUNT(*) AS CNT FROM {TABLE} WHERE DESTINATION_NAME = 'Save Role' AND PAGE_SECTION = 'form.create_role'),
exit_events AS (SELECT COUNT(*) AS CNT FROM {TABLE} WHERE DESTINATION_NAME = 'Exit Role Creation' AND PAGE_SECTION = 'form.create_role')
SELECT l.STEP_LABEL, CASE l.STEP_ORDER WHEN 1 THEN (SELECT CNT FROM start_events) WHEN 2 THEN (SELECT CNT FROM save_events) WHEN 3 THEN (SELECT CNT FROM exit_events) END AS TOTAL_EVENTS
FROM labels l ORDER BY l.STEP_ORDER""",
        "viz": {}
    },
    {
        "name": "System-Defined Roles Usage",
        "description": '"Which system-defined roles are being used?"\nShows which pre-built roles users select most when creating policies.',
        "display": "row",
        "sql": f"""SELECT SPLIT_PART(DESTINATION_NAME, ':', 2) AS ROLE_NAME, COUNT(*) AS USAGE_COUNT
FROM {TABLE}
WHERE DESTINATION_NAME LIKE 'change_role.system_defined:%'
  AND PAGE_SECTION = 'form.create_authorization_policy'
  AND SUB_PAGE_SECTION = 'choose_role'
GROUP BY 1 ORDER BY USAGE_COUNT DESC LIMIT 15""",
        "viz": {"graph.dimensions": ["ROLE_NAME"], "graph.metrics": ["USAGE_COUNT"]}
    },
    {
        "name": "Most Cloned Roles",
        "description": '"Which roles do users clone the most?"\nShows which existing roles users pick as templates for new roles.',
        "display": "row",
        "sql": f"""SELECT SPLIT_PART(DESTINATION_NAME, ':', 2) AS CLONED_ROLE, COUNT(*) AS CLONE_COUNT
FROM {TABLE}
WHERE DESTINATION_NAME LIKE 'select_role:%'
  AND PAGE_SECTION = 'form.create_from_existing_role'
GROUP BY 1 ORDER BY CLONE_COUNT DESC LIMIT 15""",
        "viz": {"graph.dimensions": ["CLONED_ROLE"], "graph.metrics": ["CLONE_COUNT"]}
    },
    {
        "name": "Custom Roles Created over Time",
        "description": '"How many custom roles do people create?"\nShows the trend of custom role creation completions over time.',
        "display": "line",
        "sql": f"""SELECT DATE_TRUNC('month', TIMESTAMP) AS MONTH, COUNT(*) AS ROLES_CREATED
FROM {TABLE}
WHERE DESTINATION_NAME = 'Save Role'
  AND PAGE_SECTION = 'form.create_role'
GROUP BY 1 ORDER BY 1""",
        "viz": {"graph.dimensions": ["MONTH"], "graph.metrics": ["ROLES_CREATED"]}
    },
    {
        "name": "Most Common Role List Actions",
        "description": '"What actions do users take most commonly on the Role list?"\nShows which actions users perform most on the roles list page.',
        "display": "bar",
        "sql": f"""SELECT DESTINATION_NAME AS ACTION_NAME, COUNT(*) AS ACTION_COUNT
FROM {TABLE}
WHERE PAGE_SECTION = 'Roles'
  AND SUB_PAGE_SECTION IN ('actions_dropdown', 'list_view')
  AND ACTION_TYPE = 'click'
GROUP BY 1 ORDER BY ACTION_COUNT DESC""",
        "viz": {"graph.dimensions": ["ACTION_NAME"], "graph.metrics": ["ACTION_COUNT"]}
    },
    {
        "name": "Role Creation — Average Time Spent over Time",
        "description": '"How long do people spend on role creation?"\nShows the trend of average creation duration month by month.',
        "display": "line",
        "sql": f"""WITH start_events AS (
  SELECT SESSION_ID, TIMESTAMP AS START_TIME
  FROM {TABLE}
  WHERE DESTINATION_NAME = 'create_role.newRole' AND PAGE_SECTION = 'Roles'
),
end_events AS (
  SELECT SESSION_ID, TIMESTAMP AS END_TIME
  FROM {TABLE}
  WHERE DESTINATION_NAME IN ('Save Role', 'Exit Role Creation') AND PAGE_SECTION = 'form.create_role'
),
paired AS (
  SELECT s.SESSION_ID, s.START_TIME, TIMESTAMPDIFF('second', s.START_TIME, e.END_TIME) AS DURATION_SECONDS,
         ROW_NUMBER() OVER (PARTITION BY s.SESSION_ID ORDER BY e.END_TIME ASC) AS RN
  FROM start_events s JOIN end_events e ON s.SESSION_ID = e.SESSION_ID AND e.END_TIME > s.START_TIME
)
SELECT DATE_TRUNC('month', START_TIME) AS MONTH, ROUND(AVG(DURATION_SECONDS)/60,1) AS AVG_MINUTES
FROM paired WHERE RN = 1 AND DURATION_SECONDS > 0 AND DURATION_SECONDS < 3600
GROUP BY MONTH ORDER BY MONTH""",
        "viz": {"graph.dimensions": ["MONTH"], "graph.metrics": ["AVG_MINUTES"]}
    },
    {
        "name": "Individual vs Group Operation Adds over Time",
        "description": '"Do people add individual operations or all operations for entities?"\nShows the comparison between individual and group adds month by month.',
        "display": "bar",
        "sql": f"""SELECT DATE_TRUNC('month', TIMESTAMP) AS MONTH,
  CASE WHEN DESTINATION_NAME = 'add_operation' THEN 'Individual Operations'
       ELSE 'All Operations (Group)' END AS OPERATION_TYPE,
  COUNT(*) AS TOTAL_CLICKS
FROM {TABLE}
WHERE DESTINATION_NAME IN ('add_operation', 'add_operation_group')
  AND PAGE_SECTION = 'form.create_role'
  AND SUB_PAGE_SECTION = 'select_operations'
GROUP BY MONTH, OPERATION_TYPE ORDER BY MONTH""",
        "viz": {"graph.dimensions": ["MONTH"], "graph.metrics": ["TOTAL_CLICKS"], "series_settings": {}}
    },
    {
        "name": "Role Description Usage over Time",
        "description": '"How often do users add a description when creating roles?"\nShows the trend of description field usage during role creation.',
        "display": "line",
        "sql": f"""SELECT DATE_TRUNC('month', TIMESTAMP) AS MONTH, COUNT(*) AS DESCRIPTION_ADDS
FROM {TABLE}
WHERE DESTINATION_NAME = 'Role Description'
  AND ACTION_TYPE = 'change'
  AND PAGE_SECTION = 'form.create_role'
GROUP BY 1 ORDER BY 1""",
        "viz": {"graph.dimensions": ["MONTH"], "graph.metrics": ["DESCRIPTION_ADDS"]}
    },
    {
        "name": "Most Added Operations in Custom Roles",
        "description": '"Which entity types and operations are added most frequently in custom roles?"\nShows the top operations users add to custom roles.',
        "display": "row",
        "sql": f"""SELECT
  CASE
    WHEN DESTINATION_NAME LIKE 'add_operation_group:%'
      THEN INITCAP(REPLACE(SPLIT_PART(DESTINATION_NAME, ':', 2), '_', ' ')) || ' (Group)'
    ELSE INITCAP(REPLACE(SPLIT_PART(DESTINATION_NAME, ':', 2), '_', ' '))
  END AS OPERATION_NAME,
  COUNT(*) AS TOTAL_ADDS
FROM {TABLE}
WHERE DESTINATION_NAME LIKE 'add_operation%'
  AND DESTINATION_NAME LIKE '%:%'
  AND PAGE_SECTION = 'form.create_role'
  AND SUB_PAGE_SECTION = 'select_operations'
GROUP BY 1 ORDER BY TOTAL_ADDS DESC LIMIT 20""",
        "viz": {"graph.dimensions": ["OPERATION_NAME"], "graph.metrics": ["TOTAL_ADDS"]}
    },
    {
        "name": "Operation Removals during Role Creation over Time",
        "description": '"How often do users remove operations during role create?"\nShows the frequency trend of operation removal actions.',
        "display": "line",
        "sql": f"""SELECT DATE_TRUNC('month', TIMESTAMP) AS MONTH, COUNT(*) AS REMOVALS
FROM {TABLE}
WHERE DESTINATION_NAME LIKE 'remove_operation:%'
  AND PAGE_SECTION = 'form.create_role'
GROUP BY 1 ORDER BY 1""",
        "viz": {"graph.dimensions": ["MONTH"], "graph.metrics": ["REMOVALS"]}
    },
    {
        "name": "Most Removed Operations during Role Creation",
        "description": '"Which operations do users remove during role create?"\nShows which specific operations are removed most frequently.',
        "display": "row",
        "sql": f"""SELECT INITCAP(REPLACE(SPLIT_PART(DESTINATION_NAME, ':', 2), '_', ' ')) AS REMOVED_OPERATION, COUNT(*) AS REMOVAL_COUNT
FROM {TABLE}
WHERE DESTINATION_NAME LIKE 'remove_operation:%'
  AND PAGE_SECTION = 'form.create_role'
GROUP BY 1 ORDER BY REMOVAL_COUNT DESC LIMIT 15""",
        "viz": {"graph.dimensions": ["REMOVED_OPERATION"], "graph.metrics": ["REMOVAL_COUNT"]}
    },
    {
        "name": "Role Save vs Save & Create Policy over Time",
        "description": '"How often do users save their roles versus save and go to policy creation?"\nShows the comparison between the two completion paths month by month.',
        "display": "bar",
        "sql": f"""SELECT DATE_TRUNC('month', TIMESTAMP) AS MONTH,
  CASE WHEN DESTINATION_NAME = 'save_role' THEN 'Save Role'
       ELSE 'Save & Create Policy' END AS ACTION_LABEL,
  COUNT(*) AS TOTAL_CLICKS
FROM {TABLE}
WHERE DESTINATION_NAME IN ('save_role', 'save_role_create_policy')
  AND PAGE_SECTION = 'form.create_role'
  AND SUB_PAGE_SECTION = 'footer'
GROUP BY MONTH, ACTION_LABEL ORDER BY MONTH""",
        "viz": {"graph.dimensions": ["MONTH"], "graph.metrics": ["TOTAL_CLICKS"], "series_settings": {}}
    },
    {
        "name": "Related Operations Icon Clicks over Time",
        "description": '"How often do people click on the related operations icon?"\nShows the trend of users exploring related operations during role creation.',
        "display": "line",
        "sql": f"""SELECT DATE_TRUNC('month', TIMESTAMP) AS MONTH, COUNT(*) AS CLICKS
FROM {TABLE}
WHERE DESTINATION_NAME LIKE 'view_related_operations:%'
  AND PAGE_SECTION = 'form.create_role'
  AND SUB_PAGE_SECTION = 'select_operations'
GROUP BY 1 ORDER BY 1""",
        "viz": {"graph.dimensions": ["MONTH"], "graph.metrics": ["CLICKS"]}
    },
    {
        "name": "Operations with Related Ops Added over Time",
        "description": '"How often do users add operations that have related operations?"\nShows the trend of adding operations flagged with related dependencies.',
        "display": "line",
        "sql": f"""SELECT DATE_TRUNC('month', TIMESTAMP) AS MONTH, COUNT(*) AS ADDS
FROM {TABLE}
WHERE DESTINATION_NAME LIKE 'add_operation.with_related_operations:%'
  AND PAGE_SECTION = 'form.create_role'
  AND SUB_PAGE_SECTION = 'select_operations'
GROUP BY 1 ORDER BY 1""",
        "viz": {"graph.dimensions": ["MONTH"], "graph.metrics": ["ADDS"]}
    },
    {
        "name": "Operations with All Related Ops Removed",
        "description": '"For which common operations do users remove related operations?"\nShows which operations most commonly trigger bulk removal of related ops.',
        "display": "row",
        "sql": f"""SELECT INITCAP(REPLACE(SPLIT_PART(DESTINATION_NAME, '.', 2), '_', ' ')) AS OPERATION_NAME, COUNT(*) AS REMOVAL_COUNT
FROM {TABLE}
WHERE DESTINATION_NAME LIKE 'remove_all_related_operation.%'
  AND PAGE_SECTION = 'form.create_role'
  AND SUB_PAGE_SECTION = 'role_related_operations'
GROUP BY 1 ORDER BY REMOVAL_COUNT DESC LIMIT 15""",
        "viz": {"graph.dimensions": ["OPERATION_NAME"], "graph.metrics": ["REMOVAL_COUNT"]}
    },
    {
        "name": "Save Despite Missing Operations Warning over Time",
        "description": '"How often do users ignore the warning about related operations missing before they save the role?"\nShows the trend of users overriding the missing-ops safety warning.',
        "display": "line",
        "sql": f"""SELECT DATE_TRUNC('month', TIMESTAMP) AS MONTH, COUNT(*) AS WARNING_OVERRIDES
FROM {TABLE}
WHERE DESTINATION_NAME = 'save_role_with_missing_operations'
  AND PAGE_SECTION = 'form.create_role'
GROUP BY 1 ORDER BY 1""",
        "viz": {"graph.dimensions": ["MONTH"], "graph.metrics": ["WARNING_OVERRIDES"]}
    },
    {
        "name": "Operation Removals during Role Update over Time",
        "description": '"How often do users remove operations from the right-hand side during role update?"\nShows the frequency of operation removal during role editing.',
        "display": "line",
        "sql": f"""SELECT DATE_TRUNC('month', TIMESTAMP) AS MONTH, COUNT(*) AS REMOVALS
FROM {TABLE}
WHERE DESTINATION_NAME LIKE 'remove_operation:%'
  AND FEATNAME = 'Role'
  AND PAGE_SECTION = 'form.create_role'
GROUP BY 1 ORDER BY 1""",
        "viz": {"graph.dimensions": ["MONTH"], "graph.metrics": ["REMOVALS"]}
    },
    {
        "name": "Role Updates over Time",
        "description": '"How often do users update roles?"\nShows the trend of role update actions over time.',
        "display": "line",
        "sql": f"""SELECT DATE_TRUNC('month', TIMESTAMP) AS MONTH, COUNT(*) AS UPDATES
FROM {TABLE}
WHERE DESTINATION_NAME = 'update_role'
  AND PAGE_SECTION = 'Roles'
  AND SUB_PAGE_SECTION = 'actions_dropdown'
GROUP BY 1 ORDER BY 1""",
        "viz": {"graph.dimensions": ["MONTH"], "graph.metrics": ["UPDATES"]}
    },
    {
        "name": "Show Changes Toggle Usage over Time",
        "description": '"How often do users use the show changes feature?"\nShows how frequently users toggle the change-diff view during role updates.',
        "display": "line",
        "sql": f"""SELECT DATE_TRUNC('month', TIMESTAMP) AS MONTH, COUNT(*) AS TOGGLES
FROM {TABLE}
WHERE DESTINATION_NAME LIKE 'toggle_show_changes:%'
  AND PAGE_SECTION = 'form.update_role'
GROUP BY 1 ORDER BY 1""",
        "viz": {"graph.dimensions": ["MONTH"], "graph.metrics": ["TOGGLES"]}
    },
    {
        "name": "Role Update Entry Points over Time",
        "description": '"From where do users enter the role update workflow?"\nShows whether users start updates from the details page or list dropdown, month by month.',
        "display": "bar",
        "sql": f"""SELECT DATE_TRUNC('month', TIMESTAMP) AS MONTH, PAGE_SECTION AS ENTRY_POINT, COUNT(*) AS TOTAL_CLICKS
FROM {TABLE}
WHERE DESTINATION_NAME IN ('update', 'update_role')
  AND FEATNAME = 'Role'
  AND ACTION_TYPE = 'click'
GROUP BY MONTH, ENTRY_POINT ORDER BY MONTH""",
        "viz": {"graph.dimensions": ["MONTH"], "graph.metrics": ["TOTAL_CLICKS"], "series_settings": {}}
    },
    {
        "name": "Role Deletions over Time",
        "description": '"How often do users delete roles?"\nShows the trend of role deletion actions.',
        "display": "line",
        "sql": f"""SELECT DATE_TRUNC('month', TIMESTAMP) AS MONTH, COUNT(*) AS DELETIONS
FROM {TABLE}
WHERE DESTINATION_NAME IN ('delete_role', 'delete')
  AND FEATNAME = 'Role'
  AND ACTION_TYPE = 'click'
GROUP BY 1 ORDER BY 1""",
        "viz": {"graph.dimensions": ["MONTH"], "graph.metrics": ["DELETIONS"]}
    },
    {
        "name": "Role Delete Entry Points over Time",
        "description": '"From where do users enter the role delete workflow?"\nShows whether users delete from the list or details page, month by month.',
        "display": "bar",
        "sql": f"""SELECT DATE_TRUNC('month', TIMESTAMP) AS MONTH, PAGE_SECTION AS ENTRY_POINT, COUNT(*) AS TOTAL_CLICKS
FROM {TABLE}
WHERE DESTINATION_NAME IN ('delete_role', 'delete')
  AND FEATNAME = 'Role'
  AND ACTION_TYPE = 'click'
GROUP BY MONTH, ENTRY_POINT ORDER BY MONTH""",
        "viz": {"graph.dimensions": ["MONTH"], "graph.metrics": ["TOTAL_CLICKS"], "series_settings": {}}
    },
    {
        "name": "Most Common Role Details Actions",
        "description": '"What actions do users take most commonly on the Role Details page?"\nShows which header actions users take most.',
        "display": "bar",
        "sql": f"""SELECT DESTINATION_NAME AS ACTION_NAME, COUNT(*) AS ACTION_COUNT
FROM {TABLE}
WHERE PAGE_SECTION = 'Role Details'
  AND SUB_PAGE_SECTION = 'header_actions'
  AND FEATNAME = 'Role'
  AND ACTION_TYPE = 'click'
GROUP BY 1 ORDER BY ACTION_COUNT DESC""",
        "viz": {"graph.dimensions": ["ACTION_NAME"], "graph.metrics": ["ACTION_COUNT"]}
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# POLICIES TAB WIDGETS (17 cards)
# ─────────────────────────────────────────────────────────────────────────────
policies_widgets = [
    {
        "name": "Policy Deletions over Time",
        "description": '"How often do users delete policies?"\nShows the trend of authorization policy deletion actions.',
        "display": "line",
        "sql": f"""SELECT DATE_TRUNC('month', TIMESTAMP) AS MONTH, COUNT(*) AS DELETIONS
FROM {TABLE}
WHERE DESTINATION_NAME LIKE 'delete:%'
  AND FEATNAME = 'Authorization Policy'
  AND PAGE_SECTION = 'Authorization Policies'
  AND SUB_PAGE_SECTION = 'actions_dropdown'
GROUP BY 1 ORDER BY 1""",
        "viz": {"graph.dimensions": ["MONTH"], "graph.metrics": ["DELETIONS"]}
    },
    {
        "name": "Policy Delete Entry Points over Time",
        "description": '"From where do users enter the policy delete workflow?"\nShows whether users delete from the list or details page, month by month.',
        "display": "bar",
        "sql": f"""SELECT DATE_TRUNC('month', TIMESTAMP) AS MONTH, PAGE_SECTION AS ENTRY_POINT, COUNT(*) AS TOTAL_CLICKS
FROM {TABLE}
WHERE (DESTINATION_NAME LIKE 'delete:%' OR DESTINATION_NAME = 'delete')
  AND FEATNAME = 'Authorization Policy'
  AND ACTION_TYPE = 'click'
GROUP BY MONTH, ENTRY_POINT ORDER BY MONTH""",
        "viz": {"graph.dimensions": ["MONTH"], "graph.metrics": ["TOTAL_CLICKS"], "series_settings": {}}
    },
    {
        "name": "Policy Creation Entry Points over Time",
        "description": '"From where do users enter the policy creation workflow?"\nShows whether users create policies from the list or role flow, month by month.',
        "display": "bar",
        "sql": f"""SELECT DATE_TRUNC('month', TIMESTAMP) AS MONTH,
  CASE WHEN DESTINATION_NAME = 'Create Authorization Policy' THEN 'Policy List'
       ELSE 'Role Creation Flow' END AS ENTRY_POINT,
  COUNT(*) AS TOTAL_CLICKS
FROM {TABLE}
WHERE DESTINATION_NAME IN ('Create Authorization Policy', 'save_role_create_policy')
  AND ACTION_TYPE = 'click'
GROUP BY MONTH, ENTRY_POINT ORDER BY MONTH""",
        "viz": {"graph.dimensions": ["MONTH"], "graph.metrics": ["TOTAL_CLICKS"], "series_settings": {}}
    },
    {
        "name": "Policy Creation over Time",
        "description": '"How often do users create new authorization policies?"\nShows the trend of new policy creation events.',
        "display": "line",
        "sql": f"""SELECT DATE_TRUNC('month', TIMESTAMP) AS MONTH, COUNT(*) AS CREATIONS
FROM {TABLE}
WHERE DESTINATION_NAME IN ('create_policy', 'save_role_create_policy')
  AND ACTION_TYPE = 'click'
GROUP BY 1 ORDER BY 1""",
        "viz": {"graph.dimensions": ["MONTH"], "graph.metrics": ["CREATIONS"]}
    },
    {
        "name": "System-Defined Roles Used in Policies",
        "description": '"Which system-defined roles do users utilize the most in policies?"\nShows which pre-built roles users select when creating authorization policies.',
        "display": "row",
        "sql": f"""SELECT SPLIT_PART(DESTINATION_NAME, ':', 2) AS ROLE_NAME, COUNT(*) AS USAGE_COUNT
FROM {TABLE}
WHERE DESTINATION_NAME LIKE 'change_role.system_defined:%'
  AND FEATNAME = 'Authorization Policy'
  AND PAGE_SECTION = 'form.create_authorization_policy'
  AND SUB_PAGE_SECTION = 'choose_role'
GROUP BY 1 ORDER BY USAGE_COUNT DESC LIMIT 15""",
        "viz": {"graph.dimensions": ["ROLE_NAME"], "graph.metrics": ["USAGE_COUNT"]}
    },
    {
        "name": "Full Access vs Configured Access over Time",
        "description": '"Do users typically create configured access or full access policies?"\nShows the comparison between the two access modes month by month.',
        "display": "bar",
        "sql": f"""SELECT DATE_TRUNC('month', TIMESTAMP) AS MONTH,
  CASE WHEN DESTINATION_NAME = 'select_entity_type:fullAccess' THEN 'Full Access'
       ELSE 'Configured Access' END AS ACCESS_TYPE,
  COUNT(*) AS TOTAL_CLICKS
FROM {TABLE}
WHERE DESTINATION_NAME IN ('select_entity_type:fullAccess', 'select_entity_type:configureAccess')
  AND FEATNAME = 'Authorization Policy'
  AND PAGE_SECTION = 'form.edit_authorization_policy'
GROUP BY MONTH, ACCESS_TYPE ORDER BY MONTH""",
        "viz": {"graph.dimensions": ["MONTH"], "graph.metrics": ["TOTAL_CLICKS"], "series_settings": {}}
    },
    {
        "name": "Policy Creation — Average Time Spent over Time",
        "description": '"How long does it take users to create policies?"\nShows the trend of average creation duration month by month.',
        "display": "line",
        "sql": f"""WITH form_open AS (
  SELECT SESSION_ID, TIMESTAMP AS OPEN_TIME
  FROM {TABLE}
  WHERE DESTINATION_NAME IN ('create_policy', 'Create Authorization Policy', 'save_role_create_policy')
    AND FEATNAME = 'Authorization Policy'
),
form_save AS (
  SELECT SESSION_ID, TIMESTAMP AS SAVE_TIME
  FROM {TABLE}
  WHERE DESTINATION_NAME = 'save_policy'
    AND PAGE_SECTION = 'form.edit_authorization_policy'
),
paired AS (
  SELECT o.SESSION_ID, o.OPEN_TIME, TIMESTAMPDIFF('second', o.OPEN_TIME, s.SAVE_TIME) AS DURATION_SECONDS,
         ROW_NUMBER() OVER (PARTITION BY o.SESSION_ID ORDER BY s.SAVE_TIME ASC) AS RN
  FROM form_open o JOIN form_save s ON o.SESSION_ID = s.SESSION_ID AND s.SAVE_TIME > o.OPEN_TIME
)
SELECT DATE_TRUNC('month', OPEN_TIME) AS MONTH, ROUND(AVG(DURATION_SECONDS)/60,1) AS AVG_MINUTES
FROM paired WHERE RN = 1 AND DURATION_SECONDS > 0 AND DURATION_SECONDS < 3600
GROUP BY MONTH ORDER BY MONTH""",
        "viz": {"graph.dimensions": ["MONTH"], "graph.metrics": ["AVG_MINUTES"]}
    },
    {
        "name": "Future Access Checkbox Usage over Time",
        "description": '"How often do users check the future access box?"\nShows the trend of users enabling future access during policy creation/edit.',
        "display": "line",
        "sql": f"""SELECT DATE_TRUNC('month', TIMESTAMP) AS MONTH, COUNT(*) AS CHECKS
FROM {TABLE}
WHERE DESTINATION_NAME = 'change_future_access:true'
  AND FEATNAME = 'Authorization Policy'
  AND PAGE_SECTION = 'form.edit_authorization_policy'
GROUP BY 1 ORDER BY 1""",
        "viz": {"graph.dimensions": ["MONTH"], "graph.metrics": ["CHECKS"]}
    },
    {
        "name": "Automatic Access Unchecked over Time",
        "description": '"How often do users uncheck the automatic access box?"\nShows the trend of users disabling automatic access.',
        "display": "line",
        "sql": f"""SELECT DATE_TRUNC('month', TIMESTAMP) AS MONTH, COUNT(*) AS UNCHECKS
FROM {TABLE}
WHERE DESTINATION_NAME = 'change_automatic_access:false'
  AND FEATNAME = 'Authorization Policy'
  AND PAGE_SECTION = 'form.edit_authorization_policy'
GROUP BY 1 ORDER BY 1""",
        "viz": {"graph.dimensions": ["MONTH"], "graph.metrics": ["UNCHECKS"]}
    },
    {
        "name": "All Entity Types Selection over Time",
        "description": '"How often do users select All Entity Types in the entity selector?"\nShows adoption of the blanket all-entity-types option.',
        "display": "line",
        "sql": f"""SELECT DATE_TRUNC('month', TIMESTAMP) AS MONTH, COUNT(*) AS SELECTIONS
FROM {TABLE}
WHERE DESTINATION_NAME = 'entity_type:All Entity Types'
  AND ACTION_TYPE = 'change'
  AND FEATNAME = 'Authorization Policy'
  AND PAGE_SECTION = 'form.create_authorization_policy'
GROUP BY 1 ORDER BY 1""",
        "viz": {"graph.dimensions": ["MONTH"], "graph.metrics": ["SELECTIONS"]}
    },
    {
        "name": "Advanced Filter Usage over Time",
        "description": '"How often do users use the advanced filter?"\nShows the trend of users switching to advanced filter mode.',
        "display": "line",
        "sql": f"""SELECT DATE_TRUNC('month', TIMESTAMP) AS MONTH, COUNT(*) AS USES
FROM {TABLE}
WHERE DESTINATION_NAME = 'scope_filter:advanced'
  AND ACTION_TYPE = 'change'
  AND FEATNAME = 'Authorization Policy'
  AND PAGE_SECTION = 'form.create_authorization_policy'
GROUP BY 1 ORDER BY 1""",
        "viz": {"graph.dimensions": ["MONTH"], "graph.metrics": ["USES"]}
    },
    {
        "name": "Advanced Filter Conditions per Session",
        "description": '"How many conditions do users add when creating an advanced filter?"\nShows the distribution of condition counts per session.',
        "display": "bar",
        "sql": f"""WITH condition_counts AS (
  SELECT SESSION_ID, COUNT(*) AS NUM_CONDITIONS
  FROM {TABLE}
  WHERE DESTINATION_NAME = 'add_condition'
    AND FEATNAME = 'Authorization Policy'
    AND PAGE_SECTION = 'form.create_authorization_policy'
    AND SUB_PAGE_SECTION = 'advanced_filter'
  GROUP BY SESSION_ID
)
SELECT NUM_CONDITIONS AS CONDITIONS_ADDED, COUNT(*) AS SESSIONS
FROM condition_counts GROUP BY NUM_CONDITIONS ORDER BY NUM_CONDITIONS""",
        "viz": {"graph.dimensions": ["CONDITIONS_ADDED"], "graph.metrics": ["SESSIONS"]}
    },
    {
        "name": "Policy Creation — Time per Step over Time",
        "description": '"How much time do users spend on each step of the policy creation workflow?"\nShows the average time per step month by month.',
        "display": "bar",
        "sql": f"""WITH step_events AS (
  SELECT SESSION_ID, SUB_PAGE_SECTION AS STEP_NAME, TIMESTAMP AS STEP_TIME,
         LEAD(TIMESTAMP) OVER (PARTITION BY SESSION_ID ORDER BY TIMESTAMP) AS NEXT_STEP_TIME
  FROM {TABLE}
  WHERE DESTINATION_NAME = 'next'
    AND FEATNAME = 'Authorization Policy'
    AND PAGE_SECTION = 'form.create_authorization_policy'
    AND SUB_PAGE_SECTION LIKE 'step_%'
),
step_durations AS (
  SELECT SESSION_ID, STEP_NAME, STEP_TIME, TIMESTAMPDIFF('second', STEP_TIME, NEXT_STEP_TIME) AS DURATION_SECONDS
  FROM step_events
  WHERE NEXT_STEP_TIME IS NOT NULL AND TIMESTAMPDIFF('second', STEP_TIME, NEXT_STEP_TIME) BETWEEN 1 AND 1800
)
SELECT DATE_TRUNC('month', STEP_TIME) AS MONTH,
       INITCAP(REPLACE(STEP_NAME, '_', ' ')) AS STEP_LABEL,
       ROUND(AVG(DURATION_SECONDS)/60,1) AS AVG_MINUTES
FROM step_durations GROUP BY MONTH, STEP_NAME ORDER BY MONTH, STEP_NAME""",
        "viz": {"graph.dimensions": ["MONTH"], "graph.metrics": ["AVG_MINUTES"], "series_settings": {}}
    },
    {
        "name": "View Entity Types Clicks over Time",
        "description": '"How often do users click View Entity Types on the 2nd step?"\nShows adoption of the entity-types drill-down feature.',
        "display": "line",
        "sql": f"""SELECT DATE_TRUNC('month', TIMESTAMP) AS MONTH, COUNT(*) AS CLICKS
FROM {TABLE}
WHERE DESTINATION_NAME = 'view_entity_types'
  AND FEATNAME = 'Authorization Policy'
  AND PAGE_SECTION = 'form.create_authorization_policy'
GROUP BY 1 ORDER BY 1""",
        "viz": {"graph.dimensions": ["MONTH"], "graph.metrics": ["CLICKS"]}
    },
    {
        "name": "Policy Details Page — Average Time Spent over Time",
        "description": '"How much time do users spend on the policy details page?"\nShows the trend of average time on the details page month by month.',
        "display": "line",
        "sql": f"""WITH open_events AS (
  SELECT SESSION_ID, TIMESTAMP AS OPEN_TIME
  FROM {TABLE}
  WHERE DESTINATION_NAME = 'view_policy_details' AND FEATNAME = 'Authorization Policy' AND PAGE_SECTION = 'Authorization Policies'
),
close_events AS (
  SELECT SESSION_ID, TIMESTAMP AS CLOSE_TIME
  FROM {TABLE}
  WHERE DESTINATION_NAME = 'close_policy' AND FEATNAME = 'Authorization Policy'
),
paired AS (
  SELECT o.SESSION_ID, o.OPEN_TIME, TIMESTAMPDIFF('second', o.OPEN_TIME, c.CLOSE_TIME) AS DURATION_SECONDS,
         ROW_NUMBER() OVER (PARTITION BY o.SESSION_ID, o.OPEN_TIME ORDER BY c.CLOSE_TIME ASC) AS RN
  FROM open_events o JOIN close_events c ON o.SESSION_ID = c.SESSION_ID AND c.CLOSE_TIME > o.OPEN_TIME
)
SELECT DATE_TRUNC('month', OPEN_TIME) AS MONTH, ROUND(AVG(DURATION_SECONDS)/60,1) AS AVG_MINUTES
FROM paired WHERE RN = 1 AND DURATION_SECONDS > 0 AND DURATION_SECONDS < 1800
GROUP BY MONTH ORDER BY MONTH""",
        "viz": {"graph.dimensions": ["MONTH"], "graph.metrics": ["AVG_MINUTES"]}
    },
    {
        "name": "Most Common Policy Details Actions",
        "description": '"Which are the most commonly taken actions from the policy details page?"\nShows which header actions users take most on policy details.',
        "display": "bar",
        "sql": f"""SELECT DESTINATION_NAME AS ACTION_NAME, COUNT(*) AS ACTION_COUNT
FROM {TABLE}
WHERE PAGE_SECTION = 'Authorization Policy Details'
  AND SUB_PAGE_SECTION = 'header_actions'
  AND FEATNAME = 'Authorization Policy'
  AND ACTION_TYPE = 'click'
GROUP BY 1 ORDER BY ACTION_COUNT DESC""",
        "viz": {"graph.dimensions": ["ACTION_NAME"], "graph.metrics": ["ACTION_COUNT"]}
    },
    {
        "name": "Role Changes during Policy Update over Time",
        "description": '"When users update policies, how often do they change the role?"\nShows the frequency of role-change actions during policy editing.',
        "display": "line",
        "sql": f"""SELECT DATE_TRUNC('month', TIMESTAMP) AS MONTH, COUNT(*) AS ROLE_CHANGES
FROM {TABLE}
WHERE DESTINATION_NAME LIKE 'change_role%'
  AND FEATNAME = 'Authorization Policy'
  AND PAGE_SECTION = 'form.edit_authorization_policy'
  AND SUB_PAGE_SECTION = 'choose_role'
GROUP BY 1 ORDER BY 1""",
        "viz": {"graph.dimensions": ["MONTH"], "graph.metrics": ["ROLE_CHANGES"]}
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# IDENTITIES TAB WIDGETS (3 cards)
# ─────────────────────────────────────────────────────────────────────────────
identities_widgets = [
    {
        "name": "Local Users Added over Time",
        "description": '"How many local users do customers add?"\nShows the trend of local user creation actions over time.',
        "display": "line",
        "sql": f"""SELECT DATE_TRUNC('month', TIMESTAMP) AS MONTH, COUNT(*) AS LOCAL_USERS_ADDED
FROM {TABLE}
WHERE DESTINATION_NAME = 'add_local_user'
  AND FEATNAME = 'Identity'
  AND PAGE_SECTION = 'Identities'
  AND SUB_PAGE_SECTION = 'list_view'
GROUP BY 1 ORDER BY 1""",
        "viz": {"graph.dimensions": ["MONTH"], "graph.metrics": ["LOCAL_USERS_ADDED"]}
    },
    {
        "name": "Identities Page — Time per Tab over Time",
        "description": '"How much time do users spend in each of the tabs in the Identities page?"\nShows the average time per tab month by month.',
        "display": "bar",
        "sql": f"""WITH tab_events AS (
  SELECT SESSION_ID, DESTINATION_NAME AS TAB_NAME, TIMESTAMP AS TAB_TIME,
         LEAD(TIMESTAMP) OVER (PARTITION BY SESSION_ID ORDER BY TIMESTAMP) AS NEXT_EVENT_TIME
  FROM {TABLE}
  WHERE (
    (DESTINATION_NAME LIKE 'switch_tab:%' AND FEATNAME = 'Identity' AND PAGE_SECTION = 'Identities')
    OR (DESTINATION_NAME = 'nav_item.roles' AND PAGE_SECTION = 'roles')
  )
),
tab_durations AS (
  SELECT SESSION_ID, TAB_TIME,
    CASE WHEN TAB_NAME = 'nav_item.roles' THEN 'Roles Tab'
         ELSE INITCAP(REPLACE(SPLIT_PART(TAB_NAME, ':', 2), '_', ' '))
    END AS TAB_LABEL,
    TIMESTAMPDIFF('second', TAB_TIME, NEXT_EVENT_TIME) AS DURATION_SECONDS
  FROM tab_events
  WHERE NEXT_EVENT_TIME IS NOT NULL AND TIMESTAMPDIFF('second', TAB_TIME, NEXT_EVENT_TIME) BETWEEN 1 AND 1800
)
SELECT DATE_TRUNC('month', TAB_TIME) AS MONTH, TAB_LABEL, ROUND(AVG(DURATION_SECONDS)/60,1) AS AVG_MINUTES
FROM tab_durations GROUP BY MONTH, TAB_LABEL ORDER BY MONTH, TAB_LABEL""",
        "viz": {"graph.dimensions": ["MONTH"], "graph.metrics": ["AVG_MINUTES"], "series_settings": {}}
    },
    {
        "name": "Guided Experience Enablement over Time",
        "description": '"How often is the guided experience enabled in the create role screen?"\nShows adoption trend of the guided experience feature.',
        "display": "line",
        "sql": f"""SELECT DATE_TRUNC('month', TIMESTAMP) AS MONTH, COUNT(*) AS ENABLEMENTS
FROM {TABLE}
WHERE DESTINATION_NAME = 'guided_experience:enable'
  AND FEATNAME = 'Role'
  AND PAGE_SECTION = 'form.create_role'
GROUP BY 1 ORDER BY 1""",
        "viz": {"graph.dimensions": ["MONTH"], "graph.metrics": ["ENABLEMENTS"]}
    },
]


def main():
    # Step 0: Create a new dashboard
    print(f"=== Creating dashboard: {DASHBOARD_NAME} ===")
    dash_payload = {
        "name": DASHBOARD_NAME,
        "description": "IAM Telemetry Dashboard with tabs for Roles, Policies, and Identities.",
        "collection_id": COLLECTION_ID,
        "parameters": []
    }
    dash_result = api("POST", "/api/dashboard", dash_payload)
    dashboard_id = dash_result["id"]
    print(f"  Dashboard created: ID={dashboard_id}")
    print(f"  URL: {BASE_URL}/dashboard/{dashboard_id}")
    print()

    # Step 1: Create tabs (without cards)
    print("=== Creating tabs ===")
    tab_payload = {
        "tabs": [
            {"id": -1, "name": "Roles"},
            {"id": -2, "name": "Policies"},
            {"id": -3, "name": "Identities"}
        ],
        "dashcards": []
    }
    result = api("PUT", f"/api/dashboard/{dashboard_id}", tab_payload)
    tabs = result.get("tabs", [])
    print(f"  Tabs created: {json.dumps(tabs, indent=2)}")

    # Map tab names to IDs
    tab_map = {}
    for tab in tabs:
        tab_map[tab["name"]] = tab["id"]
    print(f"  Tab map: {tab_map}")

    if not tab_map:
        print("  WARNING: No tabs returned. Will try with ordered_tabs approach.")
        # Fallback: try the deprecated cards endpoint
        tab_map = {"Roles": -1, "Policies": -2, "Identities": -3}

    # Step 2: Create all cards
    all_cards = []  # (card_id, tab_name, display)

    print("\n=== Creating Roles cards (25) ===")
    for i, w in enumerate(roles_widgets, 1):
        print(f"  [{i:02d}/25] {w['name']}...", end=" ", flush=True)
        try:
            card_id = create_card(w["name"], w["description"], w["display"], w["sql"], w.get("viz"), dashboard_id=dashboard_id)
            all_cards.append((card_id, "Roles", w["display"]))
            print(f"OK (card #{card_id})")
        except Exception as e:
            print(f"FAILED: {e}")
            all_cards.append((None, "Roles", w["display"]))
        time.sleep(0.3)

    print("\n=== Creating Policies cards (17) ===")
    for i, w in enumerate(policies_widgets, 1):
        print(f"  [{i:02d}/17] {w['name']}...", end=" ", flush=True)
        try:
            card_id = create_card(w["name"], w["description"], w["display"], w["sql"], w.get("viz"), dashboard_id=dashboard_id)
            all_cards.append((card_id, "Policies", w["display"]))
            print(f"OK (card #{card_id})")
        except Exception as e:
            print(f"FAILED: {e}")
            all_cards.append((None, "Policies", w["display"]))
        time.sleep(0.3)

    print("\n=== Creating Identities cards (3) ===")
    for i, w in enumerate(identities_widgets, 1):
        print(f"  [{i:02d}/03] {w['name']}...", end=" ", flush=True)
        try:
            card_id = create_card(w["name"], w["description"], w["display"], w["sql"], w.get("viz"), dashboard_id=dashboard_id)
            all_cards.append((card_id, "Identities", w["display"]))
            print(f"OK (card #{card_id})")
        except Exception as e:
            print(f"FAILED: {e}")
            all_cards.append((None, "Identities", w["display"]))
        time.sleep(0.3)

    # Step 3: Build dashcards layout per tab
    print("\n=== Building dashboard layout ===")
    dashcards = []
    dc_id = -1

    for tab_name in ["Roles", "Policies", "Identities"]:
        tab_id = tab_map[tab_name]
        tab_cards = [(cid, disp) for cid, tname, disp in all_cards if tname == tab_name and cid is not None]

        col_cursor = 0
        row_cursor = 0
        current_row_height = 0

        for card_id, display in tab_cards:
            sx, sy = get_size(display)
            if col_cursor + sx > GRID_COLUMNS:
                row_cursor += current_row_height
                col_cursor = 0
                current_row_height = 0

            dashcards.append({
                "id": dc_id,
                "card_id": card_id,
                "row": row_cursor,
                "col": col_cursor,
                "size_x": sx,
                "size_y": sy,
                "dashboard_tab_id": tab_id,
                "parameter_mappings": [],
                "visualization_settings": {}
            })
            col_cursor += sx
            current_row_height = max(current_row_height, sy)
            dc_id -= 1

    # Step 4: PUT dashcards to dashboard
    print(f"  Total dashcards: {len(dashcards)}")
    print("\n=== Updating dashboard with cards ===")

    update_payload = {
        "dashcards": dashcards,
        "tabs": [{"id": tab_map[n], "name": n} for n in ["Roles", "Policies", "Identities"]]
    }
    result = api("PUT", f"/api/dashboard/{dashboard_id}", update_payload)
    final_tabs = result.get("tabs", [])
    final_cards = result.get("dashcards", [])
    print(f"  Dashboard updated! Tabs: {len(final_tabs)}, Cards: {len(final_cards)}")

    # Summary
    print("\n" + "=" * 60)
    print(f"DONE! Dashboard: {BASE_URL}/dashboard/{dashboard_id}")
    print(f"  Tab 1 - Roles: {sum(1 for c,t,d in all_cards if t=='Roles' and c)} cards")
    print(f"  Tab 2 - Policies: {sum(1 for c,t,d in all_cards if t=='Policies' and c)} cards")
    print(f"  Tab 3 - Identities: {sum(1 for c,t,d in all_cards if t=='Identities' and c)} cards")
    failed = sum(1 for c,t,d in all_cards if c is None)
    if failed:
        print(f"  FAILED: {failed} cards could not be created")


if __name__ == "__main__":
    main()
