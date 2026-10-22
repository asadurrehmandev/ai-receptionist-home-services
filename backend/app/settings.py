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
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    deepgram_api_key: str | None = None
    elevenlabs_api_key: str | None = None
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"
    twilio_auth_token: str | None = None
    public_base_url: str = ""

    @property
    def media_stream_ready(self) -> bool:
        return bool(self.deepgram_api_key and self.elevenlabs_api_key)


def settings_from_env() -> Settings:
    static_default = ROOT / "frontend" / "dist"
    static_env = os.environ.get("STATIC_DIR")
    static_dir = Path(static_env) if static_env else static_default
    if not static_dir.exists():
        static_dir = None
    return Settings(
        config_path=Path(os.environ.get("BUSINESS_CONFIG", ROOT / "config" / "business.yaml")),
        db_path=Path(os.environ.get("DATABASE_PATH", ROOT / "data" / "receptionist.db")),
        static_dir=static_dir,
        seed_on_start=os.environ.get("SEED_ON_START", "1") != "0",
        openai_api_key=os.environ.get("OPENAI_API_KEY") or None,
        openai_base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        openai_model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        deepgram_api_key=os.environ.get("DEEPGRAM_API_KEY") or None,
        elevenlabs_api_key=os.environ.get("ELEVENLABS_API_KEY") or None,
        elevenlabs_voice_id=os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM"),
        twilio_auth_token=os.environ.get("TWILIO_AUTH_TOKEN") or None,
        public_base_url=os.environ.get("PUBLIC_BASE_URL", ""),
    )
