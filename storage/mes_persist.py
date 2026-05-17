"""
Persistência operacional MES em SQLite (fonte de verdade).

- pedidos (fila / programação por máquina)
- dados_maquinas (status, produção, operador, tablet, paradas…)
- produtos_cadastrados
- resumo_fabrica

`dados.json` permanece como espelho/backup legível no mesmo volume (INDUPACK_DATA_DIR).
"""

from __future__ import annotations

import json
import logging
import shutil
import sqlite3
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


def _pedidos_count(pedidos: dict) -> int:
    if not isinstance(pedidos, dict):
        return 0
    n = 0
    for lst in pedidos.values():
        if isinstance(lst, list):
            n += len(lst)
    return n


def _maquinas_count(dados_maquinas: dict) -> int:
    return len(dados_maquinas) if isinstance(dados_maquinas, dict) else 0


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


def _load_chunks_from_db_path(db_path) -> dict[str, Any] | None:
    """Lê chunks MES de um ficheiro SQLite (ex.: DB legado na raiz do projeto)."""
    if not db_path.is_file():
        return None
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='mes_operacional_chunks'"
        )
        if cur.fetchone() is None:
            conn.close()
            return None
        rows = conn.execute(
            "SELECT chunk_key, payload_json FROM mes_operacional_chunks"
        ).fetchall()
        conn.close()
        if not rows:
            return None
        out: dict[str, Any] = {}
        for key, blob in rows:
            try:
                out[str(key)] = json.loads(blob or "{}")
            except json.JSONDecodeError:
                logger.warning("Chunk inválido em %s: %s", db_path, key)
        if CHUNK_MAQUINAS not in out:
            return None
        return out
    except (OSError, sqlite3.Error) as e:
        logger.warning("Não foi possível ler chunks de %s: %s", db_path, e)
        return None


def _chunks_to_state(chunks: dict[str, Any]) -> tuple[dict, list, dict, dict]:
    pedidos = _deserialize_pedidos(chunks.get(CHUNK_PEDIDOS))
    produtos = _deserialize_produtos(chunks.get(CHUNK_PRODUTOS))
    maquinas = _deserialize_maquinas(chunks.get(CHUNK_MAQUINAS))
    resumo = _deserialize_resumo(chunks.get(CHUNK_RESUMO))
    return pedidos, produtos, maquinas, resumo


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


def _score_state(pedidos: dict, maquinas: dict) -> int:
    """Prioriza snapshot com mais programação operacional."""
    return _pedidos_count(pedidos) * 1000 + _maquinas_count(maquinas)


def _pick_best_state(
    *candidates: tuple[dict, list, dict, dict] | None,
) -> tuple[dict, list, dict, dict]:
    best: tuple[dict, list, dict, dict] | None = None
    best_score = -1
    for c in candidates:
        if c is None:
            continue
        sc = _score_state(c[0], c[2])
        if sc > best_score:
            best_score = sc
            best = c
    if best is not None:
        return best
    return _defaults()


def load_operational_state() -> tuple[dict, list, dict, dict]:
    """
    Carrega estado operacional: melhor snapshot entre SQLite, DB legado, dados.json.
    Nunca descarta programação existente em disco por snapshot vazio em memória.
    """
    _migrate_legacy_files()

    sqlite_chunks = _load_chunks_from_sqlite()
    sqlite_state = _chunks_to_state(sqlite_chunks) if sqlite_chunks else None

    json_state = _load_from_json_file()

    legacy_db_chunks = _load_chunks_from_db_path(LEGACY_DB_PATH)
    legacy_db_state = _chunks_to_state(legacy_db_chunks) if legacy_db_chunks else None

    pedidos, produtos, maquinas, resumo = _pick_best_state(
        sqlite_state,
        json_state,
        legacy_db_state,
    )

    n_ped = _pedidos_count(pedidos)
    sc = _score_state(pedidos, maquinas)
    if sqlite_state is not None and sc == _score_state(sqlite_state[0], sqlite_state[2]):
        src = "SQLite"
    elif json_state is not None and sc == _score_state(json_state[0], json_state[2]):
        src = "dados.json"
    elif legacy_db_state is not None and sc == _score_state(legacy_db_state[0], legacy_db_state[2]):
        src = "indupack.db legado"
    else:
        src = "defaults"

    logger.info(
        "Estado MES carregado (%s): %s máquinas, %s pedidos na fila | DB=%s",
        src,
        len(maquinas),
        n_ped,
        DB_PATH,
    )

    if n_ped == 0 and sqlite_state is None and json_state is None and legacy_db_state is None:
        logger.warning(
            "Sem programação em disco — defaults iniciais (use INDUPACK_DATA_DIR em volume persistente no Render)"
        )

    # Sincroniza snapshot vencedor → SQLite + dados.json no volume persistente
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
            conn.execute(text("PRAGMA wal_checkpoint(FULL)"))
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
