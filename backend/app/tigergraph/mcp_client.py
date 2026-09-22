"""
TigerGraph MCP client — backed by the official tigergraph-mcp package.

Uses the real tigergraph-mcp subprocess via stdio.

Architecture
────────────
  FraudAgent / GraphRetriever
       ↓
  MCPInvestigationClient          ← this module
       ↓
  tigergraph-mcp subprocess       ← official TigerGraph MCP server
       ↓
  pyTigerGraph async              ← actual REST++ calls
       ↓
  TigerGraph Savanna / FraudCaseGraph

Auth
────
The MCP subprocess reads TG_* env vars (not our TIGERGRAPH_* vars).
We map them in _mcp_env() from Settings at call time — no hardcoding.

Provenance
──────────
Every result is wrapped in a ProvenanceMCPResult that records:
  source_type, tool_name, query_name, entity_ids, raw_data, retrieved_at
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from ..config import get_settings

logger = logging.getLogger(__name__)


# ── JSON parser for MCP text responses ───────────────────────────────────────

def _parse_mcp_json(raw: str) -> dict:
    """
    Extract the JSON object from an MCP text response.

    MCP responses look like:
        ```json
        { "success": true, "data": {...}, "summary": "...", "suggestions": [...] }
        ```
    or just raw JSON. We scan for the outermost { } object.
    """
    if not raw:
        return {}

    # Strip markdown fences
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Drop first line (``` or ```json) and last line (```)
        inner_lines = lines[1:]
        if inner_lines and inner_lines[-1].strip() == "```":
            inner_lines = inner_lines[:-1]
        text = "\n".join(inner_lines).strip()

    # Find the first complete JSON object by scanning braces
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start != -1:
                try:
                    return json.loads(text[start: i + 1])
                except json.JSONDecodeError:
                    break

    # Fallback: try the full text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw_text": text[:500]}


# ── Provenance wrapper ────────────────────────────────────────────────────────

@dataclass
class ProvenanceMCPResult:
    """Every MCP tool result carries full provenance."""
    source_type: str = "tigergraph_mcp"
    tool_name: str = ""
    query_name: str = ""
    entity_ids: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    raw_data: Any = None
    success: bool = False
    error: str = ""
    started_at: str = ""
    completed_at: str = ""
    duration_ms: float = 0.0
    retrieved_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_type":  self.source_type,
            "tool_name":    self.tool_name,
            "query_name":   self.query_name,
            "entity_ids":   self.entity_ids,
            "evidence":     self.evidence,
            "success":      self.success,
            "error":        self.error,
            "retrieved_at": self.retrieved_at,
            "started_at":   self.started_at,
            "completed_at": self.completed_at,
            "duration_ms":  self.duration_ms,
        }


# ── Env mapping ───────────────────────────────────────────────────────────────

def _mcp_env() -> dict[str, str]:
    """
    Build the TG_* environment the MCP subprocess expects.
    Reads from Settings so no credentials are hardcoded here.
    """
    s = get_settings()
    env = dict(os.environ)
    env.update({
        "TG_HOST":      s.tigergraph_host,
        "TG_GRAPHNAME": s.tigergraph_graph_name,
        "TG_SECRET":    s.tigergraph_secret,
        "TG_TGCLOUD":   "true",
        "TG_SSL_PORT":  "443",
    })
    # Pre-issued token takes priority over secret
    if s.tigergraph_token:
        env["TG_API_TOKEN"] = s.tigergraph_token
    return env


# ── Session management ────────────────────────────────────────────────────────

class _MCPSession:
    """
    Manages a single stdio session with the MCP subprocess.
    Keeps the session open for the lifetime of one investigation.
    """

    def __init__(self) -> None:
        self._session = None
        self._ctx_stack: list[Any] = []
        self._tools: list[Any] = []

    async def open(self) -> None:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import get_default_environment, stdio_client

        env = {**get_default_environment(), **_mcp_env()}
        server_params = StdioServerParameters(
            command="tigergraph-mcp",
            args=[],
            env=env,
        )
        self._stdio_ctx = stdio_client(server_params)
        streams = await self._stdio_ctx.__aenter__()
        read_stream, write_stream = streams
        self._session_ctx = ClientSession(read_stream, write_stream)
        self._session = await self._session_ctx.__aenter__()
        await self._session.initialize()
        tools_resp = await self._session.list_tools()
        self._tools = tools_resp.tools

    async def close(self) -> None:
        if self._session_ctx:
            try:
                await self._session_ctx.__aexit__(None, None, None)
            except Exception:  # noqa: BLE001
                pass
        if self._stdio_ctx:
            try:
                await self._stdio_ctx.__aexit__(None, None, None)
            except Exception:  # noqa: BLE001
                pass

    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
        if self._session is None:
            raise RuntimeError("Session not open")
        result = await self._session.call_tool(tool_name, arguments=arguments)
        # Collect all text content
        texts = [c.text for c in result.content if hasattr(c, "text")]
        if not texts:
            return {}
        raw = "\n".join(texts)
        return _parse_mcp_json(raw)

    @property
    def tools(self) -> list[Any]:
        return self._tools

    @property
    def tool_names(self) -> list[str]:
        return [t.name for t in self._tools]


# ── Investigation client ──────────────────────────────────────────────────────

class MCPInvestigationClient:
    """
    Investigation-oriented MCP client for the fraud agent.

    Opens one stdio session per investigation run and closes it when done.
    All results are wrapped in ProvenanceMCPResult.

    If the MCP subprocess is unavailable (package not installed, TG down),
    every method returns a failed ProvenanceMCPResult — never raises, never
    fabricates data.
    """

    GRAPH_NAME = property(lambda self: get_settings().tigergraph_graph_name)

    def __init__(self) -> None:
        # Initialise state immediately so the object is always safe to call
        self._session: _MCPSession | None = None
        self._available: bool = False

    # ── Session lifecycle ─────────────────────────────────────────────────────

    async def __aenter__(self) -> "MCPInvestigationClient":
        self._session = _MCPSession()
        try:
            await self._session.open()
            self._available = True
            logger.info(
                "MCP session opened — %d tools available",
                len(self._session.tools),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("MCP unavailable: %s", exc)
            self._session = None
            self._available = False
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._session:
            await self._session.close()
            self._session = None

    @property
    def available(self) -> bool:
        return self._available and self._session is not None

    @property
    def tool_count(self) -> int:
        return len(self._session.tools) if self._session else 0

    @property
    def tool_names(self) -> list[str]:
        return self._session.tool_names if self._session else []

    # ── Internal call wrapper ─────────────────────────────────────────────────

    async def _call(
        self,
        tool_name: str,
        arguments: dict,
        query_name: str = "",
        entity_ids: list[str] | None = None,
    ) -> ProvenanceMCPResult:
        """Execute one MCP tool and return a ProvenanceMCPResult."""
        result = ProvenanceMCPResult(
            tool_name=tool_name,
            query_name=query_name,
            entity_ids=entity_ids or [],
        )
        started = time.monotonic()
        result.started_at = datetime.now(timezone.utc).isoformat()
        if not self.available:
            result.error = "MCP session not available"
            result.completed_at = datetime.now(timezone.utc).isoformat()
            result.duration_ms = round((time.monotonic() - started) * 1000, 2)
            return result

        try:
            raw = await self._session.call_tool(tool_name, arguments)
            result.raw_data = raw
            result.success = raw.get("success", True)
            # MCP wraps results in {"success":true, "data":{...}, "summary":...}
            # Expose data directly so callers don't have to unwrap
            inner = raw.get("data", raw)
            result.evidence = inner
            if not result.success:
                result.error = raw.get("error", "tool returned success=false")
        except Exception as exc:  # noqa: BLE001
            result.error = str(exc)
            logger.warning("MCP tool %s failed: %s", tool_name, exc)
        result.completed_at = datetime.now(timezone.utc).isoformat()
        result.duration_ms = round((time.monotonic() - started) * 1000, 2)

        return result

    # ── Investigation tools ───────────────────────────────────────────────────

    async def get_transaction(self, txn_id: str) -> ProvenanceMCPResult:
        """Run Transaction_Fraud for a specific transaction."""
        return await self._call(
            "tigergraph__run_installed_query",
            {
                "graph_name": get_settings().tigergraph_graph_name,
                "query_name": "Transaction_Fraud",
                "params": {"txn": (txn_id,)},   # 1-tuple = VERTEX<T> format
            },
            query_name="Transaction_Fraud",
            entity_ids=[txn_id],
        )

    async def get_transaction_context(self, txn_id: str) -> ProvenanceMCPResult:
        """Run get_transaction_context for full neighbourhood."""
        return await self._call(
            "tigergraph__run_installed_query",
            {
                "graph_name": get_settings().tigergraph_graph_name,
                "query_name": "get_transaction_context",
                "params": {"txn": (txn_id,)},
            },
            query_name="get_transaction_context",
            entity_ids=[txn_id],
        )

    async def get_customer_history(
        self, customer_id: str, limit: int = 50
    ) -> ProvenanceMCPResult:
        """Run get_customer_history."""
        return await self._call(
            "tigergraph__run_installed_query",
            {
                "graph_name": get_settings().tigergraph_graph_name,
                "query_name": "get_customer_history",
                "params": {"customer": (customer_id,), "lim": limit},
            },
            query_name="get_customer_history",
            entity_ids=[customer_id],
        )

    async def get_connected_cards(self, card_id: str) -> ProvenanceMCPResult:
        """Run find_connected_cards."""
        return await self._call(
            "tigergraph__run_installed_query",
            {
                "graph_name": get_settings().tigergraph_graph_name,
                "query_name": "find_connected_cards",
                "params": {"card": (card_id,)},
            },
            query_name="find_connected_cards",
            entity_ids=[card_id],
        )

    async def get_shared_identity(self, txn_id: str) -> ProvenanceMCPResult:
        """Run find_shared_identity."""
        return await self._call(
            "tigergraph__run_installed_query",
            {
                "graph_name": get_settings().tigergraph_graph_name,
                "query_name": "find_shared_identity",
                "params": {"txn": (txn_id,)},
            },
            query_name="find_shared_identity",
            entity_ids=[txn_id],
        )

    async def get_prior_fraud_cases(
        self, customer_id: str, card_id: str
    ) -> ProvenanceMCPResult:
        """Run find_prior_fraud_cases."""
        return await self._call(
            "tigergraph__run_installed_query",
            {
                "graph_name": get_settings().tigergraph_graph_name,
                "query_name": "find_prior_fraud_cases",
                "params": {"customer": (customer_id,), "card": (card_id,)},
            },
            query_name="find_prior_fraud_cases",
            entity_ids=[customer_id, card_id],
        )

    async def get_behavioral_anomalies(self, card_id: str) -> ProvenanceMCPResult:
        """Run find_behavioral_anomalies."""
        return await self._call(
            "tigergraph__run_installed_query",
            {
                "graph_name": get_settings().tigergraph_graph_name,
                "query_name": "find_behavioral_anomalies",
                "params": {"card": (card_id,)},
            },
            query_name="find_behavioral_anomalies",
            entity_ids=[card_id],
        )

    async def get_card_transactions(
        self, card_id: str, limit: int = 50
    ) -> ProvenanceMCPResult:
        """Run find_card_transactions."""
        return await self._call(
            "tigergraph__run_installed_query",
            {
                "graph_name": get_settings().tigergraph_graph_name,
                "query_name": "find_card_transactions",
                "params": {"card": (card_id,), "lim": limit},
            },
            query_name="find_card_transactions",
            entity_ids=[card_id],
        )

    async def get_graph_schema(self) -> ProvenanceMCPResult:
        """Get FraudCaseGraph schema via MCP."""
        result = await self._call(
            "tigergraph__get_graph_schema",
            {"graph_name": get_settings().tigergraph_graph_name},
            query_name="get_graph_schema",
        )
        # Normalise: ensure VertexTypes are accessible at evidence["schema"]
        if result.success and isinstance(result.evidence, dict):
            raw_data = result.raw_data or {}
            # MCP returns {"success":true,"data":{"graph_name":...,"schema":{...}}}
            data = raw_data.get("data", raw_data)
            schema = data.get("schema", data)
            result.evidence = {"schema": schema, "graph_name": data.get("graph_name", "")}
        return result

    async def list_installed_queries(self) -> list[str]:
        """Return list of installed query names via MCP."""
        if not self.available:
            return []
        result = await self._call(
            "tigergraph__show_graph_details",
            {"graph_name": get_settings().tigergraph_graph_name},
            query_name="show_graph_details",
        )
        if result.success:
            details = result.evidence
            queries = details.get("queries", [])
            return [q.get("name", q) if isinstance(q, dict) else str(q)
                    for q in queries]
        return []

    # ── Bulk retrieval ────────────────────────────────────────────────────────

    async def retrieve_investigation_evidence(
        self,
        txn_id: str,
        card_id: str,
        customer_id: str,
    ) -> tuple[list[ProvenanceMCPResult], list[str]]:
        """
        Run all investigation-relevant queries.
        Transaction_Fraud runs first (most critical), rest run in parallel.
        Returns (results, queries_executed).
        """
        results: list[ProvenanceMCPResult] = []
        queries: list[str] = []

        # Transaction_Fraud must run first — it's the anchor query
        r_txn = await self.get_transaction(txn_id)
        results.append(r_txn)
        if r_txn.success:
            queries.append(r_txn.query_name)

        # Rest can run in parallel
        rest = await asyncio.gather(
            self.get_customer_history(customer_id),
            self.get_connected_cards(card_id),
            self.get_shared_identity(txn_id),
            self.get_prior_fraud_cases(customer_id, card_id),
            self.get_behavioral_anomalies(card_id),
            self.get_card_transactions(card_id),
            return_exceptions=True,
        )
        for r in rest:
            if isinstance(r, Exception):
                logger.warning("MCP parallel call failed: %s", r)
            elif isinstance(r, ProvenanceMCPResult):
                results.append(r)
                if r.success and r.query_name:
                    queries.append(r.query_name)

        return results, queries


# ── Module-level factory ──────────────────────────────────────────────────────

def get_mcp_investigation_client() -> MCPInvestigationClient:
    """Return a fresh client for use as an async context manager."""
    return MCPInvestigationClient()


# ── Backward-compat singleton (legacy MCPClient kept for API compatibility) ───

class MCPClient:
    """Legacy shim — kept so existing imports don't break."""

    def __init__(self) -> None:
        self.base_url = get_settings().tigergraph_mcp_url

    async def ping(self) -> bool:
        return False  # Legacy HTTP server not used

    async def list_tools(self) -> list[dict]:
        return []

    async def close(self) -> None:
        pass


_mcp_instance: MCPClient | None = None


def get_mcp_client() -> MCPClient:
    global _mcp_instance
    if _mcp_instance is None:
        _mcp_instance = MCPClient()
    return _mcp_instance
