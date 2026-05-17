import os
from pathlib import Path

try:
    import itsdangerous  # noqa: F401  # exigido pelo SessionMiddleware do Starlette
except ModuleNotFoundError as exc:
    raise SystemExit(
        "[INDUPACK] Dependência ausente: itsdangerous.\n"
        "Na pasta do projeto, execute:\n"
        "  python -m pip install -r requirements.txt\n"
        "Se usar outro interpretador, use o mesmo comando com esse Python "
        "(ex.: py -3 -m pip install -r requirements.txt)."
    ) from exc

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from database import init_db
from routes.admin_painel import router as admin_painel_router
from routes.api import router as api_router
from routes.backup_api import router as backup_router
from routes.config_params import router as config_params_router
from routes.pages import router as pages_router
from routes.relatorios_api import router as relatorios_router
from routes.terminais_api import router as terminais_router
from services import backup_indupack
from services.config_params_db import seed_stop_motives_if_empty, session_max_age_seconds
from storage.mes_persist import bootstrap_mes_operacional
from services.terminais_store import bootstrap_terminal_sessions

init_db()
seed_stop_motives_if_empty()
bootstrap_mes_operacional()
bootstrap_terminal_sessions()
_SESSION_MAX_AGE = session_max_age_seconds()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_stop_motives_if_empty()
    bootstrap_mes_operacional()
    bootstrap_terminal_sessions()
    backup_indupack.start_auto_backup_scheduler()
    yield
    backup_indupack.stop_auto_backup_scheduler()
    try:
        from storage.state import persist

        persist()
    except Exception:
        pass


app = FastAPI(lifespan=lifespan)

_secret = os.environ.get("INDUPACK_SESSION_SECRET", "indupack-dev-secret-altere-em-producao")
app.add_middleware(SessionMiddleware, secret_key=_secret, max_age=_SESSION_MAX_AGE, same_site="lax")

_static_dir = Path(__file__).resolve().parent / "static"
_static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

# API antes das páginas: GET /tablet/operadores não pode cair em GET /tablet/{id} com id="operadores".
app.include_router(api_router)
app.include_router(relatorios_router)
app.include_router(terminais_router)
app.include_router(pages_router)
app.include_router(backup_router)
app.include_router(admin_painel_router)
app.include_router(config_params_router)


if __name__ == "__main__":
    import uvicorn

    _port = int(os.environ.get("PORT", "10000"))
    uvicorn.run("main:app", host="0.0.0.0", port=_port)
