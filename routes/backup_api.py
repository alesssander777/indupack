"""API de backup (admin): listar, gerar manualmente e descarregar ficheiros."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse

from services import backup_indupack, indupack_auth

router = APIRouter(prefix="/backup", tags=["backup"])


@router.get("/list")
def backup_list(request: Request):
    err = indupack_auth.require_api_role(request, "backup_list")
    if err:
        return err
    return backup_indupack.list_backups()


@router.post("/database")
async def backup_database_manual(request: Request):
    err = indupack_auth.require_api_role(request, "backup_database_manual")
    if err:
        return err
    return await asyncio.to_thread(backup_indupack.backup_database)


@router.post("/full")
async def backup_full_manual(request: Request):
    err = indupack_auth.require_api_role(request, "backup_full_manual")
    if err:
        return err
    return await asyncio.to_thread(backup_indupack.backup_full_system_zip)


@router.get("/download/database/{filename}")
def backup_download_database(request: Request, filename: str):
    err = indupack_auth.require_api_role(request, "backup_download")
    if err:
        return err
    path = backup_indupack.resolve_safe_backup_path("database", filename)
    if path is None:
        return JSONResponse({"ok": False, "erro": "ficheiro_invalido"}, status_code=404)
    return FileResponse(
        path,
        filename=path.name,
        media_type="application/octet-stream",
    )


@router.get("/download/system/{filename}")
def backup_download_system(request: Request, filename: str):
    err = indupack_auth.require_api_role(request, "backup_download")
    if err:
        return err
    path = backup_indupack.resolve_safe_backup_path("system", filename)
    if path is None:
        return JSONResponse({"ok": False, "erro": "ficheiro_invalido"}, status_code=404)
    return FileResponse(
        path,
        filename=path.name,
        media_type="application/zip",
    )
