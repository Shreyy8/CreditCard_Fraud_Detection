"""Central configuration — reads from environment / .env file."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# .env lives at the project root (one level above backend/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── TigerGraph data-plane (workspace) ─────────────────────────────────────
    # e.g. https://abc123.i.tgcloud.io  (auto-discovered via Savanna API if blank)
    tigergraph_host: str = ""
    tigergraph_graph_name: str = "FraudCaseGraph"
    tigergraph_username: str = "tigergraph"
    tigergraph_password: str = ""
    # GSQL secret for token generation (data-plane auth)
    tigergraph_secret: str = ""
    # Pre-issued bearer token (optional — takes priority over secret)
    tigergraph_token: str = ""

    # ── TigerGraph Savanna control-plane ──────────────────────────────────────
    # API key for api.tgcloud.io (x-api-key header)
    # Accepts both spellings — .env currently has the typo TIGERGRAPGH_SAVANNA
    tigergraph_savanna: str = ""
    tigergrapgh_savanna: str = ""   # tolerates the typo present in .env

    # ── TigerGraph MCP ────────────────────────────────────────────────────────
    tigergraph_mcp_url: str = "http://localhost:8765"
    # Official tigergraph-mcp is stdio-based; disable only for environments
    # that intentionally validate the direct graph path in isolation.
    mcp_enabled: bool = True
    allow_simulated_evidence: bool = True

    # ── LLM ───────────────────────────────────────────────────────────────────
    llm_provider: str = "openai"
    llm_api_key: str = ""
    llm_backup_api_key: str = ""
    llm_model: str = "gpt-4o"
    llm_base_url: str = ""
    llm_timeout_s: float = 30.0

    # ── GraphRAG ──────────────────────────────────────────────────────────────
    graphrag_provider: str = "tigergraph"
    graphrag_embedding_model: str = "text-embedding-3-small"

    # ── Persistence ───────────────────────────────────────────────────────────
    database_url: str = "sqlite:///./fraud_cases.db"

    # ── App ───────────────────────────────────────────────────────────────────
    app_env: str = "development"
    log_level: str = "INFO"
    secret_key: str = "dev-secret-key"

    # ── Datasets ──────────────────────────────────────────────────────────────
    transactions_csv: str = "DataSet/transactions.csv"
    identity_csv: str = "DataSet/identity.csv"
    closed_cases_csv: str = "DataSet/closed_cases_history.csv"
    case_pack_csv: str = "DataSet/case_pack.csv"

    @property
    def savanna_api_key(self) -> str:
        """Return the Savanna API key — works with both spellings in .env."""
        return self.tigergraph_savanna or self.tigergrapgh_savanna


@lru_cache
def get_settings() -> Settings:
    return Settings()
