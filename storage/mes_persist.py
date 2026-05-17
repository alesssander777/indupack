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
from storage.paths import DADOS_JSON_PATH, DATA_DIR, DB_PATH, LEGACY_DADOS_JSON_PATH, LEGACY_DB_PATH, ROOT

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
    """Copia legado só se o destino ainda não existir (nunca sobrescreve produção ativa)."""
    if LEGACY_DB_PATH.is_file() and not DB_PATH.is_file():
        try:
            shutil.copy2(LEGACY_DB_PATH, DB_PATH)
            logger.info("Migrado indupack.db legado → %s", DB_PATH)
        except OSError as e:
            logger.warning("Não foi possível migrar DB legado: %s", e)
    elif LEGACY_DB_PATH.is_file() and DB_PATH.is_file():
        logger.debug("DB ativo em %s — migração legado ignorada", DB_PATH)

    if LEGACY_DADOS_JSON_PATH.is_file() and not DADOS_JSON_PATH.is_file():
        try:
            shutil.copy2(LEGACY_DADOS_JSON_PATH, DADOS_JSON_PATH)
            logger.info("Migrado dados.json legado → %s", DADOS_JSON_PATH)
        except OSError as e:
            logger.warning("Não foi possível migrar dados.json legado: %s", e)
    elif LEGACY_DADOS_JSON_PATH.is_file() and DADOS_JSON_PATH.is_file():
        logger.debug("dados.json ativo em %s — migração legado ignorada", DADOS_JSON_PATH)


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


def _read_json_state_file(path) -> tuple[dict, list, dict, dict] | None:
    """Lê dados.json sem efeitos colaterais (não regrava defaults em disco)."""
    if not path.is_file():
        return None
    try:
        blob = path.read_bytes()
    except OSError as e:
        logger.warning("Não foi possível ler %s: %s", path, e)
        return None
    if not blob or not blob.strip():
        return None
    try:
        text = blob.decode("utf-8-sig").strip()
    except UnicodeDecodeError:
        return None
    if not text:
        return None
    try:
        raw = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(raw, dict):
        return None
    if "pedidos" in raw:
        pedidos = _deserialize_pedidos(raw.get("pedidos"))
        produtos = raw.get("produtos_cadastrados", [])
        if not isinstance(produtos, list):
            produtos = []
        maquinas = _deserialize_maquinas(raw.get("dados_maquinas", {}))
        resumo = _deserialize_resumo(raw.get("resumo_fabrica", {}))
        return pedidos, produtos, maquinas, resumo
    pedidos = _deserialize_pedidos(raw)
    return pedidos, [], json_store._default_dados_maquinas(), json_store._merge_resumo_fabrica({})


def _load_from_json_file() -> tuple[dict, list, dict, dict] | None:
    for path in (DADOS_JSON_PATH, LEGACY_DADOS_JSON_PATH):
        st = _read_json_state_file(path)
        if st is not None:
            return st
    return None


def _defaults() -> tuple[dict, list, dict, dict]:
    return {}, [], json_store._default_dados_maquinas(), json_store._merge_resumo_fabrica({})


def _score_state(pedidos: dict, maquinas: dict) -> tuple[int, int]:
    """Tupla (pedidos, máquinas): pedidos na fila sempre vencem quantidade de máquinas."""
    return (_pedidos_count(pedidos), _maquinas_count(maquinas))


def _pedido_identity(p: dict) -> str:
    if not isinstance(p, dict):
        return ""
    parts = [
        str(p.get("data") or "").strip(),
        str(p.get("cod") or "").strip(),
        str(p.get("cliente") or "").strip(),
        str(p.get("quantidade") or "").strip(),
        str(p.get("produto") or "").strip(),
        "1" if p.get("finalizado") else "0",
    ]
    return "|".join(parts)


def _merge_pedido_lists(*lists: list) -> list:
    """União por identidade; ordem da lista mais longa (fila programada)."""
    ordered: list = []
    for lst in sorted(
        (x for x in lists if isinstance(x, list)),
        key=len,
        reverse=True,
    ):
        for p in lst:
            if not isinstance(p, dict):
                continue
            key = _pedido_identity(p)
            if not key:
                ordered.append(dict(p))
                continue
            if any(_pedido_identity(x) == key for x in ordered if isinstance(x, dict)):
                continue
            ordered.append(dict(p))
    return ordered


def _merge_pedidos_dict(*pedidos_maps: dict) -> dict:
    keys: set[int] = set()
    for pm in pedidos_maps:
        if not isinstance(pm, dict):
            continue
        for k in pm:
            try:
                keys.add(int(k))
            except (TypeError, ValueError):
                pass
    out: dict = {}
    for mid in sorted(keys):
        lists = []
        for pm in pedidos_maps:
            if isinstance(pm, dict):
                lst = pm.get(mid) or pm.get(str(mid))
                if isinstance(lst, list):
                    lists.append(lst)
        if lists:
            out[mid] = _merge_pedido_lists(*lists)
    return out


def _machine_operational_score(m: dict) -> tuple:
    """Prioriza snapshot com mais produção/sessão ativa (evita reset na fusão)."""
    if not isinstance(m, dict):
        return (0, 0, 0, 0, 0)
    produzido = int(m.get("produzido") or 0)
    has_op = 1 if str(m.get("operador_atual") or "").strip() else 0
    st = str(m.get("status") or "PARADA").strip().upper()
    running = 1 if st == "RODANDO" else 0
    fp = str(m.get("pedido_atual_fp") or "")
    has_fp = 1 if fp and fp != "__vazio__" else 0
    parada = int(m.get("parada_inicio_epoch") or 0)
    hist = m.get("historico_paradas")
    hist_n = len(hist) if isinstance(hist, list) else 0
    return (produzido, has_op, running, has_fp, parada + hist_n)


def _merge_maquinas_dict(*maps: dict) -> dict:
    """Por máquina, mantém o registro com mais operação em curso (não o mais vazio)."""
    keys: set[int] = set()
    for m in maps:
        if not isinstance(m, dict):
            continue
        for k in m:
            try:
                keys.add(int(k))
            except (TypeError, ValueError):
                pass
    if not keys:
        return json_store._default_dados_maquinas()

    base = json_store._default_maquina_record()
    out: dict = {}
    for mid in sorted(keys):
        variants: list[dict] = []
        for m in maps:
            if not isinstance(m, dict):
                continue
            raw = m.get(mid) if mid in m else m.get(str(mid))
            if isinstance(raw, dict):
                variants.append({**base, **raw})
        if not variants:
            continue
        out[mid] = max(variants, key=_machine_operational_score)
    return json_store._merge_dados_maquinas(out)


def _merge_produtos_lists(*lists: list) -> list:
    best: list = []
    for lst in lists:
        if isinstance(lst, list) and len(lst) > len(best):
            best = list(lst)
    return best


def _merge_operational_states(
    *candidates: tuple[dict, list, dict, dict],
    labels: list[str] | None = None,
) -> tuple[dict, list, dict, dict, int, str]:
    """
    Funde candidatos: fila por máquina = união da maior programação disponível.
    Retorna (estado, total_pedidos, descrição_fontes).
    """
    valid = [c for c in candidates if c is not None]
    if not valid:
        d = _defaults()
        return d[0], d[1], d[2], d[3], 0, "defaults"

    pedidos = _merge_pedidos_dict(*(c[0] for c in valid))
    produtos = _merge_produtos_lists(*(c[1] for c in valid))
    maquinas = _merge_maquinas_dict(*(c[2] for c in valid))
    resumo = valid[0][3]
    best_resumo_score = (-1, -1)
    for c in valid:
        sc = _score_state(c[0], c[2])
        if sc > best_resumo_score:
            best_resumo_score = sc
            resumo = c[3]

    n = _pedidos_count(pedidos)
    if labels and len(labels) == len(valid):
        parts = [f"{labels[i]}={_pedidos_count(valid[i][0])}" for i in range(len(valid))]
        src = "merge(" + ", ".join(parts) + f") -> {n} pedidos"
    else:
        src = f"merge -> {n} pedidos"
    return pedidos, produtos, maquinas, resumo, n, src


def _discover_json_snapshots() -> list[tuple[str, tuple[dict, list, dict, dict]]]:
    found: list[tuple[str, tuple[dict, list, dict, dict]]] = []
    seen: set[str] = set()
    patterns = (
        DATA_DIR.glob("dados.json"),
        DATA_DIR.glob("dados.json.*"),
        ROOT.glob("dados.json"),
        ROOT.glob("dados.json.*"),
    )
    for gen in patterns:
        for path in gen:
            key = str(path.resolve())
            if key in seen or not path.is_file():
                continue
            seen.add(key)
            st = _read_json_state_file(path)
            if st is not None:
                found.append((path.name, st))
    return found


def _discover_db_snapshots() -> list[tuple[str, tuple[dict, list, dict, dict]]]:
    found: list[tuple[str, tuple[dict, list, dict, dict]]] = []
    db_paths: list = [DB_PATH, LEGACY_DB_PATH]
    backup_dir = ROOT / "backups" / "database"
    if backup_dir.is_dir():
        for p in sorted(backup_dir.glob("backup_db_*.db"), key=lambda x: x.stat().st_mtime, reverse=True)[:12]:
            db_paths.append(p)
    seen: set[str] = set()
    for path in db_paths:
        key = str(path.resolve())
        if key in seen:
            continue
        seen.add(key)
        chunks = _load_chunks_from_db_path(path)
        if chunks is None:
            continue
        st = _chunks_to_state(chunks)
        found.append((path.name, st))
    return found


def _pick_best_state(
    *candidates: tuple[dict, list, dict, dict] | None,
) -> tuple[dict, list, dict, dict]:
    """Escolhe candidato com maior programação (pedidos na fila, depois máquinas)."""
    best: tuple[dict, list, dict, dict] | None = None
    best_score: tuple[int, int] = (-1, -1)
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


def _pick_richest_pedidos_state(
    candidates: list[tuple[dict, list, dict, dict]],
) -> tuple[dict, list, dict, dict]:
    """Snapshot com mais pedidos na fila (evita perda após fusão inferior)."""
    best: tuple[dict, list, dict, dict] | None = None
    best_n = -1
    for c in candidates:
        n = _pedidos_count(c[0])
        if n > best_n:
            best_n = n
            best = c
    if best is not None:
        return best
    return _defaults()


def load_operational_state() -> tuple[dict, list, dict, dict]:
    """
    Carrega estado operacional fundindo SQLite, dados.json, DB legado e backups.
    Nunca descarta programação: filas são unidas por máquina; gravação na subida
    só ocorre se não reduzir o total de pedidos já presentes em disco.
    """
    _migrate_legacy_files()

    sqlite_chunks = _load_chunks_from_sqlite()
    sqlite_state = _chunks_to_state(sqlite_chunks) if sqlite_chunks else None

    json_state = _load_from_json_file()

    legacy_db_chunks = _load_chunks_from_db_path(LEGACY_DB_PATH)
    legacy_db_state = _chunks_to_state(legacy_db_chunks) if legacy_db_chunks else None

    candidates: list[tuple[dict, list, dict, dict]] = []
    labels: list[str] = []
    for label, st in (
        ("SQLite", sqlite_state),
        ("dados.json", json_state),
        ("DB legado", legacy_db_state),
    ):
        if st is not None:
            candidates.append(st)
            labels.append(label)

    main_json_n = _pedidos_count(json_state[0]) if json_state else -1
    for name, st in _discover_json_snapshots():
        if name in ("dados.json",) and main_json_n == _pedidos_count(st[0]):
            continue
        candidates.append(st)
        labels.append(f"JSON:{name}")

    sqlite_n = _pedidos_count(sqlite_state[0]) if sqlite_state else -1
    for name, st in _discover_db_snapshots():
        if name == DB_PATH.name and sqlite_n == _pedidos_count(st[0]):
            continue
        candidates.append(st)
        labels.append(f"backup:{name}")

    max_on_disk = max((_pedidos_count(c[0]) for c in candidates), default=0)

    if len(candidates) >= 2 or max_on_disk > 0:
        pedidos, produtos, maquinas, resumo, n_ped, src = _merge_operational_states(
            *candidates, labels=labels
        )
    else:
        picked = _pick_best_state(sqlite_state, json_state, legacy_db_state)
        pedidos, produtos, maquinas, resumo = picked
        n_ped = _pedidos_count(pedidos)
        src = "único snapshot ou defaults"

    logger.info(
        "Estado MES carregado (%s): %s máquinas, %s pedidos na fila | volume=%s | DB=%s",
        src,
        len(maquinas),
        n_ped,
        DATA_DIR,
        DB_PATH,
    )

    if n_ped < max_on_disk and candidates:
        logger.warning(
            "Fusão com %s pedidos < máximo em disco (%s) — usando snapshot mais completo",
            n_ped,
            max_on_disk,
        )
        pedidos, produtos, maquinas, resumo = _pick_richest_pedidos_state(candidates)
        n_ped = _pedidos_count(pedidos)
        src = f"fallback-richest -> {n_ped} pedidos"

    if n_ped == 0 and not candidates:
        logger.warning(
            "Sem programação em disco — defaults iniciais (use INDUPACK_DATA_DIR em volume persistente no Render)"
        )

    # Na subida: só grava se RECUPEROU mais pedidos — nunca regrava por "sincronizar"
    # (regravar no boot apagava filas após atualização/deploy).
    if n_ped < max_on_disk:
        logger.error(
            "Abortando gravação na subida: %s pedidos em memória vs %s no disco (volume intacto)",
            n_ped,
            max_on_disk,
        )
    elif n_ped > max_on_disk:
        logger.warning(
            "Programação recuperada na fusão: %s -> %s pedidos (persistindo)",
            max_on_disk,
            n_ped,
        )
        save_operational_state(pedidos, produtos, maquinas, resumo, mirror_json=True)
    else:
        logger.info(
            "Subida: %s pedidos carregados — gravação adiada (persist() na operação)",
            n_ped,
        )

    by_maq = {k: len(v) for k, v in pedidos.items() if isinstance(v, list)}
    if by_maq:
        logger.info("Fila por máquina: %s", by_maq)

    return pedidos, produtos, maquinas, resumo


def _load_disk_snapshot_minimal() -> tuple[dict, dict] | None:
    """Lê pedidos + máquinas do SQLite sem alterar memória."""
    chunks = _load_chunks_from_sqlite()
    if chunks is None:
        return None
    return (
        _deserialize_pedidos(chunks.get(CHUNK_PEDIDOS)),
        _deserialize_maquinas(chunks.get(CHUNK_MAQUINAS)),
    )


def _coalesce_with_disk(
    pedidos: dict,
    dados_maquinas: dict,
    *,
    allow_reduce: bool,
) -> tuple[dict, dict, bool]:
    """
    Funde com disco antes de gravar. Retorna (pedidos, máquinas, pode_gravar).
    Se allow_reduce=False, nunca grava menos pedidos que o disco já tem.
    """
    disk = _load_disk_snapshot_minimal()
    if disk is None:
        return pedidos, dados_maquinas, True

    disk_pedidos, disk_maquinas = disk
    disk_n = _pedidos_count(disk_pedidos)
    merged_pedidos = _merge_pedidos_dict(pedidos, disk_pedidos)
    merged_maquinas = _merge_maquinas_dict(dados_maquinas, disk_maquinas)
    new_n = _pedidos_count(merged_pedidos)

    if not allow_reduce and disk_n > 0 and new_n < disk_n:
        logger.error(
            "Gravação bloqueada: %s pedidos na memória vs %s no disco (%s) — dados em disco preservados",
            _pedidos_count(pedidos),
            disk_n,
            DB_PATH,
        )
        return merged_pedidos, merged_maquinas, False

    if not allow_reduce and disk_n > 0 and new_n > _pedidos_count(pedidos):
        logger.warning(
            "Memória recuperou pedidos do disco antes de gravar (%s → %s)",
            _pedidos_count(pedidos),
            new_n,
        )

    return merged_pedidos, merged_maquinas, True


def save_operational_state(
    pedidos: dict,
    produtos_cadastrados: list,
    dados_maquinas: dict,
    resumo_fabrica: dict | None = None,
    *,
    mirror_json: bool = True,
    allow_reduce: bool = False,
) -> bool:
    """
    Grava estado operacional no SQLite (transação) e opcionalmente em dados.json.
    Retorna False se a gravação foi bloqueada para não apagar programação.
    """
    pedidos, dados_maquinas, ok = _coalesce_with_disk(
        pedidos, dados_maquinas, allow_reduce=allow_reduce
    )
    if not ok:
        return False

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

    return True


def bootstrap_mes_operacional() -> None:
    """Chamado na subida do app após init_db — recarrega memória a partir do SQLite."""
    from storage.state import reload_from_store

    reload_from_store()
