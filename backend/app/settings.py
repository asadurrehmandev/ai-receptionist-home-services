"""Runtime settings. Secrets stay empty in the demo."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


@dataclass
class Settings:
    config_path: Path
    db_path: Path
    static_dir: Path | None
    seed_on_start: bool = True
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5-5"
    deepgram_api_key: str | None = None
    elevenlabs_api_key: str | None = None
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"
    twilio_auth_token: str | None = None
    twilio_account_sid: str | None = None
    twilio_from_number: str | None = None
    public_base_url: str = ""
    admin_token: str | None = None
    demo_mode: bool = True
    webhook_secret: str | None = None
    retention_days: int = 30
    cors_origins: tuple[str, ...] = ("http://127.0.0.1:43123", "http://localhost:43123")
    model_client: object | None = None

    @property
    def media_stream_ready(self) -> bool:
        return bool(self.deepgram_api_key and self.elevenlabs_api_key)

    @property
    def llm_ready(self) -> bool:
        return bool(self.anthropic_api_key or self.model_client)


def settings_from_env() -> Settings:
    static_default = ROOT / "frontend" / "dist"
    static_env = os.environ.get("STATIC_DIR")
    static_dir = Path(static_env) if static_env else static_default
    if not static_dir.exists():
        static_dir = None
    origins = os.environ.get("CORS_ORIGINS", "http://127.0.0.1:43123,http://localhost:43123")
    return Settings(
        config_path=Path(os.environ.get("BUSINESS_CONFIG", ROOT / "config" / "business.yaml")),
        db_path=Path(os.environ.get("DATABASE_PATH", ROOT / "data" / "receptionist.db")),
        static_dir=static_dir,
        seed_on_start=os.environ.get("SEED_ON_START", "1") != "0",
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY") or None,
        anthropic_model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5"),
        deepgram_api_key=os.environ.get("DEEPGRAM_API_KEY") or None,
        elevenlabs_api_key=os.environ.get("ELEVENLABS_API_KEY") or None,
        elevenlabs_voice_id=os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM"),
        twilio_auth_token=os.environ.get("TWILIO_AUTH_TOKEN") or None,
        twilio_account_sid=os.environ.get("TWILIO_ACCOUNT_SID") or None,
        twilio_from_number=os.environ.get("TWILIO_FROM_NUMBER") or None,
        public_base_url=os.environ.get("PUBLIC_BASE_URL", ""),
        admin_token=os.environ.get("ADMIN_TOKEN") or None,
        demo_mode=os.environ.get("DEMO_MODE", "1") != "0",
        webhook_secret=os.environ.get("WEBHOOK_SECRET") or None,
        retention_days=int(os.environ.get("RETENTION_DAYS", "30")),
        cors_origins=tuple(item.strip() for item in origins.split(",") if item.strip()),
    )
