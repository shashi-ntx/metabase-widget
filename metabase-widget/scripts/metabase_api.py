#!/usr/bin/env python3
"""Metabase REST API client for the metabase-widget skill.

Stdlib-only. Reads config from environment variables (and an optional .env in CWD).

Subcommands:
    check                    Verify connectivity (GET /api/user/current, GET /api/database/{id})
    list-databases           GET /api/database
    list-collections         GET /api/collection
    list-tables              GET /api/database/{id}/metadata
    find-dashboard           GET /api/search?models=dashboard or extract ID from URL
    get-dashboard            GET /api/dashboard/{id}
    create-card              POST /api/card (native SQL)
    create-dashboard         POST /api/dashboard
    put-dashboard-cards      PUT /api/dashboard/{id} with a dashcards array
    run-card                 POST /api/card/{id}/query

Run `python metabase_api.py <subcommand> --help` for flags.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def load_dotenv(path: Path = Path(".env")) -> None:
    """Load KEY=VALUE pairs from .env into os.environ if not already set."""
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def require_env(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        sys.stderr.write(
            f"ERROR: required environment variable {name} is not set.\n"
            f"       Set it in your shell or in a local .env file (see .env.example).\n"
        )
        sys.exit(2)
    return val


def get_config() -> dict[str, Any]:
    load_dotenv()
    base_url = require_env("METABASE_BASE_URL").rstrip("/")
    return {
        "base_url": base_url,
        "api_key": require_env("METABASE_API_KEY"),
        "database_id": int(require_env("METABASE_DATABASE_ID")),
        "default_collection_id": _int_or_none(os.environ.get("METABASE_DEFAULT_COLLECTION_ID")),
        "default_table_name": os.environ.get(
            "METABASE_DEFAULT_TABLE_NAME",
            "NUSIGHTS_EVENTS_ACTIVITYTYPE_DEFAULT_HISTORICAL_TBL_FLAT",
        ),
    }


def _int_or_none(s: str | None) -> int | None:
    if s is None or s == "":
        return None
    try:
        return int(s)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------


class ApiError(Exception):
    def __init__(self, status: int, body: str, hint: str = ""):
        self.status = status
        self.body = body
        self.hint = hint
        super().__init__(f"HTTP {status}: {body}{(' — ' + hint) if hint else ''}")


def request(
    method: str,
    path: str,
    *,
    body: dict | None = None,
    query: dict | None = None,
    timeout: int = 30,
) -> Any:
    cfg = get_config()
    url = f"{cfg['base_url']}{path}"
    if query:
        url += "?" + urllib.parse.urlencode({k: v for k, v in query.items() if v is not None})

    data: bytes | None = None
    headers = {
        "X-API-Key": cfg["api_key"],
        "Accept": "application/json",
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            if not raw:
                return None
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        hint = _hint_for(e.code, path, body_text)
        raise ApiError(e.code, body_text, hint) from None
    except urllib.error.URLError as e:
        raise ApiError(0, str(e.reason), "Could not reach Metabase — check METABASE_BASE_URL and network.") from None


def _hint_for(status: int, path: str, body: str) -> str:
    if status == 401:
        return "API key invalid or expired. Re-create it in Admin → Settings → Authentication → API Keys."
    if status == 403:
        return "Permission denied. Check that the API key's group can read the database and write to the target collection."
    if status == 404:
        return f"Resource not found at {path}. Run a list-* subcommand to confirm the ID exists."
    if status == 400 and "already exists" in body.lower():
        return "Name collision. Rename the resource or delete the existing one."
    if status == 400 and "dataset_query" in body.lower():
        return "SQL or query is invalid. Check the SQL compiles in Metabase's native query editor."
    if status >= 500:
        return "Metabase internal error. Retrying once with backoff usually helps."
    return ""


def request_with_retry(method: str, path: str, **kwargs) -> Any:
    """Try once, retry once on 5xx with 2s backoff."""
    try:
        return request(method, path, **kwargs)
    except ApiError as e:
        if e.status >= 500 or e.status == 0:
            time.sleep(2)
            return request(method, path, **kwargs)
        raise


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------


def cmd_check(args) -> int:
    cfg = get_config()
    print(f"→ Metabase: {cfg['base_url']}")
    try:
        user = request("GET", "/api/user/current")
        print(f"✓ Authenticated as: {user.get('email') or user.get('common_name') or '<unknown>'}")
    except ApiError as e:
        print(f"✗ Auth check failed: {e}", file=sys.stderr)
        return 1
    try:
        db = request("GET", f"/api/database/{cfg['database_id']}")
        print(f"✓ Database {cfg['database_id']}: {db.get('name')} ({db.get('engine')})")
    except ApiError as e:
        print(f"✗ Database check failed: {e}", file=sys.stderr)
        return 1
    coll_id = cfg["default_collection_id"]
    if coll_id is not None:
        try:
            coll = request("GET", f"/api/collection/{coll_id}")
            print(f"✓ Default collection {coll_id}: {coll.get('name')}")
        except ApiError as e:
            print(f"✗ Default collection check failed: {e}", file=sys.stderr)
            return 1
    print("OK")
    return 0


def cmd_list_databases(args) -> int:
    data = request("GET", "/api/database")
    items = data.get("data", data) if isinstance(data, dict) else data
    for db in items:
        print(f"{db['id']:>4}  {db.get('engine','?'):<10}  {db['name']}")
    return 0


def cmd_list_collections(args) -> int:
    items = request("GET", "/api/collection")
    for c in items:
        cid = c.get("id")
        if cid is None or cid == "root":
            continue
        print(f"{cid:>5}  {c['name']}")
    return 0


def cmd_list_tables(args) -> int:
    db_id = args.database_id or get_config()["database_id"]
    meta = request("GET", f"/api/database/{db_id}/metadata", query={"include_hidden": "true"})
    for t in meta.get("tables", []):
        print(f"{t['id']:>5}  {t.get('schema','?'):<15}  {t['name']}")
    return 0


def cmd_find_dashboard(args) -> int:
    if args.url:
        m = re.search(r"/dashboard/(\d+)", args.url)
        if not m:
            print("Could not extract dashboard ID from URL.", file=sys.stderr)
            return 1
        dash_id = int(m.group(1))
        dash = request("GET", f"/api/dashboard/{dash_id}")
        print(json.dumps({"id": dash["id"], "name": dash["name"], "collection_id": dash.get("collection_id")}, indent=2))
        return 0
    if args.query:
        result = request("GET", "/api/search", query={"q": args.query, "models": "dashboard"})
        items = result.get("data", []) if isinstance(result, dict) else result
        if not items:
            print("[]")
            return 0
        out = [
            {"id": i["id"], "name": i["name"], "collection_id": i.get("collection_id")}
            for i in items
            if i.get("model") in (None, "dashboard")
        ]
        print(json.dumps(out, indent=2))
        return 0
    print("Provide --query or --url.", file=sys.stderr)
    return 2


def cmd_get_dashboard(args) -> int:
    dash = request("GET", f"/api/dashboard/{args.dashboard_id}")
    print(json.dumps(dash, indent=2))
    return 0


def _read_text_arg(value: str | None, file_arg: str | None) -> str | None:
    if value is not None:
        return value
    if file_arg is not None:
        return Path(file_arg).read_text()
    return None


def _read_json_arg(value: str | None, file_arg: str | None) -> Any:
    text = _read_text_arg(value, file_arg)
    if text is None:
        return None
    return json.loads(text)


def cmd_create_card(args) -> int:
    cfg = get_config()
    sql = _read_text_arg(args.sql, args.sql_file)
    if not sql:
        print("Provide --sql or --sql-file.", file=sys.stderr)
        return 2
    description = _read_text_arg(args.description, args.description_file) or ""
    viz_settings = _read_json_arg(args.visualization_settings, args.visualization_settings_file) or {}
    collection_id = args.collection_id if args.collection_id is not None else cfg["default_collection_id"]

    payload: dict[str, Any] = {
        "name": args.name,
        "description": description,
        "collection_id": collection_id,
        "display": args.display,
        "visualization_settings": viz_settings,
        "dataset_query": {
            "database": cfg["database_id"],
            "type": "native",
            "native": {
                "query": sql,
                "template-tags": {},
            },
        },
    }
    card = request_with_retry("POST", "/api/card", body=payload)
    out = {
        "id": card["id"],
        "name": card["name"],
        "url": f"{cfg['base_url']}/question/{card['id']}",
    }
    print(json.dumps(out, indent=2))
    return 0


def cmd_create_dashboard(args) -> int:
    cfg = get_config()
    collection_id = args.collection_id if args.collection_id is not None else cfg["default_collection_id"]
    payload: dict[str, Any] = {
        "name": args.name,
        "description": args.description or "",
        "collection_id": collection_id,
        "parameters": [],
    }
    dash = request_with_retry("POST", "/api/dashboard", body=payload)
    out = {
        "id": dash["id"],
        "name": dash["name"],
        "url": f"{cfg['base_url']}/dashboard/{dash['id']}",
    }
    print(json.dumps(out, indent=2))
    return 0


def cmd_put_dashboard_cards(args) -> int:
    cfg = get_config()
    dashcards = _read_json_arg(None, args.dashcards_file)
    if dashcards is None:
        print("Provide --dashcards-file.", file=sys.stderr)
        return 2
    if not isinstance(dashcards, list):
        print("dashcards file must contain a JSON array.", file=sys.stderr)
        return 2
    payload = {"dashcards": dashcards}
    dash = request_with_retry("PUT", f"/api/dashboard/{args.dashboard_id}", body=payload)
    out = {
        "id": dash["id"],
        "url": f"{cfg['base_url']}/dashboard/{dash['id']}",
        "dashcard_count": len(dash.get("dashcards", [])),
    }
    print(json.dumps(out, indent=2))
    return 0


def cmd_run_card(args) -> int:
    result = request_with_retry("POST", f"/api/card/{args.card_id}/query", body={})
    print(json.dumps(result, indent=2))
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Metabase REST API client for the metabase-widget skill.")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("check", help="Verify connectivity").set_defaults(func=cmd_check)
    sub.add_parser("list-databases", help="List databases").set_defaults(func=cmd_list_databases)
    sub.add_parser("list-collections", help="List collections").set_defaults(func=cmd_list_collections)

    pt = sub.add_parser("list-tables", help="List tables in a database")
    pt.add_argument("--database-id", type=int)
    pt.set_defaults(func=cmd_list_tables)

    pf = sub.add_parser("find-dashboard", help="Find a dashboard by name or URL")
    pf.add_argument("--query")
    pf.add_argument("--url")
    pf.set_defaults(func=cmd_find_dashboard)

    pg = sub.add_parser("get-dashboard", help="Get a dashboard's full definition")
    pg.add_argument("--dashboard-id", type=int, required=True)
    pg.set_defaults(func=cmd_get_dashboard)

    pc = sub.add_parser("create-card", help="Create a native SQL question")
    pc.add_argument("--name", required=True)
    pc.add_argument("--description")
    pc.add_argument("--description-file")
    pc.add_argument("--sql")
    pc.add_argument("--sql-file")
    pc.add_argument("--display", default="table",
                    help="Metabase display value: table, bar, row, line, area, pie, scalar, smartscalar, funnel, scatter, combo, waterfall, progress, gauge, map, pivot")
    pc.add_argument("--visualization-settings", help="JSON string")
    pc.add_argument("--visualization-settings-file", help="Path to JSON file")
    pc.add_argument("--collection-id", type=int)
    pc.set_defaults(func=cmd_create_card)

    pd = sub.add_parser("create-dashboard", help="Create an empty dashboard")
    pd.add_argument("--name", required=True)
    pd.add_argument("--description")
    pd.add_argument("--collection-id", type=int)
    pd.set_defaults(func=cmd_create_dashboard)

    pp = sub.add_parser("put-dashboard-cards", help="Replace a dashboard's dashcards array")
    pp.add_argument("--dashboard-id", type=int, required=True)
    pp.add_argument("--dashcards-file", required=True,
                    help="Path to a JSON file containing the full dashcards array")
    pp.set_defaults(func=cmd_put_dashboard_cards)

    pr = sub.add_parser("run-card", help="Run a card and print results")
    pr.add_argument("--card-id", type=int, required=True)
    pr.set_defaults(func=cmd_run_card)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ApiError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
