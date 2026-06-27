"""Print Genie glue-service settings (env-driven). Secrets come from .env only."""
from __future__ import annotations

import os
from functools import lru_cache


class Settings:
    # Alerts
    discord_webhook_url: str = os.getenv("DISCORD_WEBHOOK_URL", "")

    # Supabase
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_service_role_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    # Meshy preflight
    meshy_api_key: str = os.getenv("MESHY_API_KEY", "")
    meshy_base_url: str = os.getenv("MESHY_BASE_URL", "https://api.meshy.ai")

    # Economy
    core_url: str = os.getenv("HYPERCODE_CORE_URL", "http://host.docker.internal:8000")
    award_path: str = os.getenv("ECONOMY_AWARD_PATH", "/economy/award-dev-xp")
    owner_discord_id: str = os.getenv("OWNER_DISCORD_ID", "418075243404591106")
    xp_per_success: int = int(os.getenv("XP_PER_SUCCESS", "50"))

    # Service
    webhook_secret: str = os.getenv("PRINTGENIE_WEBHOOK_SECRET", "change-me")
    printguard_base_url: str = os.getenv("PRINTGUARD_BASE_URL", "http://printguard:8000")

    # Phase 4 (off by default)
    auto_pause_enabled: bool = os.getenv("AUTO_PAUSE_ENABLED", "false").lower() == "true"

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_role_key)

    @property
    def meshy_configured(self) -> bool:
        return bool(self.meshy_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
