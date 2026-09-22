"""
Install GSQL queries into TigerGraph.

Run from backend/:
    python install_queries.py

Installs every CREATE OR REPLACE QUERY from gsql/investigation_queries.gsql
into the live FraudCaseGraph on Savanna.
"""

from __future__ import annotations

import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.config import get_settings
get_settings.cache_clear()
settings = get_settings()


def get_conn():
    import pyTigerGraph as tg
    host = settings.tigergraph_host
    conn = tg.TigerGraphConnection(
        host=host,
        graphname=settings.tigergraph_graph_name,
        gsqlSecret=settings.tigergraph_secret,
        tgCloud="tgcloud.io" in host.lower(),
    )
    res = conn.getToken(settings.tigergraph_secret)
    conn.apiToken = res[0] if isinstance(res, (tuple, list)) else str(res)
    return conn


def install_all() -> int:
    print("Installing GSQL queries into", settings.tigergraph_graph_name)
    conn = get_conn()

    gsql_file = Path(__file__).parent / "gsql" / "investigation_queries.gsql"
    full_gsql = gsql_file.read_text(encoding="utf-8")

    # Strip comment blocks and USE GRAPH line — pyTigerGraph adds graph context
    lines = []
    in_block_comment = False
    for line in full_gsql.splitlines():
        stripped = line.strip()
        if stripped.startswith("/*"):
            in_block_comment = True
        if in_block_comment:
            if "*/" in stripped:
                in_block_comment = False
            continue
        if stripped.startswith("//") or stripped.upper().startswith("USE GRAPH"):
            continue
        lines.append(line)

    clean_gsql = "\n".join(lines)

    # Split into individual CREATE OR REPLACE QUERY blocks
    pattern = re.compile(
        r'(CREATE\s+OR\s+REPLACE\s+QUERY\s+\w+.*?(?=CREATE\s+OR\s+REPLACE\s+QUERY|\Z))',
        re.IGNORECASE | re.DOTALL,
    )
    blocks = pattern.findall(clean_gsql)
    print(f"Found {len(blocks)} query block(s)")

    installed = 0
    failed    = 0

    for block in blocks:
        block = block.strip()
        if not block:
            continue
        # Extract query name for logging
        m = re.search(r'QUERY\s+(\w+)', block, re.IGNORECASE)
        name = m.group(1) if m else "unknown"

        print(f"\n  Installing: {name} ...", end=" ", flush=True)
        try:
            result = conn.gsql(
                f"USE GRAPH {settings.tigergraph_graph_name}\n"
                f"{block}\n"
                f"INSTALL QUERY {name}"
            )
            if "error" in str(result).lower() and "already" not in str(result).lower():
                print(f"FAIL\n    {str(result)[:200]}")
                failed += 1
            else:
                print(f"PASS")
                installed += 1
        except Exception as exc:
            print(f"FAIL\n    {exc}")
            failed += 1

    print(f"\n{'─'*50}")
    print(f"Installed: {installed}   Failed: {failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(install_all())
