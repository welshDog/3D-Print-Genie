"""Print Genie glue-service settings (env-driven). Secrets come from .env only.

Env is read in __init__ (not at class definition) so tests can monkeypatch the environment
and call get_settings.cache_clear() to pick up changes.
"""
from __future__ import annotations

import os
from functools import lru_cache


class Settings:
    def __init__(self) -> None:
        # Alerts
        self.discord_webhook_url: str = os.getenv("DISCORD_WEBHOOK_URL", "")

        # Supabase
        self.supabase_url: str = os.getenv("SUPABASE_URL", "")
        self.supabase_service_role_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

        # Meshy preflight
        self.meshy_api_key: str = os.getenv("MESHY_API_KEY", "")
        self.meshy_base_url: str = os.getenv("MESHY_BASE_URL", "https://api.meshy.ai")

        # Economy
        self.core_url: str = os.getenv("HYPERCODE_CORE_URL", "http://host.docker.internal:8000")
        self.award_path: str = os.getenv("ECONOMY_AWARD_PATH", "/economy/award-dev-xp")
        self.owner_discord_id: str = os.getenv("OWNER_DISCORD_ID", "418075243404591106")
        self.xp_per_success: int = int(os.getenv("XP_PER_SUCCESS", "50"))

        # Service
        self.webhook_secret: str = os.getenv("PRINTGENIE_WEBHOOK_SECRET", "change-me")
        self.printguard_base_url: str = os.getenv("PRINTGUARD_BASE_URL", "http://printguard:8000")

        # Phase 4 (off by default)
        self.auto_pause_enabled: bool = (
            os.getenv("AUTO_PAUSE_ENABLED", "false").lower() == "true"
        )

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_role_key)

    @property
    def meshy_configured(self) -> bool:
        return bool(self.meshy_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
