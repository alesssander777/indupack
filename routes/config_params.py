"""API da central de parâmetros (SQLite) — admin apenas."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, File, Request, UploadFile

from services import config_params_db, indupack_auth, maquinas

router = APIRouter(prefix="/admin/config", tags=["config"])


def _guard(request: Request):
    return indupack_auth.require_api_role(request, "config_central")


@router.get("/completo")
def config_completo(request: Request):
    err = _guard(request)
    if err:
        return err
    return config_params_db.build_completo_payload()


@router.put("/settings")
async def config_settings_put(request: Request):
    err = _guard(request)
    if err:
        return err
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        return {"ok": False, "erro": "payload_invalido"}
    merged = config_params_db.save_merged_config(body)
    return {"ok": True, "settings": merged}


@router.post("/maquinas")
async def config_maquina_post(request: Request):
    err = _guard(request)
    if err:
        return err
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        body = {}
    nome = str(body.get("nome") or "").strip()
    setor = str(body.get("setor") or "").strip()
    raw_meta = body.get("meta_padrao", body.get("meta", 1000))
    try:
        meta = int(raw_meta)
    except (TypeError, ValueError):
        meta = 1000
    mid = body.get("id")
    if mid is not None and str(mid).strip() != "":
        try:
            mid_i = int(mid)
        except (TypeError, ValueError):
            return {"ok": False, "erro": "id_invalido"}
        return maquinas.criar_maquina(mid_i, nome=nome, setor=setor, meta_padrao=meta)
    mid_free = maquinas.proximo_id_maquina_livre()
    return maquinas.criar_maquina(mid_free, nome=nome, setor=setor, meta_padrao=meta)


@router.put("/maquinas/{mid}")
async def config_maquina_put(request: Request, mid: int):
    err = _guard(request)
    if err:
        return err
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        body = {}
    nome = str(body.get("nome") or "")
    setor = str(body.get("setor") or "")
    raw_meta = body.get("meta")
    meta = None
    if raw_meta is not None:
        try:
            meta = int(raw_meta)
        except (TypeError, ValueError):
            meta = None
    ativo = body.get("ativo")
    if ativo is not None:
        ativo = bool(ativo)
    else:
        ativo = None
    return maquinas.atualizar_maquina_config(mid, nome=nome, setor=setor, meta=meta, ativo=ativo)


@router.post("/operadores")
async def config_operador_post(request: Request):
    err = _guard(request)
    if err:
        return err
    body = await request.json()
    if not isinstance(body, dict):
        return {"ok": False, "erro": "payload_invalido"}
    return config_params_db.create_operator(
        str(body.get("nome") or ""),
        str(body.get("turno_padrao") or ""),
        str(body.get("nivel_acesso") or "operador"),
        bool(body.get("ativo", True)),
    )


@router.put("/operadores/{oid}")
async def config_operador_put(request: Request, oid: int):
    err = _guard(request)
    if err:
        return err
    body = await request.json()
    if not isinstance(body, dict):
        return {"ok": False, "erro": "payload_invalido"}
    return config_params_db.update_operator(
        oid,
        str(body.get("nome") or ""),
        str(body.get("turno_padrao") or ""),
        str(body.get("nivel_acesso") or "operador"),
        bool(body.get("ativo", True)),
    )


@router.delete("/operadores/{oid}")
def config_operador_delete(request: Request, oid: int):
    err = _guard(request)
    if err:
        return err
    return config_params_db.delete_operator(oid)


@router.post("/paradas")
async def config_parada_post(request: Request):
    err = _guard(request)
    if err:
        return err
    body = await request.json()
    if not isinstance(body, dict):
        return {"ok": False, "erro": "payload_invalido"}
    return config_params_db.create_stop_motive(
        str(body.get("codigo") or ""),
        str(body.get("rotulo") or ""),
        str(body.get("categoria") or "geral"),
        bool(body.get("ativo", True)),
    )


@router.put("/paradas/{sid}")
async def config_parada_put(request: Request, sid: int):
    err = _guard(request)
    if err:
        return err
    body = await request.json()
    if not isinstance(body, dict):
        return {"ok": False, "erro": "payload_invalido"}
    ordem = body.get("ordem")
    return config_params_db.update_stop_motive(
        sid,
        str(body.get("rotulo") or ""),
        str(body.get("categoria") or "geral"),
        bool(body.get("ativo", True)),
        ordem,
    )


@router.delete("/paradas/{sid}")
def config_parada_delete(request: Request, sid: int):
    err = _guard(request)
    if err:
        return err
    return config_params_db.delete_stop_motive(sid)


@router.post("/logo")
async def config_logo_post(request: Request, file: UploadFile = File(...)):
    err = _guard(request)
    if err:
        return err
    data = await file.read()
    if not data:
        return {"ok": False, "erro": "ficheiro_vazio"}
    return await asyncio.to_thread(config_params_db.save_logo_file, data, file.filename or "logo.png")
