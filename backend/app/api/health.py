from fastapi import APIRouter
from ..tigergraph.client import get_client
from ..tigergraph.mcp_client import get_mcp_investigation_client
from ..data_layer import get_data_layer
from ..config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    dl = get_data_layer()
    tg_ok = False
    mcp_ok = False
    mcp_health = {
        "available": False,
        "tool_count": 0,
        "tools": [],
        "required_tools": [],
        "missing_required_tools": [],
        "error": "MCP session did not open",
        "ready": False,
    }
    try:
        tg_ok = await get_client().ping()
    except Exception:
        pass
    try:
        async with get_mcp_investigation_client() as mcp:
            mcp_health = await mcp.health_check()
            mcp_ok = mcp_health["ready"]
    except Exception:
        pass
    settings = get_settings()
    return {
        "status": "ok" if tg_ok and mcp_ok else "degraded",
        "tigergraph": "connected" if tg_ok else "unavailable",
        "mcp": {
            "status": "connected" if mcp_ok else "unavailable",
            **mcp_health,
        },
        "llm": {
            "provider": settings.llm_provider,
            "model": settings.llm_model,
            "configured": bool(settings.llm_api_key),
        },
        "data_loaded": {
            "transactions": len(dl.transactions),
            "identity": len(dl.identity),
            "closed_cases": len(dl.closed_cases),
            "case_pack": len(dl.case_pack),
        },
    }
