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

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from routes.api import router as api_router
from routes.pages import router as pages_router

app = FastAPI()

_secret = os.environ.get("INDUPACK_SESSION_SECRET", "indupack-dev-secret-altere-em-producao")
app.add_middleware(SessionMiddleware, secret_key=_secret, max_age=60 * 60 * 24 * 7, same_site="lax")

_static_dir = Path(__file__).resolve().parent / "static"
_static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

app.include_router(pages_router)
app.include_router(api_router)
