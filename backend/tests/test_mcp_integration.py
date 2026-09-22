"""
TigerGraph MCP integration tests.

Hard-failing — no mock/fake result is accepted as PASS.
Each test opens its own MCP session so there are no event-loop conflicts.

Run all:       pytest tests/test_mcp_integration.py -v
Run fast only: pytest tests/test_mcp_integration.py -v -k "not bulk and not hhg004"
Skip MCP:      pytest tests/ -v --ignore=tests/test_mcp_integration.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

# ── Known real data ───────────────────────────────────────────────────────────
HHG004_TXN_ID  = "3583227"
HHG004_CARD_ID = "C08106-K1"
HHG004_CUST_ID = "C08106"
HHG004_AMOUNT  = 128.33
KNOWN_GRAPH    = "FraudCaseGraph"
KNOWN_QUERY    = "Transaction_Fraud"


# ── Helper: run one MCP call inside a fresh session ──────────────────────────

async def _with_mcp(coro_factory):
    """Open MCP session, run coro_factory(client), close session."""
    from app.tigergraph.mcp_client import MCPInvestigationClient
    async with MCPInvestigationClient() as client:
        return await coro_factory(client)


# ══════════════════════════════════════════════════════════════════════════════
# 1. Server reachability & tool discovery
# ══════════════════════════════════════════════════════════════════════════════

class TestMCPServerReachability:

    def test_mcp_session_opens(self):
        """MCP subprocess must start and initialise — real failure if it can't."""
        async def _test():
            from app.tigergraph.mcp_client import MCPInvestigationClient
            async with MCPInvestigationClient() as client:
                assert client.available, (
                    "MCP session did not open. "
                    "Ensure 'tigergraph-mcp' is installed and TG_* vars are set."
                )
                return client.tool_count
        count = asyncio.run(_test())
        assert count >= 10

    def test_tools_discovered_count(self):
        """At least 10 real tools from the official package."""
        async def _test():
            from app.tigergraph.mcp_client import MCPInvestigationClient
            async with MCPInvestigationClient() as client:
                return client.tool_count, client.tool_names
        count, names = asyncio.run(_test())
        assert count >= 10, f"Expected ≥10 tools, got {count}"

    def test_core_investigation_tools_present(self):
        """The 3 tools we depend on must be present."""
        async def _test():
            from app.tigergraph.mcp_client import MCPInvestigationClient
            async with MCPInvestigationClient() as client:
                return client.tool_names
        names = asyncio.run(_test())
        for tool in [
            "tigergraph__run_installed_query",
            "tigergraph__get_graph_schema",
            "tigergraph__list_graphs",
        ]:
            assert tool in names, f"Required tool missing: {tool}"

    def test_all_tools_use_official_prefix(self):
        """Every tool must use the tigergraph__ prefix (not a fake/mock tool)."""
        async def _test():
            from app.tigergraph.mcp_client import MCPInvestigationClient
            async with MCPInvestigationClient() as client:
                return client.tool_names
        names = asyncio.run(_test())
        for name in names:
            assert name.startswith("tigergraph__"), (
                f"Unexpected tool name (not official): {name}"
            )


# ══════════════════════════════════════════════════════════════════════════════
# 2. Graph introspection
# ══════════════════════════════════════════════════════════════════════════════

class TestMCPGraphIntrospection:

    def test_list_graphs_includes_fraud_case_graph(self):
        """tigergraph__list_graphs must return FraudCaseGraph."""
        async def _test():
            from app.tigergraph.mcp_client import MCPInvestigationClient
            async with MCPInvestigationClient() as client:
                return await client._call("tigergraph__list_graphs", {})
        result = asyncio.run(_test())
        assert result.success, f"list_graphs failed: {result.error}"
        graphs = result.evidence.get("graphs", [])
        assert KNOWN_GRAPH in graphs, f"FraudCaseGraph not in: {graphs}"
        assert result.source_type == "tigergraph_mcp"
        assert result.retrieved_at

    def test_schema_has_real_vertex_types(self):
        """Schema must contain the verified vertex types."""
        async def _test():
            from app.tigergraph.mcp_client import MCPInvestigationClient
            async with MCPInvestigationClient() as client:
                return await client.get_graph_schema()
        result = asyncio.run(_test())
        assert result.success, f"get_graph_schema failed: {result.error}"
        schema = result.evidence.get("schema", {})
        vtypes = [v.get("Name", "") for v in schema.get("VertexTypes", [])]
        for vt in ["Transaction", "Customer", "Card", "FraudCase"]:
            assert vt in vtypes, f"Vertex type missing: {vt}, got {vtypes}"
        assert result.source_type == "tigergraph_mcp"


# ══════════════════════════════════════════════════════════════════════════════
# 3. Transaction_Fraud real data
# ══════════════════════════════════════════════════════════════════════════════

class TestMCPTransactionFraud:

    def test_transaction_fraud_succeeds(self):
        """Transaction_Fraud(3583227) must return success=True."""
        async def _test():
            from app.tigergraph.mcp_client import MCPInvestigationClient
            async with MCPInvestigationClient() as client:
                return await client.get_transaction(HHG004_TXN_ID)
        result = asyncio.run(_test())
        assert result.success, (
            f"Transaction_Fraud FAILED: {result.error}\n"
            "This is a real failure — mock not accepted."
        )

    def test_transaction_amount_matches_known(self):
        """transaction_amt must be $128.33 (from the real dataset)."""
        async def _test():
            from app.tigergraph.mcp_client import MCPInvestigationClient
            async with MCPInvestigationClient() as client:
                return await client.get_transaction(HHG004_TXN_ID)
        result = asyncio.run(_test())
        assert result.success
        query_result = result.evidence.get("result", [])
        txn_vertices = []
        for block in query_result:
            if isinstance(block, dict):
                txn_vertices.extend(block.get("T", []))
        assert txn_vertices, "No transaction vertex returned"
        amt = txn_vertices[0].get("attributes", {}).get("transaction_amt", 0)
        assert abs(float(amt) - HHG004_AMOUNT) < 0.01, (
            f"Amount mismatch: got {amt}, expected {HHG004_AMOUNT}"
        )

    def test_transaction_vertex_id_correct(self):
        """v_id must match the requested transaction ID."""
        async def _test():
            from app.tigergraph.mcp_client import MCPInvestigationClient
            async with MCPInvestigationClient() as client:
                return await client.get_transaction(HHG004_TXN_ID)
        result = asyncio.run(_test())
        assert result.success
        query_result = result.evidence.get("result", [])
        txn_vertices = []
        for block in query_result:
            if isinstance(block, dict):
                txn_vertices.extend(block.get("T", []))
        assert txn_vertices
        v_id = str(txn_vertices[0].get("v_id", ""))
        assert v_id == HHG004_TXN_ID

    def test_result_provenance_complete(self):
        """Every MCP result must have full provenance."""
        async def _test():
            from app.tigergraph.mcp_client import MCPInvestigationClient
            async with MCPInvestigationClient() as client:
                return await client.get_transaction(HHG004_TXN_ID)
        result = asyncio.run(_test())
        assert result.source_type == "tigergraph_mcp"
        assert result.tool_name == "tigergraph__run_installed_query"
        assert result.query_name == KNOWN_QUERY
        assert HHG004_TXN_ID in result.entity_ids
        assert result.retrieved_at


# ══════════════════════════════════════════════════════════════════════════════
# 4. Prior fraud cases
# ══════════════════════════════════════════════════════════════════════════════

class TestMCPPriorCases:

    def test_prior_cases_query_succeeds(self):
        """find_prior_fraud_cases for C08106 must succeed."""
        async def _test():
            from app.tigergraph.mcp_client import MCPInvestigationClient
            async with MCPInvestigationClient() as client:
                return await client.get_prior_fraud_cases(
                    HHG004_CUST_ID, HHG004_CARD_ID
                )
        result = asyncio.run(_test())
        assert result.success, f"find_prior_fraud_cases failed: {result.error}"
        assert result.source_type == "tigergraph_mcp"
        assert result.query_name == "find_prior_fraud_cases"

    def test_returned_case_ids_are_real_format(self):
        """Any returned case IDs must be real CC-/HHG- format, not fabricated."""
        async def _test():
            from app.tigergraph.mcp_client import MCPInvestigationClient
            async with MCPInvestigationClient() as client:
                return await client.get_prior_fraud_cases(
                    HHG004_CUST_ID, HHG004_CARD_ID
                )
        result = asyncio.run(_test())
        assert result.success
        query_result = result.evidence.get("result", [])
        for block in query_result:
            if isinstance(block, dict):
                for vertex in block.get("cases", []):
                    if isinstance(vertex, dict):
                        cid = vertex.get("v_id", "")
                        assert cid.startswith(("CC-", "HHG-")), (
                            f"Unexpected case ID: '{cid}' — may be fabricated"
                        )


# ══════════════════════════════════════════════════════════════════════════════
# 5. Failure behaviour
# ══════════════════════════════════════════════════════════════════════════════

class TestMCPFailureBehaviour:

    def test_unavailable_session_returns_failed_result_not_raises(self):
        """Calling without opening session must return failure, not raise."""
        from app.tigergraph.mcp_client import MCPInvestigationClient
        client = MCPInvestigationClient()
        result = asyncio.run(client.get_transaction("FAKE"))
        assert result is not None
        assert result.success is False
        assert result.error  # must say why

    def test_unavailable_session_never_claims_success(self):
        """An unopened client must NEVER report success=True."""
        from app.tigergraph.mcp_client import MCPInvestigationClient
        client = MCPInvestigationClient()
        result = asyncio.run(client.get_transaction("FAKE"))
        assert result.success is False, (
            "Unopened client returned success=True — fabricated result"
        )

    def test_provenance_still_set_on_failure(self):
        """Even failed results must carry source_type provenance."""
        from app.tigergraph.mcp_client import MCPInvestigationClient
        client = MCPInvestigationClient()
        result = asyncio.run(client.get_transaction("FAKE"))
        assert result.source_type == "tigergraph_mcp"
        assert result.retrieved_at


# ══════════════════════════════════════════════════════════════════════════════
# 6. HHG-004 via MCP
# ══════════════════════════════════════════════════════════════════════════════

class TestHHG004ViaMCP:

    def test_hhg004_transaction_via_mcp(self):
        """Transaction 3583227 retrieved via MCP must contain real attributes."""
        async def _test():
            from app.tigergraph.mcp_client import MCPInvestigationClient
            async with MCPInvestigationClient() as client:
                return await client.get_transaction(HHG004_TXN_ID)
        result = asyncio.run(_test())
        assert result.success
        assert result.source_type == "tigergraph_mcp"

    def test_hhg004_no_fabricated_entity_ids(self):
        """No entity_id in MCP results for HHG-004 should be a fabrication marker."""
        async def _test():
            from app.tigergraph.mcp_client import MCPInvestigationClient
            async with MCPInvestigationClient() as client:
                return await client.get_transaction(HHG004_TXN_ID)
        result = asyncio.run(_test())
        assert result.success
        forbidden = {"FABRICATED", "INVENTED", "MOCK", "undefined"}
        for eid in result.entity_ids:
            assert eid not in forbidden

    def test_hhg004_bulk_mcp_retrieval(self):
        """Bulk MCP retrieval must return at least Transaction_Fraud evidence."""
        async def _test():
            from app.tigergraph.mcp_client import MCPInvestigationClient
            async with MCPInvestigationClient() as client:
                return await client.retrieve_investigation_evidence(
                    HHG004_TXN_ID, HHG004_CARD_ID, HHG004_CUST_ID
                )
        results, queries = asyncio.run(_test())
        assert len(results) >= 1, f"No successful MCP results. queries={queries}"
        assert KNOWN_QUERY in queries, f"Transaction_Fraud not in: {queries}"
        assert all(r.source_type == "tigergraph_mcp" for r in results)
        assert all(r.retrieved_at for r in results)
