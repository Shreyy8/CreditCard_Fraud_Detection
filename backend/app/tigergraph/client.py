"""
TigerGraph client — Savanna-aware, pyTigerGraph-backed.

Two-plane architecture
──────────────────────
Control-plane  api.tgcloud.io          x-api-key header (TIGERGRAPGH_SAVANNA)
               → discovers workspace hostname automatically

Data-plane     <workspace>.i.tgcloud.io  Bearer token via GSQL secret
               → runs GSQL queries, upserts vertices/edges

Auth priority
─────────────
1. TIGERGRAPH_TOKEN      pre-issued bearer token (skip getToken)
2. TIGERGRAPH_SECRET     exchange for bearer token via pyTigerGraph.getToken()
3. USERNAME + PASSWORD   basic auth (self-managed TG only)

Nothing is hardcoded.  All values come from .env via Settings.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

import requests

from ..config import get_settings

logger = logging.getLogger(__name__)

# ── Savanna control-plane base URL ────────────────────────────────────────────
_SAVANNA_API = "https://api.tgcloud.io/controller/v4/v2"


# ── Exceptions ────────────────────────────────────────────────────────────────

class TigerGraphConfigError(RuntimeError):
    """Missing or invalid .env configuration."""


class TigerGraphAuthError(RuntimeError):
    """Authentication against TigerGraph failed."""


class TigerGraphConnectionError(RuntimeError):
    """Could not reach TigerGraph host."""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _require_pytg() -> None:
    try:
        import pyTigerGraph  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "pyTigerGraph is required but not installed.\n"
            "Run:  pip install pyTigerGraph"
        ) from exc


def _savanna_headers(api_key: str) -> dict[str, str]:
    return {"Content-Type": "application/json", "x-api-key": api_key}


# ── Savanna discovery ─────────────────────────────────────────────────────────

def discover_workspace_host(api_key: str) -> str:
    """
    Use the Savanna control-plane API to find the workspace hostname.

    Walks: workgroups → workspaces → nginxHost / endpoint
    Returns a full https:// URL, e.g. https://abc123.i.tgcloud.io

    Raises TigerGraphConfigError with a clear message if nothing is found.
    """
    hdrs = _savanna_headers(api_key)

    # 1. List workgroups
    try:
        r = requests.get(f"{_SAVANNA_API}/workgroups", headers=hdrs, timeout=15)
    except requests.exceptions.ConnectionError as exc:
        raise TigerGraphConnectionError(
            f"Cannot reach Savanna control-plane at {_SAVANNA_API}. "
            "Check your internet connection."
        ) from exc

    if r.status_code == 401:
        raise TigerGraphAuthError(
            "Savanna API key rejected (HTTP 401). "
            "Check TIGERGRAPGH_SAVANNA in .env."
        )
    if r.status_code == 403:
        raise TigerGraphAuthError(
            "Savanna API key has no permission (HTTP 403). "
            "Check TIGERGRAPGH_SAVANNA in .env."
        )
    r.raise_for_status()

    workgroups = r.json().get("Result") or []
    if not workgroups:
        raise TigerGraphConfigError(
            "No workgroups found in your Savanna org. "
            "Create a workgroup and workspace at https://savanna.tgcloud.io first."
        )

    # 2. Walk every workgroup → workspace looking for a hostname
    for wg in workgroups:
        wg_id = (
            wg.get("workgroup_id")    # snake_case (actual Savanna response)
            or wg.get("workgroupID")  # camelCase (docs)
            or wg.get("id")
            or wg.get("WorkgroupID")
        )
        if not wg_id:
            continue

        # Workspaces may be embedded in the workgroup object
        embedded_workspaces = wg.get("workspaces") or []
        if embedded_workspaces:
            workspaces = embedded_workspaces
        else:
            try:
                r2 = requests.get(
                    f"{_SAVANNA_API}/workgroups/{wg_id}/workspaces",
                    headers=hdrs, timeout=15,
                )
                r2.raise_for_status()
                workspaces = r2.json().get("Result") or []
            except Exception:  # noqa: BLE001
                continue

        for ws in workspaces:
            # Try every hostname field name (snake_case and camelCase)
            for field in (
                "nginx_host",         # actual field name in Savanna v4
                "nginxHost",
                "endpoint", "Endpoint",
                "host", "Host",
                "url", "Url",
                "NginxHost",
                "workspaceNginxHost",
                "WorkspaceEndpoint",
            ):
                host = ws.get(field, "")
                if host:
                    host = host.rstrip("/")
                    if not host.startswith("http"):
                        host = f"https://{host}"
                    logger.info(
                        "Savanna discovery: found workspace host=%s (workgroup=%s)",
                        host, wg_id,
                    )
                    return host

    raise TigerGraphConfigError(
        "Could not find a workspace hostname in your Savanna org. "
        "Make sure your workspace is running at https://savanna.tgcloud.io "
        "and that the API key has read access to workgroups/workspaces."
    )


# ── Main client ───────────────────────────────────────────────────────────────

class TigerGraphClient:
    """
    Synchronous TigerGraph client backed by pyTigerGraph.
    Async callers use the async_* shims (asyncio.to_thread).
    """

    def __init__(self) -> None:
        _require_pytg()
        self._settings = get_settings()
        self._conn = None        # pyTigerGraph.TigerGraphConnection, lazy
        self._resolved_host: str = ""

    # ── Connection bootstrap ──────────────────────────────────────────────────

    def _resolve_host(self) -> str:
        """
        Return the data-plane workspace host.

        Priority:
          1. TIGERGRAPH_HOST in .env
          2. Auto-discover via Savanna control-plane API key
        """
        s = self._settings
        if s.tigergraph_host:
            return s.tigergraph_host.rstrip("/")

        api_key = s.savanna_api_key
        if not api_key:
            raise TigerGraphConfigError(
                "TIGERGRAPH_HOST is not set and no Savanna API key is available "
                "to auto-discover it.\n"
                "Add one of these to .env:\n"
                "  TIGERGRAPH_HOST=https://<workspace>.i.tgcloud.io\n"
                "  TIGERGRAPGH_SAVANNA=<your-api-key>"
            )

        logger.info("TIGERGRAPH_HOST not set — discovering via Savanna API...")
        return discover_workspace_host(api_key)

    def _build_conn(self):
        """Build a pyTigerGraph.TigerGraphConnection, obtain a token, return it."""
        import pyTigerGraph as tg

        s = self._settings
        if not s.tigergraph_graph_name:
            raise TigerGraphConfigError("TIGERGRAPH_GRAPH_NAME is not set in .env.")
        if not s.tigergraph_secret and not s.tigergraph_token and not s.tigergraph_password:
            raise TigerGraphConfigError(
                "No authentication credential found in .env.\n"
                "Set TIGERGRAPH_SECRET (recommended for Savanna) or TIGERGRAPH_TOKEN."
            )

        host = self._resolve_host()
        self._resolved_host = host
        graphname = s.tigergraph_graph_name

        # tgCloud=True makes pyTigerGraph use port 443 for both REST++ and GSQL
        is_tgcloud = "tgcloud.io" in host.lower()

        logger.info(
            "Connecting to TigerGraph: host=%s graph=%s tgCloud=%s",
            host, graphname, is_tgcloud,
        )

        conn = tg.TigerGraphConnection(
            host=host,
            graphname=graphname,
            gsqlSecret=s.tigergraph_secret or "",
            username=s.tigergraph_username or "tigergraph",
            password=s.tigergraph_password or "tigergraph",
            tgCloud=is_tgcloud,
        )

        # Authenticate
        if s.tigergraph_token:
            conn.apiToken = s.tigergraph_token
            logger.info("TigerGraph auth: using pre-issued token from TIGERGRAPH_TOKEN")
        elif s.tigergraph_secret:
            logger.info("TigerGraph auth: requesting token via GSQL secret...")
            try:
                result = conn.getToken(s.tigergraph_secret)
            except Exception as exc:
                raise TigerGraphAuthError(
                    f"getToken() failed for host={host} graph={graphname}.\n"
                    f"Error: {exc}\n"
                    "Check TIGERGRAPH_SECRET and ensure the workspace is running."
                ) from exc
            token = result[0] if isinstance(result, (tuple, list)) else str(result)
            conn.apiToken = token
            logger.info("TigerGraph auth: token obtained successfully")
        else:
            logger.info("TigerGraph auth: using username/password")

        return conn

    def _ensure_conn(self) -> None:
        if self._conn is None:
            self._conn = self._build_conn()

    # ── Public API ────────────────────────────────────────────────────────────

    def health(self) -> dict[str, Any]:
        """Echo the server and return structured health info. Raises on failure."""
        self._ensure_conn()
        t0 = time.monotonic()
        try:
            echo = self._conn.echo()
        except Exception as exc:
            raise TigerGraphConnectionError(
                f"TigerGraph echo() failed: {exc}"
            ) from exc
        latency = round(time.monotonic() - t0, 3)
        return {
            "status": "ok",
            "echo": echo,
            "host": self._resolved_host,
            "graph": self._settings.tigergraph_graph_name,
            "latency_s": latency,
        }

    def installed_queries(self) -> dict[str, Any]:
        """Return all installed queries on the configured graph."""
        self._ensure_conn()
        return self._conn.getInstalledQueries()

    def run_query(self, query_name: str, params: dict | None = None) -> list[Any]:
        """
        Execute an installed GSQL query via runInstalledQuery().
        query_name is always the short name (e.g. "Transaction_Fraud").
        VERTEX<T> params are automatically wrapped as 1-tuples.
        Returns the results list.  Raises on auth/connection failure.
        """
        self._ensure_conn()
        short_name = query_name.split("/")[-1] if "/" in query_name else query_name
        # Wrap plain string values as 1-tuples for VERTEX<T> parameters
        fixed: dict = {}
        for k, v in (params or {}).items():
            fixed[k] = (v,) if isinstance(v, str) else v
        result = self._conn.runInstalledQuery(short_name, params=fixed)
        return result if isinstance(result, list) else []

    def upsert_vertex(self, vtype: str, vid: str, attrs: dict) -> bool:
        self._ensure_conn()
        return bool(self._conn.upsertVertex(vtype, vid, attrs))

    def upsert_edge(
        self,
        src_type: str, src_id: str,
        edge_type: str,
        tgt_type: str, tgt_id: str,
        attrs: dict | None = None,
    ) -> bool:
        self._ensure_conn()
        return bool(
            self._conn.upsertEdge(src_type, src_id, edge_type, tgt_type, tgt_id, attrs or {})
        )

    def get_vertex(self, vtype: str, vid: str) -> dict | None:
        self._ensure_conn()
        try:
            # This graph exposes the application case identifier as an
            # attribute; the SDK version in use has no getVertex-by-ID API.
            where = f'case_id=="{vid}"' if vtype == "FraudCase" else f'v_id=="{vid}"'
            results = self._conn.getVertices(vtype, where=where, limit=1)
            return results[0] if results else None
        except Exception:  # noqa: BLE001
            return None

    def get_schema(self) -> dict:
        self._ensure_conn()
        return self._conn.getSchema()

    def close(self) -> None:
        self._conn = None

    # ── Async shims (wrap sync calls so the event loop is never blocked) ───────

    async def ping(self) -> bool:
        import asyncio
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(self.health),
                timeout=8.0,
            )
            return result.get("status") == "ok"
        except Exception as exc:
            logger.warning("TigerGraph ping failed: %s", exc)
            return False

    async def async_run_query(
        self, query_name: str, params: dict | None = None
    ) -> list[Any]:
        import asyncio
        # Keep async calls on the same VERTEX<T> contract as run_query().
        fixed_params = {
            key: (value,) if isinstance(value, str) else value
            for key, value in (params or {}).items()
        }
        return await asyncio.to_thread(self.run_query, query_name, fixed_params)

    async def async_upsert_vertex(self, vtype: str, vid: str, attrs: dict) -> bool:
        import asyncio
        return await asyncio.to_thread(self.upsert_vertex, vtype, vid, attrs)

    async def async_get_vertex(self, vtype: str, vid: str) -> dict | None:
        import asyncio
        return await asyncio.to_thread(self.get_vertex, vtype, vid)

    async def async_upsert_edge(
        self,
        src_type: str, src_id: str,
        edge_type: str,
        tgt_type: str, tgt_id: str,
        attrs: dict | None = None,
    ) -> bool:
        import asyncio
        return await asyncio.to_thread(
            self.upsert_edge, src_type, src_id, edge_type, tgt_type, tgt_id, attrs
        )


# ── Module-level singleton ────────────────────────────────────────────────────

_client_instance: Optional[TigerGraphClient] = None


def get_client() -> TigerGraphClient:
    global _client_instance
    if _client_instance is None:
        _client_instance = TigerGraphClient()
    return _client_instance


def reset_client() -> None:
    """Force a fresh connection on the next get_client() call."""
    global _client_instance
    if _client_instance:
        _client_instance.close()
    _client_instance = None
