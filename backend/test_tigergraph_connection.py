"""
TigerGraph real connection test.

Run from the backend/ directory:
    python test_tigergraph_connection.py

Exit codes:
    0  all checks passed
    1  one or more checks failed

Nothing fake.  Every FAIL contains the actual error from TigerGraph/network.
Secrets are never printed.
"""

from __future__ import annotations

import sys
import time
import traceback
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))

# ── Force settings reload from .env ──────────────────────────────────────────
from app.config import get_settings
get_settings.cache_clear()
settings = get_settings()

import requests

# ── Constants ─────────────────────────────────────────────────────────────────
_SAVANNA_API = "https://api.tgcloud.io/controller/v4/v2"
_WIDTH = 60

# All field names Savanna has ever used for the workspace hostname
_HOST_FIELDS = (
    "nginx_host",            # actual field in Savanna v4 (snake_case)
    "nginxHost",             # camelCase variant in some docs
    "endpoint", "Endpoint",
    "host", "Host",
    "url", "Url",
    "NginxHost",
    "workspaceNginxHost",
    "WorkspaceEndpoint",
)


def _line(label: str, result: str, detail: str = "") -> None:
    print(f"  {label:<38} [{result:<8}]  {detail}")


def _section(title: str) -> None:
    print(f"\n{'─' * _WIDTH}")
    print(f"  {title}")
    print(f"{'─' * _WIDTH}")


def _mask(value: str) -> str:
    if len(value) <= 8:
        return "****"
    return value[:4] + "****" + value[-4:]


def _extract_host(ws: dict) -> str:
    """Pull hostname from a workspace dict, trying every known field name."""
    for field in _HOST_FIELDS:
        val = ws.get(field, "")
        if val:
            val = val.rstrip("/")
            return val if val.startswith("http") else f"https://{val}"
    return ""


# ══════════════════════════════════════════════════════════════════════════════
# Step 1 — .env loaded correctly
# ══════════════════════════════════════════════════════════════════════════════

def check_env() -> tuple[bool, dict]:
    _section("1. Environment (.env)")
    ok = True

    api_key = settings.savanna_api_key
    secret  = settings.tigergraph_secret
    token   = settings.tigergraph_token
    host    = settings.tigergraph_host
    graph   = settings.tigergraph_graph_name

    _line("TIGERGRAPGH_SAVANNA (api key)",
          "OK" if api_key else "MISSING",
          _mask(api_key) if api_key else "add TIGERGRAPGH_SAVANNA to .env")
    _line("TIGERGRAPH_SECRET",
          "OK" if secret else "MISSING",
          _mask(secret) if secret else "add TIGERGRAPH_SECRET to .env")
    _line("TIGERGRAPH_GRAPH_NAME",
          "OK" if graph else "MISSING",
          graph or "add to .env")
    _line("TIGERGRAPH_HOST",
          "OK" if host else "AUTO",
          host if host else "(will auto-discover via Savanna API)")
    _line("TIGERGRAPH_TOKEN",
          "OK" if token else "not set",
          "(optional — secret preferred)")

    if not api_key and not secret and not token:
        print("\n  ERROR: no auth credentials in .env")
        ok = False
    if not graph:
        print("\n  ERROR: TIGERGRAPH_GRAPH_NAME not set")
        ok = False

    return ok, {"api_key": api_key, "secret": secret,
                "token": token, "host": host, "graph": graph}


# ══════════════════════════════════════════════════════════════════════════════
# Step 2 — Savanna control-plane + workspace host discovery
# ══════════════════════════════════════════════════════════════════════════════

def check_control_plane(api_key: str) -> tuple[bool, str]:
    _section("2. Savanna control-plane  (api.tgcloud.io)")
    if not api_key:
        _line("API key present", "SKIP", "no key in .env")
        return False, ""

    hdrs = {"Content-Type": "application/json", "x-api-key": api_key}

    # Hit /workgroups
    try:
        t0 = time.monotonic()
        r  = requests.get(f"{_SAVANNA_API}/workgroups", headers=hdrs, timeout=15)
        ms = int((time.monotonic() - t0) * 1000)
    except requests.exceptions.ConnectionError as exc:
        _line("Reach api.tgcloud.io", "FAIL", str(exc))
        return False, ""

    if r.status_code == 401:
        _line("API key auth", "FAIL", "HTTP 401 — key rejected")
        return False, ""
    if r.status_code == 403:
        _line("API key auth", "FAIL", "HTTP 403 — no permission")
        return False, ""
    if not r.ok:
        _line("API key auth", "FAIL", f"HTTP {r.status_code}: {r.text[:120]}")
        return False, ""

    _line("Reach api.tgcloud.io", "PASS", f"{ms} ms")
    _line("API key auth",         "PASS", "")

    workgroups = r.json().get("Result") or []
    _line("Workgroups found", "OK" if workgroups else "NONE", str(len(workgroups)))

    discovered_host = ""

    for wg in workgroups:
        # Savanna v4 uses snake_case field names
        wg_id   = (wg.get("workgroup_id") or wg.get("workgroupID")
                   or wg.get("id") or wg.get("WorkgroupID", ""))
        wg_name = wg.get("name") or wg.get("workgroupName", wg_id)
        if not wg_id:
            continue

        # Workspaces can be embedded inside the workgroup object (v4)
        # OR returned separately from /workgroups/{id}/workspaces
        workspaces = wg.get("workspaces") or []
        if not workspaces:
            try:
                r2 = requests.get(
                    f"{_SAVANNA_API}/workgroups/{wg_id}/workspaces",
                    headers=hdrs, timeout=15,
                )
                if r2.ok:
                    workspaces = r2.json().get("Result") or []
            except Exception:
                pass

        print(f"\n  Workgroup: {wg_name}  ({wg_id})")

        for ws in workspaces:
            ws_name  = ws.get("name") or ws.get("workspaceName", "")
            ws_id    = (ws.get("workspace_id") or ws.get("workspaceID")
                        or ws.get("id", ""))
            status   = (ws.get("display_status") or ws.get("status")
                        or ws.get("workspaceStatus", ""))
            catalog  = ws.get("solution_catalog_id", "")

            print(f"    Workspace : {ws_name} ({ws_id})")
            print(f"    Status    : {status}")
            if catalog:
                print(f"    Catalog   : {catalog}")

            host = _extract_host(ws)
            if host:
                print(f"    Host      : {host}")
                if not discovered_host:
                    discovered_host = host
            else:
                # Show all keys so we can add missing ones later
                print(f"    (all keys): {list(ws.keys())}")

    if discovered_host:
        _line("Workspace host discovered", "PASS", discovered_host)
    else:
        _line("Workspace host discovered", "FAIL",
              "set TIGERGRAPH_HOST in .env manually")

    return bool(workgroups), discovered_host


# ══════════════════════════════════════════════════════════════════════════════
# Step 3 — data-plane connection + token
# ══════════════════════════════════════════════════════════════════════════════

def check_data_plane(host: str, secret: str, token: str, graph: str):
    _section("3. Data-plane connection  (workspace REST++)")

    if not host:
        _line("Workspace host", "FAIL", "host not resolved — cannot proceed")
        return False, None

    _line("Workspace host", "OK",   host)
    _line("Graph name",     "OK",   graph)

    try:
        import pyTigerGraph as tg
    except ImportError:
        _line("pyTigerGraph import", "FAIL", "run: pip install pyTigerGraph")
        return False, None

    _line("pyTigerGraph import", "PASS", tg.__version__)

    is_tgcloud = "tgcloud.io" in host.lower()

    try:
        conn = tg.TigerGraphConnection(
            host=host,
            graphname=graph,
            gsqlSecret=secret or "",
            username=settings.tigergraph_username or "tigergraph",
            password=settings.tigergraph_password or "tigergraph",
            tgCloud=is_tgcloud,
        )
    except Exception as exc:
        _line("Build TigerGraphConnection", "FAIL", str(exc))
        return False, None

    _line("Build TigerGraphConnection", "PASS",
          f"restppUrl={conn.restppUrl}")

    # Authenticate
    if token:
        conn.apiToken = token
        _line("Auth (pre-issued token)", "PASS", "from TIGERGRAPH_TOKEN")
    elif secret:
        try:
            t0  = time.monotonic()
            res = conn.getToken(secret)
            ms  = int((time.monotonic() - t0) * 1000)
            tok = res[0] if isinstance(res, (tuple, list)) else str(res)
            conn.apiToken = tok
            _line("Auth (getToken via secret)", "PASS",
                  f"{ms} ms  token={_mask(tok)}")
        except Exception as exc:
            _line("Auth (getToken via secret)", "FAIL", str(exc))
            traceback.print_exc()
            return False, None
    else:
        _line("Auth", "SKIP", "using username/password")

    # Echo / health
    try:
        t0   = time.monotonic()
        echo = conn.echo()
        ms   = int((time.monotonic() - t0) * 1000)
        _line("echo() health", "PASS", f"{ms} ms  → {str(echo)[:60]}")
    except Exception as exc:
        _line("echo() health", "FAIL", str(exc))
        return False, None

    return True, conn


# ══════════════════════════════════════════════════════════════════════════════
# Step 4 — installed queries
# ══════════════════════════════════════════════════════════════════════════════

def check_installed_queries(conn) -> tuple[bool, dict]:
    _section("4. Installed GSQL queries")
    try:
        queries = conn.getInstalledQueries()
    except Exception as exc:
        _line("getInstalledQueries()", "FAIL", str(exc))
        return False, {}

    count = len(queries) if isinstance(queries, dict) else 0
    _line("getInstalledQueries()", "PASS", f"{count} queries installed")

    if isinstance(queries, dict):
        for name in list(queries.keys())[:15]:
            print(f"    • {name}")
        if count > 15:
            print(f"    … and {count - 15} more")

    return True, queries if isinstance(queries, dict) else {}


# ══════════════════════════════════════════════════════════════════════════════
# Step 5 — Transaction_Fraud query
# ══════════════════════════════════════════════════════════════════════════════

def check_transaction_fraud(conn, installed: dict) -> bool:
    _section("5. Transaction_Fraud query")
    target = "Transaction_Fraud"

    # Case-insensitive search — keys may be full URL paths like
    # "GET /query/FraudCaseGraph/Transaction_Fraud"
    found_name = None
    found_short = None
    for k in installed:
        # Strip path prefix if present
        short = k.split("/")[-1] if "/" in k else k
        if short.lower() == target.lower():
            found_name = k      # full key (for dict lookup)
            found_short = short  # short name (for runInstalledQuery)
            break

    if not found_name:
        _line(f"{target} present", "NOT FOUND", "")
        print(f"\n  Available queries ({len(installed)}): "
              f"{list(installed.keys())[:20]}")
        return False

    _line(f"{target} present", "FOUND", found_short)

    # Extract parameter metadata
    meta        = installed.get(found_name, {})
    params_meta = meta.get("parameters") or meta.get("params") or []
    params: dict = {}

    if params_meta and isinstance(params_meta, list) and isinstance(params_meta[0], dict):
        print(f"\n  Parameters ({len(params_meta)}):")
        for p in params_meta:
            pname = p.get("paramName") or p.get("name") or ""
            ptype = (p.get("paramType") or p.get("type") or "").upper()
            print(f"    {pname}: {ptype}")
            if "VERTEX" in ptype:
                params[pname] = "3514030"
            elif "INT" in ptype:
                params[pname] = 10
            elif "FLOAT" in ptype or "DOUBLE" in ptype:
                params[pname] = 0.5
            elif "BOOL" in ptype:
                params[pname] = False
            else:
                params[pname] = ""
    else:
        # Transaction_Fraud(VERTEX<Transaction> txn) — pass a known txn ID
        params = {"txn": "3514030"}
        print(f"\n  Using default params: {params}")

    print(f"\n  runInstalledQuery('{found_short}', {params})")
    try:
        t0  = time.monotonic()
        res = conn.runInstalledQuery(found_short, params=params)
        ms  = int((time.monotonic() - t0) * 1000)
        result_len = len(res) if isinstance(res, list) else 1
        _line("runInstalledQuery", "PASS",
              f"{ms} ms  results={result_len}")
        print(f"\n  Result (first 600 chars):\n  {str(res)[:600]}")
        return True
    except Exception as exc:
        _line("runInstalledQuery", "FAIL", str(exc))
        traceback.print_exc()
        return False


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    print("=" * _WIDTH)
    print("  TigerGraph Connectivity Test")
    print("=" * _WIDTH)

    passed: list[str] = []
    failed: list[str] = []

    # 1. .env
    env_ok, env_info = check_env()
    (passed if env_ok else failed).append(".env loaded")

    # 2. Control-plane + host discovery
    cp_ok, discovered_host = check_control_plane(env_info.get("api_key", ""))
    (passed if cp_ok else failed).append("Savanna control-plane")

    # Resolve final host: explicit .env value wins, discovered is fallback
    host = env_info.get("host") or discovered_host

    # 3. Data-plane
    dp_ok, conn = check_data_plane(
        host,
        env_info.get("secret", ""),
        env_info.get("token", ""),
        env_info.get("graph", ""),
    )
    (passed if dp_ok else failed).append("Data-plane auth + echo")

    # 4. Installed queries
    if conn:
        iq_ok, installed = check_installed_queries(conn)
        (passed if iq_ok else failed).append("Installed queries")
    else:
        _section("4. Installed GSQL queries")
        print("  SKIP — no connection")
        failed.append("Installed queries")
        installed = {}

    # 5. Transaction_Fraud
    if conn and installed:
        tf_ok = check_transaction_fraud(conn, installed)
        (passed if tf_ok else failed).append("Transaction_Fraud")
    else:
        _section("5. Transaction_Fraud query")
        print("  SKIP — no connection or no queries")
        failed.append("Transaction_Fraud")

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'═' * _WIDTH}")
    print("  SUMMARY")
    print(f"{'═' * _WIDTH}")
    print(f"  Host    : {host or '(not resolved)'}")
    print(f"  Graph   : {env_info.get('graph', '')}")
    print(f"  pyTG    : installed (v{__import__('pyTigerGraph').__version__})")
    print()
    for item in passed:
        print(f"  ✓  {item}")
    for item in failed:
        print(f"  ✗  {item}")

    all_ok = len(failed) == 0
    print(f"\n  Result : {'ALL PASS' if all_ok else str(len(failed)) + ' check(s) FAILED'}")
    print(f"{'═' * _WIDTH}\n")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
