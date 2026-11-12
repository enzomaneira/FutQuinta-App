"""Configuração do processo, lida das variáveis de ambiente.

Aqui ficam só segredos e parâmetros de infraestrutura. Regras de negócio
(valores, horários, prazos) ficam na tabela `settings`, editável pelo app.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Procura o .env na raiz do repositório e também em backend/
        env_file=(REPO_DIR / ".env", BACKEND_DIR / ".env"),
        extra="ignore",
    )

    database_url: str
    jwt_secret: str
    jwt_expires_minutes: int = 60 * 24 * 7  # 7 dias
    tz: str = "America/Sao_Paulo"
    scheduler_enabled: bool = True
    frontend_dist: Path = REPO_DIR / "frontend" / "dist"

    @field_validator("database_url")
    @classmethod
    def use_psycopg_driver(cls, value: str) -> str:
        # O Railway entrega "postgresql://..." (ou "postgres://..."); o
        # SQLAlchemy precisa saber que o driver é o psycopg 3.
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg://" + value[len(prefix):]
        return value

    @field_validator("jwt_secret")
    @classmethod
    def secret_not_empty(cls, value: str) -> str:
        if len(value) < 16:
            raise ValueError("JWT_SECRET precisa ter pelo menos 16 caracteres")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
