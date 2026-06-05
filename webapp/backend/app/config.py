"""Application configuration via environment variables."""
import os
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Paths
    project_root: Path = _REPO_ROOT
    skills_dir: Path = Path(os.environ.get("SKILLS_DIR", str(_REPO_ROOT / "skills")))
    data_dir: Path = Path(os.environ.get("DATA_DIR", "/tmp/3dpp-data"))
    materials_file: Path = Path("/app/skills/print-profiles/materials.json")

    # Server
    host: str = "0.0.0.0"
    port: int = 8080
    cors_origins: str = "http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000"
    api_secret: str = ""

    # Redis / sessions
    redis_url: str = "redis://redis:6379/0"
    use_redis: bool = True

    # Claude
    claude_mode: str = "auto"  # auto | cli | api | demo
    claude_cli: str = "claude"
    claude_model: str = "sonnet"
    claude_timeout_s: int = 600
    anthropic_api_key: str = ""

    # MCP / Onshape
    mcp_sse_url: str = "https://nativedev.tail7d3518.ts.net:10001/sse"
    pipeline_mode: str = "auto"  # auto | onshape | cadquery | demo
    onshape_default_did: str = ""
    onshape_default_wid: str = ""
    onshape_default_eid: str = ""
    onshape_keys_file: str = ""

    # CadQuery fallback
    cadquery_timeout_s: int = 120
    exec_timeout_s: int = 60

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors(cls, v: str | list[str]) -> str:
        if isinstance(v, list):
            return ",".join(v)
        return v

    def cors_origin_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

    def resolved_skills_dir(self) -> Path:
        if self.skills_dir.exists():
            return self.skills_dir
        local = self.project_root / "skills"
        return local if local.exists() else self.skills_dir

    def resolved_materials_file(self) -> Path:
        skills = self.resolved_skills_dir()
        return skills / "print-profiles" / "materials.json"


settings = Settings()
