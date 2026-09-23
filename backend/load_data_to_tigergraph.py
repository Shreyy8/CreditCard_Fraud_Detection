"""
Bulk load CSV dataset (DataLayer) into TigerGraph Cloud.

Usage:
    python backend/load_data_to_tigergraph.py
"""

from __future__ import annotations

import sys
import logging
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.config import get_settings
from backend.app.data_layer import get_data_layer
from backend.app.tigergraph.client import get_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def load_dataset_to_tigergraph(batch_size: int = 1000):
    settings = get_settings()
    logger.info("Initializing DataLayer...")
    dl = get_data_layer()

    logger.info("Connecting to TigerGraph (%s)...", settings.tigergraph_host)
    client = get_client()
    client._ensure_conn()
    conn = client._conn

    # 1. Upsert Identity Vertices
    logger.info("Upserting %d Identity records...", len(dl.identity))
    identity_vertices = []
    for tid, row in dl.identity.items():
        identity_vertices.append((
            tid,
            {
                "device_info": row.get("DeviceInfo", ""),
                "os": row.get("id_30", ""),
                "browser": row.get("id_31", ""),
                "screen": row.get("id_33", ""),
            }
        ))
    
    for i in range(0, len(identity_vertices), batch_size):
        batch = identity_vertices[i : i + batch_size]
        for vid, attrs in batch:
            conn.upsertVertex("Identity", vid, attributes=attrs)
        logger.info("  Uploaded identity batch %d/%d", min(i + batch_size, len(identity_vertices)), len(identity_vertices))

    # 2. Upsert Customer, Card, Transaction Vertices and Edges
    logger.info("Upserting Transactions (%d total)...", len(dl.transactions))
    txns = list(dl.transactions.items())
    
    for i in range(0, len(txns), batch_size):
        batch = txns[i : i + batch_size]
        for tid, row in batch:
            cust_id = row.get("customer_id", "")
            amt = float(row.get("TransactionAmt", 0.0) or 0.0)
            ts = row.get("ts", "")
            channel = row.get("channel", "")
            risk_score = float(row.get("risk_score", 0.0) or 0.0)

            # Upsert Transaction
            conn.upsertVertex(
                "Transaction",
                str(tid),
                attributes={
                    "transaction_amt": amt,
                    "ts": ts,
                    "channel": channel,
                    "risk_score": risk_score,
                }
            )

            # Upsert Customer & Edge
            if cust_id:
                conn.upsertVertex("Customer", cust_id, attributes={})
                conn.upsertEdge("Transaction", str(tid), "transaction_belongs_to_customer", "Customer", cust_id)
                # Card ID heuristic
                card_id = f"{cust_id}-K1"
                conn.upsertVertex("Card", card_id, attributes={})
                conn.upsertEdge("Transaction", str(tid), "transaction_belongs_to_card", "Card", card_id)

            # Edge to Identity if present
            if tid in dl.identity:
                conn.upsertEdge("Transaction", str(tid), "transaction_has_identity", "Identity", str(tid))

        logger.info("  Processed transactions %d/%d", min(i + batch_size, len(txns)), len(txns))

    logger.info("Data loading complete! All vertices and edges loaded into TigerGraph.")


if __name__ == "__main__":
    load_dataset_to_tigergraph()
