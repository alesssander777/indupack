"""API de supervisão de terminais tablet (admin / supervisor / manutenção)."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from services import indupack_auth, terminais

router = APIRouter(prefix="/api/terminais", tags=["terminais"])


def _check(request: Request, route_name: str = "terminais_admin"):
    return indupack_auth.require_api_role(request, route_name)


def _usuario(request: Request) -> str:
    su = indupack_auth.session_user(request) or {}
    return str(su.get("cargo") or su.get("username") or "Supervisão")


@router.get("")
def terminais_lista(request: Request):
    err = _check(request)
    if err:
        return err
    rows = terminais.listagem_terminais_admin()
    on = sum(1 for r in rows if r.get("online"))
    last_ms = max((int(r.get("ultimo_acesso_ms") or 0) for r in rows), default=0)
    sync_txt = "—"
    if last_ms > 0:
        from datetime import datetime

        try:
            sync_txt = datetime.fromtimestamp(last_ms / 1000.0).strftime("%d/%m/%Y %H:%M:%S")
        except (OSError, OverflowError, ValueError):
            pass
    return JSONResponse(
        {
            "ok": True,
            "terminais": rows,
            "resumo": {
                "online": on,
                "offline": len(rows) - on,
                "total": len(rows),
                "ultima_sincronizacao_txt": sync_txt,
            },
        }
    )


@router.get("/{maquina_id}/logs")
def terminais_logs(request: Request, maquina_id: int):
    err = _check(request)
    if err:
        return err
    return JSONResponse({"ok": True, "logs": terminais.list_logs(maquina_id)})


@router.post("/{maquina_id}/reiniciar")
def terminais_reiniciar(request: Request, maquina_id: int):
    err = _check(request)
    if err:
        return err
    return JSONResponse(terminais.solicitar_reinicio(maquina_id, _usuario(request)))


@router.post("/{maquina_id}/kiosk")
async def terminais_kiosk(request: Request, maquina_id: int):
    err = _check(request)
    if err:
        return err
    try:
        body = await request.json()
    except Exception:
        body = {}
    ativo = bool(body.get("ativo")) if isinstance(body, dict) else True
    if isinstance(body, dict) and "ativo" not in body:
        from storage.state import dados_maquinas

        cur = bool((dados_maquinas.get(maquina_id) or {}).get("tablet_kiosk"))
        ativo = not cur
    return JSONResponse(terminais.set_kiosk(maquina_id, ativo, _usuario(request)))


@router.post("/{maquina_id}/manutencao")
async def terminais_manutencao(request: Request, maquina_id: int):
    err = _check(request)
    if err:
        return err
    try:
        body = await request.json()
    except Exception:
        body = {}
    ativo = bool(body.get("ativo")) if isinstance(body, dict) else True
    if isinstance(body, dict) and "ativo" not in body:
        from storage.state import dados_maquinas

        cur = bool((dados_maquinas.get(maquina_id) or {}).get("tablet_manutencao"))
        ativo = not cur
    return JSONResponse(terminais.set_manutencao(maquina_id, ativo, _usuario(request)))
