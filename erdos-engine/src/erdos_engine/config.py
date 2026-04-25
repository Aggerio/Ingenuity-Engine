"""Configuration utilities for Erdos Engine."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Runtime settings loaded from environment and CLI overrides."""

    data_dir: Path = Field(default=Path("data"))
    reports_dir: Path = Field(default=Path("reports"))

    openai_compatible_api_key: str | None = None
    openai_compatible_base_url: str = "https://openrouter.ai/api"
    openai_compatible_model: str = "openai/gpt-oss-20b:free"
    openai_compatible_critic_api_key: str | None = None
    openai_compatible_critic_base_url: str = "https://openrouter.ai/api"
    openai_compatible_critic_model: str | None = "google/gemini-2.5-flash-lite"
    llm_timeout_seconds: int = 45
    llm_max_tokens: int = 1800

    lean_project_dir: Path = Field(default=Path("lean_workspace"))
    lean_timeout_seconds: int = 600
    lean_required: bool = True

    beam_width: int = 5
    max_depth: int = 5
    moves_per_state: int = 8
    retrieved_lemmas_per_state: int = 10
    stall_threshold: int = 2
    use_rlm: bool = True
    random_seed: int = 13
    use_critic: bool = False
    use_secondary_checkers: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables and defaults."""
        load_dotenv()
        return cls(
            openai_compatible_api_key=os.getenv("OPENAI_COMPATIBLE_API_KEY"),
            openai_compatible_base_url=os.getenv(
                "OPENAI_COMPATIBLE_BASE_URL", "https://openrouter.ai/api"
            ),
            openai_compatible_model=os.getenv(
                "OPENAI_COMPATIBLE_MODEL", "openai/gpt-oss-20b:free"
            ),
            openai_compatible_critic_api_key=os.getenv("OPENAI_COMPATIBLE_CRITIC_API_KEY"),
            openai_compatible_critic_base_url=os.getenv(
                "OPENAI_COMPATIBLE_CRITIC_BASE_URL", "https://openrouter.ai/api"
            ),
            openai_compatible_critic_model=os.getenv(
                "OPENAI_COMPATIBLE_CRITIC_MODEL", "google/gemini-2.5-flash-lite"
            ),
            llm_timeout_seconds=int(os.getenv("LLM_TIMEOUT_SECONDS", "45")),
            llm_max_tokens=int(os.getenv("LLM_MAX_TOKENS", "1800")),
            lean_project_dir=Path(os.getenv("LEAN_PROJECT_DIR", "lean_workspace")),
            lean_timeout_seconds=int(os.getenv("LEAN_TIMEOUT_SECONDS", "600")),
            lean_required=os.getenv("LEAN_REQUIRED", "true").lower()
            in {"1", "true", "yes", "on"},
            use_critic=os.getenv("USE_CRITIC", "false").lower() in {"1", "true", "yes", "on"},
            use_secondary_checkers=os.getenv("USE_SECONDARY_CHECKERS", "false").lower()
            in {"1", "true", "yes", "on"},
        )

    def with_overrides(self, **kwargs: object) -> "Settings":
        """Return updated settings with runtime overrides."""
        clean = {k: v for k, v in kwargs.items() if v is not None}
        return self.model_copy(update=clean)
