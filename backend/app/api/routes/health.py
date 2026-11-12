from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import DbSession

router = APIRouter(tags=["health"])


@router.get("/health")
def health(db: DbSession) -> dict[str, str]:
    # Usado pelo healthcheck do Railway: confirma que o banco responde
    db.execute(text("SELECT 1"))
    return {"status": "ok"}
