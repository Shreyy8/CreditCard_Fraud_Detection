"""Install the repository-owned FraudCaseGraph schema into Savanna."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.config import get_settings


def main() -> int:
    import pyTigerGraph as tg

    settings = get_settings()
    if not settings.tigergraph_host or settings.tigergraph_host.startswith("https://your-"):
        raise SystemExit("Set TIGERGRAPH_HOST in .env before installing the schema")
    connection = tg.TigerGraphConnection(
        host=settings.tigergraph_host,
        graphname=settings.tigergraph_graph_name,
        gsqlSecret=settings.tigergraph_secret,
        username=settings.tigergraph_username,
        password=settings.tigergraph_password,
        tgCloud="tgcloud.io" in settings.tigergraph_host.lower(),
    )
    if settings.tigergraph_token:
        connection.apiToken = settings.tigergraph_token
    elif settings.tigergraph_secret:
        token = connection.getToken(settings.tigergraph_secret)
        connection.apiToken = token[0] if isinstance(token, (tuple, list)) else str(token)
    schema = (Path(__file__).parent / "gsql" / "schema.gsql").read_text(encoding="utf-8")
    result = connection.gsql(schema)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())