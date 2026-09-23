from .cases import router as cases_router
from .health import router as health_router
from .investigations import router as investigations_router
from .policy import router as policy_router

__all__ = ["cases_router", "health_router", "investigations_router", "policy_router"]
