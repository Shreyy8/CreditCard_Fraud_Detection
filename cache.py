"""
agent/tools/cache.py

Two speed levers for the graph tool layer:

1. `@graph_cache` - memoizes read-only GSQL tool calls keyed on their
   arguments plus an `as_of` cursor. Safe because, within one benchmark run,
   the graph only grows (agent write-backs), so a query issued with the same
   `as_of` date always returns the same answer. Caching is keyed per-process;
   swap `_MemoryCache` for Redis/sqlite if you need it to survive restarts or
   be shared across parallel workers.

2. `fetch_case_evidence_parallel` - issues the handful of independent
   first-round graph queries for a case concurrently instead of sequentially,
   since none of them depend on each other's output. This is a pure
   wall-clock win: graph + LLM I/O dominates per-case latency, not CPU.

Both are opt-in wrappers around your existing MCP tool client
(`agent/tools/mcp_client.py`) - they do not change what the tools return,
only how often and how fast they're called.
"""

from __future__ import annotations

import functools
import hashlib
import json
import threading
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. Memoization
# ---------------------------------------------------------------------------

class _MemoryCache:
    """Simple thread-safe in-process cache. Swap for Redis/sqlite if needed."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._store.get(key)
        if entry is None:
            self.misses += 1
            return None
        self.hits += 1
        return entry[1]

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._store[key] = (time.time(), value)

    def stats(self) -> dict[str, int]:
        return {"hits": self.hits, "misses": self.misses, "size": len(self._store)}

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


_cache = _MemoryCache()


def _make_key(fn_name: str, args: tuple, kwargs: dict) -> str:
    payload = json.dumps({"fn": fn_name, "args": args, "kwargs": kwargs}, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def graph_cache(fn: Callable) -> Callable:
    """
    Decorator for read-only graph tool functions. Requires callers to pass
    `as_of` explicitly (the case's `opened_at`, or a closed case's
    `closed_at`) so cache entries are never reused across different temporal
    cutoffs - this also happens to be required by the no-leakage rule
    (section 11 of the README), so the cache key doubles as an enforcement
    point: forgetting `as_of` is a bug, not just a missed cache hit.
    """

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if "as_of" not in kwargs:
            raise TypeError(
                f"{fn.__name__} must be called with an explicit as_of= cutoff "
                "(required for both caching and leakage prevention)"
            )
        key = _make_key(fn.__name__, args, kwargs)
        cached = _cache.get(key)
        if cached is not None:
            logger.debug("cache hit: %s(%s)", fn.__name__, kwargs)
            return cached
        result = fn(*args, **kwargs)
        _cache.set(key, result)
        return result

    return wrapper


def cache_stats() -> dict[str, int]:
    return _cache.stats()


def clear_cache() -> None:
    _cache.clear()


# ---------------------------------------------------------------------------
# 2. Parallel fetch of independent first-round evidence
# ---------------------------------------------------------------------------

def fetch_case_evidence_parallel(
    tools: dict[str, Callable],
    card_id: str,
    as_of: str,
    window_hours: int = 24,
    max_workers: int = 6,
) -> dict[str, Any]:
    """
    Issues the independent first-round graph queries concurrently.

    `tools` maps query name -> callable, e.g. the MCP-wrapped functions:
        {
          "card_window": card_window,
          "card_baseline": card_baseline,
          "device_neighbors": device_neighbors,
          "region_cluster": region_cluster,
          "email_neighbors": email_neighbors,
          "similar_closed_cases": similar_closed_cases,
        }
    Each callable must accept (card_id=..., as_of=..., ...) and be
    independently safe to call before any other result is known - this is
    true for all first-round evidence queries, but NOT for anything that
    depends on a prior query's output (e.g. `recurring_pattern` needs a
    candidate txn_id from `card_window` first, so don't include it here).

    Returns {query_name: result_or_exception}. A failed query does not abort
    the others - the caller decides whether a missing evidence source is
    fatal (see note below).
    """
    results: dict[str, Any] = {}
    errors: dict[str, Exception] = {}

    def _run(name: str, fn: Callable) -> tuple[str, Any]:
        t0 = time.time()
        try:
            out = fn(card_id=card_id, as_of=as_of, window_hours=window_hours)
            logger.debug("%s took %.2fs", name, time.time() - t0)
            return name, out
        except Exception as e:  # noqa: BLE001
            logger.warning("%s failed: %s", name, e)
            raise

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_run, name, fn): name for name, fn in tools.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                _, out = future.result()
                results[name] = out
            except Exception as e:  # noqa: BLE001
                errors[name] = e

    if errors:
        # Evidence gathering should degrade, not crash: a missing
        # device_neighbors result, say, means "treat as no shared device
        # found" rather than aborting the whole case. Log loudly so it shows
        # up in the case's tool_calls/explanation, but don't raise.
        for name, err in errors.items():
            results[name] = {"error": str(err), "degraded": True}
        logger.warning("evidence gathering degraded for %d/%d tools: %s",
                        len(errors), len(tools), list(errors))

    return results
