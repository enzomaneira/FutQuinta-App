"""Ponto de entrada da API. Também serve o build do frontend (frontend/dist)."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import Scope

from app.api.routes import auth, health, players
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.jobs.scheduler import build_scheduler
from app.services.errors import DomainError

logger = logging.getLogger(__name__)


class SPAStaticFiles(StaticFiles):
    """Serve arquivos estáticos e devolve index.html para rotas do React Router."""

    async def get_response(self, path: str, scope: Scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            # Caminhos da API nunca caem no index.html
            if exc.status_code != 404 or path.startswith("api"):
                raise
            return await super().get_response("index.html", scope)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    scheduler = None
    if settings.scheduler_enabled:
        scheduler = build_scheduler()
        scheduler.start()
        logger.info("Agendador iniciado (fuso %s)", settings.tz)
    yield
    if scheduler is not None:
        scheduler.shutdown(wait=False)


def create_app() -> FastAPI:
    setup_logging()
    settings = get_settings()
    app = FastAPI(title="App Futebol", lifespan=lifespan)

    @app.exception_handler(DomainError)
    async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
        # Erros de regra de negócio viram 4xx com a mensagem pronta para a tela
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    app.include_router(health.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    app.include_router(players.router, prefix="/api")

    if settings.frontend_dist.is_dir():
        app.mount(
            "/", SPAStaticFiles(directory=settings.frontend_dist, html=True), name="spa"
        )
    else:
        logger.warning(
            "frontend/dist não encontrado em %s; servindo só a API",
            settings.frontend_dist,
        )
    return app


app = create_app()
