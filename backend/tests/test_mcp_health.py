"""Unit tests for the MCP readiness contract."""

import asyncio
from types import SimpleNamespace

from app.tigergraph.mcp_client import MCPInvestigationClient


def test_mcp_health_reports_unavailable_startup_error():
    client = MCPInvestigationClient()
    client._startup_error = "server executable not found"

    health = asyncio.run(client.health_check())

    assert health["available"] is False
    assert health["ready"] is False
    assert health["tool_count"] == 0
    assert health["error"] == "server executable not found"
    assert set(health["missing_required_tools"]) == set(client.REQUIRED_TOOLS)


def test_mcp_health_reports_required_tools():
    client = MCPInvestigationClient()
    client._available = True
    client._session = SimpleNamespace(
        tools=[SimpleNamespace(name=name) for name in client.REQUIRED_TOOLS],
        tool_names=list(client.REQUIRED_TOOLS),
    )

    health = asyncio.run(client.health_check())

    assert health["available"] is True
    assert health["ready"] is True
    assert health["tool_count"] == 3
    assert health["missing_required_tools"] == []