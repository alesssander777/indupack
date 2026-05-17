"""
Persistência operacional MES em SQLite (fonte de verdade).

- pedidos (fila por máquina)
- dados_maquinas (status, produção, operador, tablet, paradas…)
- produtos_cadastrados
- resumo_fabrica

`dados.json` permanece como espelho/backup legível.
"""

from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import inspect, text

from database.database import SessionLocal, engine
from database.models import MesOperacionalChunk
from storage import json_store
from storage.paths import DADOS_JSON_PATH, DB_PATH, LEGACY_DADOS_JSON_PATH, LEGACY_DB_PATH

logger = logging.getLogger("indupack.mes_persist")

CHUNK_PEDIDOS = "pedidos"
CHUNK_MAQUINAS = "dados_maquinas"
CHUNK_PRODUTOS = "produtos_cadastrados"
CHUNK_RESUMO = "resumo_fabrica"
_ALL_CHUNKS = (CHUNK_PEDIDOS, CHUNK_MAQUINAS, CHUNK_PRODUTOS, CHUNK_RESUMO)


def _now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _migrate_legacy_files() -> None:
    """Copia indupack.db / dados.json da raiz do repo para INDUPACK_DATA_DIR se necessário."""
    if LEGACY_DB_PATH.is_file() and not DB_PATH.is_file():
        try:
            shutil.copy2(LEGACY_DB_PATH, DB_PATH)
            logger.info("Migrado indupack.db legado → %s", DB_PATH)
        except OSError as e:
            logger.warning("Não foi possível migrar DB legado: %s", e)
    if LEGACY_DADOS_JSON_PATH.is_file() and not DADOS_JSON_PATH.is_file():
        try:
            shutil.copy2(LEGACY_DADOS_JSON_PATH, DADOS_JSON_PATH)
            logger.info("Migrado dados.json legado → %s", DADOS_JSON_PATH)
        except OSError as e:
            logger.warning("Não foi possível migrar dados.json legado: %s", e)


def _sqlite_has_chunks() -> bool:
    insp = inspect(engine)
    if "mes_operacional_chunks" not in insp.get_table_names():
        return False
    db = SessionLocal()
    try:
        return db.query(MesOperacionalChunk).count() > 0
    finally:
        db.close()


def _serialize_pedidos(pedidos: dict) -> dict:
    return {str(k): v for k, v in pedidos.items()}


def _serialize_maquinas(dados_maquinas: dict) -> dict:
    return {str(k): v for k, v in dados_maquinas.items()}


def _deserialize_pedidos(raw: Any) -> dict:
    if not isinstance(raw, dict):
        return {}
    out = json_store._normalize_pedidos_keys(raw)
    from services.pedidos import normalizar_pedido_fardos

    for lst in out.values():
        if isinstance(lst, list):
            for p in lst:
                if isinstance(p, dict):
                    normalizar_pedido_fardos(p)
    return out


def _deserialize_maquinas(raw: Any) -> dict:
    if not isinstance(raw, dict):
        return json_store._merge_dados_maquinas({})
    return json_store._merge_dados_maquinas(raw)


def _deserialize_produtos(raw: Any) -> list:
    if isinstance(raw, list):
        return raw
    return []


def _deserialize_resumo(raw: Any) -> dict:
    if isinstance(raw, dict):
        return json_store._merge_resumo_fabrica(raw)
    return json_store._merge_resumo_fabrica({})


def _load_chunks_from_sqlite() -> dict[str, Any] | None:
    if not _sqlite_has_chunks():
        return None
    db = SessionLocal()
    try:
        rows = db.query(MesOperacionalChunk).all()
        if not rows:
            return None
        out: dict[str, Any] = {}
        for row in rows:
            try:
                out[row.chunk_key] = json.loads(row.payload_json or "{}")
            except json.JSONDecodeError:
                logger.warning("Chunk SQLite inválido: %s", row.chunk_key)
        if CHUNK_MAQUINAS not in out:
            return None
        return out
    finally:
        db.close()


def _load_from_json_file() -> tuple[dict, list, dict, dict] | None:
    path = DADOS_JSON_PATH if DADOS_JSON_PATH.is_file() else None
    if path is None and LEGACY_DADOS_JSON_PATH.is_file():
        path = LEGACY_DADOS_JSON_PATH
    if path is None:
        return None
    old_arquivo = json_store.ARQUIVO
    try:
        json_store.ARQUIVO = str(path)
        return json_store.carregar_dados()
    finally:
        json_store.ARQUIVO = old_arquivo


def _defaults() -> tuple[dict, list, dict, dict]:
    return {}, [], json_store._default_dados_maquinas(), json_store._merge_resumo_fabrica({})


def load_operational_state() -> tuple[dict, list, dict, dict]:
    """
    Carrega estado operacional: SQLite (prioridade) → dados.json → defaults.
    """
    _migrate_legacy_files()

    chunks = _load_chunks_from_sqlite()
    if chunks is not None:
        pedidos = _deserialize_pedidos(chunks.get(CHUNK_PEDIDOS))
        produtos = _deserialize_produtos(chunks.get(CHUNK_PRODUTOS))
        maquinas = _deserialize_maquinas(chunks.get(CHUNK_MAQUINAS))
        resumo = _deserialize_resumo(chunks.get(CHUNK_RESUMO))
        logger.info(
            "Estado MES restaurado do SQLite (%s máquinas, %s filas pedido)",
            len(maquinas),
            len(pedidos),
        )
        return pedidos, produtos, maquinas, resumo

    loaded = _load_from_json_file()
    if loaded is not None:
        pedidos, produtos, maquinas, resumo = loaded
        if pedidos or maquinas:
            logger.info("Estado MES importado de dados.json para SQLite")
            save_operational_state(pedidos, produtos, maquinas, resumo, mirror_json=True)
            return pedidos, produtos, maquinas, resumo

    pedidos, produtos, maquinas, resumo = _defaults()
    logger.warning("Sem snapshot MES em disco — iniciando com defaults (configure volume persistente)")
    save_operational_state(pedidos, produtos, maquinas, resumo, mirror_json=True)
    return pedidos, produtos, maquinas, resumo


def save_operational_state(
    pedidos: dict,
    produtos_cadastrados: list,
    dados_maquinas: dict,
    resumo_fabrica: dict | None = None,
    *,
    mirror_json: bool = True,
) -> None:
    """Grava estado operacional no SQLite (transação) e opcionalmente em dados.json."""
    rf = resumo_fabrica if isinstance(resumo_fabrica, dict) else json_store._merge_resumo_fabrica({})
    payloads = {
        CHUNK_PEDIDOS: _serialize_pedidos(pedidos),
        CHUNK_PRODUTOS: produtos_cadastrados,
        CHUNK_MAQUINAS: _serialize_maquinas(dados_maquinas),
        CHUNK_RESUMO: rf,
    }
    now = _now_naive()
    db = SessionLocal()
    try:
        for key, data in payloads.items():
            blob = json.dumps(data, ensure_ascii=False)
            row = db.get(MesOperacionalChunk, key)
            if row is None:
                db.add(MesOperacionalChunk(chunk_key=key, payload_json=blob, updated_at=now))
            else:
                row.payload_json = blob
                row.updated_at = now
        db.commit()
        with engine.connect() as conn:
            conn.execute(text("PRAGMA wal_checkpoint(PASSIVE)"))
            conn.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    if mirror_json:
        json_store.ARQUIVO = str(DADOS_JSON_PATH)
        json_store.salvar_dados(pedidos, produtos_cadastrados, dados_maquinas, rf)


def bootstrap_mes_operacional() -> None:
    """Chamado na subida do app após init_db — recarrega memória a partir do SQLite."""
    from storage.state import reload_from_store

    reload_from_store()
