"""API JSON do painel administrativo (configurações)."""

from __future__ import annotations

from fastapi import APIRouter, Request

from services import config_admin, indupack_auth

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/painel")
def admin_painel_json(request: Request):
    err = indupack_auth.require_api_role(request, "admin_painel")
    if err:
        return err
    return config_admin.resumo_painel_admin()
