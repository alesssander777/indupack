"""Persistência SQLite das sessões de terminal (complementa dados.json)."""

from __future__ import annotations

import time
from datetime import datetime, timezone

from sqlalchemy import inspect, text

from database.database import SessionLocal, engine
from database.models import TabletSessao
from storage.state import dados_maquinas, persist
from storage.tablet_normalize import as_bool, normalize_tablet_fields

_COMANDO_TTL_MS = 300_000

_SCHEMA_COLS = (
    ("operador_atual", 'VARCHAR(200) NOT NULL DEFAULT ""'),
    ("turno_atual", 'VARCHAR(120) NOT NULL DEFAULT ""'),
    ("status_maquina", 'VARCHAR(80) NOT NULL DEFAULT "PARADA"'),
    ("produzido", "INTEGER NOT NULL DEFAULT 0"),
    ("meta", "INTEGER NOT NULL DEFAULT 1000"),
    ("motivo_parada", 'VARCHAR(200) NOT NULL DEFAULT ""'),
    ("parada_inicio_epoch", "INTEGER NOT NULL DEFAULT 0"),
    ("tempo_producao_s", "INTEGER NOT NULL DEFAULT 0"),
    ("producao_sessao_epoch", "INTEGER NOT NULL DEFAULT 0"),
)


def _now_ms() -> int:
    return int(time.time() * 1000)


def ensure_tablet_sessao_schema() -> None:
    """Adiciona colunas operacionais em bancos já existentes (SQLite)."""
    insp = inspect(engine)
    if "tablet_sessoes" not in insp.get_table_names():
        return
    existing = {c["name"] for c in insp.get_columns("tablet_sessoes")}
    with engine.begin() as conn:
        for name, typedef in _SCHEMA_COLS:
            if name not in existing:
                conn.execute(text(f"ALTER TABLE tablet_sessoes ADD COLUMN {name} {typedef}"))


def _operational_from_machine(m: dict) -> dict:
    try:
        produzido = int(m.get("produzido") or 0)
    except (TypeError, ValueError):
        produzido = 0
    try:
        meta = int(m.get("meta") or 1000)
    except (TypeError, ValueError):
        meta = 1000
    st = str(m.get("status") or "PARADA").strip().upper()
    if st == "MANUTENCAO":
        st = "MANUTENÇÃO"
    return {
        "operador_atual": str(m.get("operador_atual") or "").strip()[:200],
        "turno_atual": str(m.get("turno_atual") or "").strip()[:120],
        "status_maquina": st[:80] if st else "PARADA",
        "produzido": max(0, produzido),
        "meta": max(1, meta),
        "motivo_parada": str(m.get("motivo_parada") or "").strip()[:200],
        "parada_inicio_epoch": int(m.get("parada_inicio_epoch") or 0),
        "tempo_producao_s": int(m.get("tempo_producao_s") or 0),
        "producao_sessao_epoch": int(m.get("producao_sessao_epoch") or 0),
    }


def _apply_operational_to_machine(m: dict, row: TabletSessao) -> None:
    m["operador_atual"] = str(row.operador_atual or "").strip()
    m["turno_atual"] = str(row.turno_atual or "").strip()
    m["status"] = str(row.status_maquina or "PARADA").strip() or "PARADA"
    m["produzido"] = int(row.produzido or 0)
    m["meta"] = max(1, int(row.meta or 1000))
    m["motivo_parada"] = str(row.motivo_parada or "").strip()
    m["parada_inicio_epoch"] = int(row.parada_inicio_epoch or 0)
    m["tempo_producao_s"] = int(row.tempo_producao_s or 0)
    m["producao_sessao_epoch"] = int(row.producao_sessao_epoch or 0)


def _row_from_machine(mid: int, m: dict) -> TabletSessao:
    normalize_tablet_fields(m)
    op = _operational_from_machine(m)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    return TabletSessao(
        maquina_id=int(mid),
        tablet_vinculado=str(m.get("tablet_vinculado") or "").strip()[:120],
        manutencao=as_bool(m.get("tablet_manutencao")),
        manutencao_msg=str(m.get("tablet_manutencao_msg") or "TERMINAL EM MANUTENÇÃO").strip()[:200],
        kiosk=as_bool(m.get("tablet_kiosk")),
        ultimo_acesso_epoch=int(m.get("tablet_ultimo_acesso_epoch") or 0),
        ultimo_ip=str(m.get("tablet_ultimo_ip") or "").strip()[:120],
        bateria_pct=m.get("tablet_bateria_pct"),
        bateria_carregando=as_bool(m.get("tablet_bateria_carregando")),
        sessao_online=as_bool(m.get("tablet_sessao_online")),
        reiniciar_em=int(m.get("tablet_reiniciar_em") or 0),
        reiniciar_ok_em=int(m.get("tablet_reiniciar_ok_em") or 0),
        operador_atual=op["operador_atual"],
        turno_atual=op["turno_atual"],
        status_maquina=op["status_maquina"],
        produzido=op["produzido"],
        meta=op["meta"],
        motivo_parada=op["motivo_parada"],
        parada_inicio_epoch=op["parada_inicio_epoch"],
        tempo_producao_s=op["tempo_producao_s"],
        producao_sessao_epoch=op["producao_sessao_epoch"],
        updated_at=now,
    )


def _sqlite_operational_meaningful(row: TabletSessao) -> bool:
    """Evita apagar operação do JSON com linha SQLite antiga/incompleta."""
    if int(row.ultimo_acesso_epoch or 0) > 0:
        return True
    if str(row.operador_atual or "").strip():
        return True
    if int(row.produzido or 0) > 0:
        return True
    st = str(row.status_maquina or "PARADA").strip().upper()
    if st and st not in ("PARADA",):
        return True
    return False


def apply_row_to_machine(m: dict, row: TabletSessao, *, json_manutencao: bool | None = None) -> None:
    """Restaura sessão do terminal do SQLite; operação só se houver snapshot válido."""
    m["tablet_vinculado"] = str(row.tablet_vinculado or "").strip()
    if json_manutencao is False:
        m["tablet_manutencao"] = False
    elif json_manutencao is True:
        m["tablet_manutencao"] = True
    else:
        m["tablet_manutencao"] = bool(row.manutencao)
    m["tablet_manutencao_msg"] = str(row.manutencao_msg or "TERMINAL EM MANUTENÇÃO").strip()
    m["tablet_kiosk"] = bool(row.kiosk)
    m["tablet_ultimo_acesso_epoch"] = int(row.ultimo_acesso_epoch or 0)
    m["tablet_ultimo_ip"] = str(row.ultimo_ip or "").strip()
    m["tablet_bateria_pct"] = row.bateria_pct
    m["tablet_bateria_carregando"] = bool(row.bateria_carregando)
    m["tablet_sessao_online"] = bool(row.sessao_online)
    m["tablet_reiniciar_em"] = int(row.reiniciar_em or 0)
    m["tablet_reiniciar_ok_em"] = int(row.reiniciar_ok_em or 0)
    if _sqlite_operational_meaningful(row):
        _apply_operational_to_machine(m, row)
    normalize_tablet_fields(m)


def save_sessao_sqlite(maquina_id: int) -> None:
    """Grava estado de terminal + operação da máquina no SQLite."""
    m = dados_maquinas.get(maquina_id)
    if not m or not isinstance(m, dict):
        return
    db = SessionLocal()
    try:
        row = db.get(TabletSessao, int(maquina_id))
        src = _row_from_machine(maquina_id, m)
        if row is None:
            db.add(src)
        else:
            row.tablet_vinculado = src.tablet_vinculado
            row.manutencao = src.manutencao
            row.manutencao_msg = src.manutencao_msg
            row.kiosk = src.kiosk
            row.ultimo_acesso_epoch = src.ultimo_acesso_epoch
            row.ultimo_ip = src.ultimo_ip
            row.bateria_pct = src.bateria_pct
            row.bateria_carregando = src.bateria_carregando
            row.sessao_online = src.sessao_online
            row.reiniciar_em = src.reiniciar_em
            row.reiniciar_ok_em = src.reiniciar_ok_em
            row.operador_atual = src.operador_atual
            row.turno_atual = src.turno_atual
            row.status_maquina = src.status_maquina
            row.produzido = src.produzido
            row.meta = src.meta
            row.motivo_parada = src.motivo_parada
            row.parada_inicio_epoch = src.parada_inicio_epoch
            row.tempo_producao_s = src.tempo_producao_s
            row.producao_sessao_epoch = src.producao_sessao_epoch
            row.updated_at = src.updated_at
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def commit_terminal(maquina_id: int | None = None) -> None:
    """Persiste terminal + operação no SQLite e dados.json."""
    if maquina_id is not None:
        m = dados_maquinas.get(maquina_id)
        if m:
            normalize_tablet_fields(m)
        save_sessao_sqlite(maquina_id)
    else:
        for mid in list(dados_maquinas.keys()):
            if isinstance(dados_maquinas[mid], dict):
                normalize_tablet_fields(dados_maquinas[mid])
            save_sessao_sqlite(mid)
    persist()


def persist_maquina(maquina_id: int) -> None:
    """Atalho: grava máquina no JSON e sincroniza sessão SQLite."""
    persist()
    save_sessao_sqlite(maquina_id)


def _limpar_comandos_expirados(m: dict, now_ms: int) -> None:
    rein = int(m.get("tablet_reiniciar_em") or 0)
    if rein <= 0:
        return
    ok = int(m.get("tablet_reiniciar_ok_em") or 0)
    if ok >= rein:
        return
    if (now_ms - rein) >= _COMANDO_TTL_MS:
        m["tablet_reiniciar_ok_em"] = rein


def preparar_pos_boot() -> None:
    """
    Após restart: offline até heartbeat; não altera manutenção nem operação.
  """
    now = _now_ms()
    for _mid, m in dados_maquinas.items():
        if not isinstance(m, dict):
            continue
        normalize_tablet_fields(m)
        _limpar_comandos_expirados(m, now)
        m["tablet_sessao_online"] = False


def bootstrap_terminal_sessions() -> None:
    """
    Sincroniza SQLite ↔ memória na subida do app.
    SQLite é fonte de verdade; JSON legado reconcilia manutenção fantasma.
    """
    ensure_tablet_sessao_schema()
    db = SessionLocal()
    try:
        rows = {r.maquina_id: r for r in db.query(TabletSessao).all()}
        for mid, m in list(dados_maquinas.items()):
            if not isinstance(m, dict):
                continue
            normalize_tablet_fields(m)
            json_manut = as_bool(m.get("tablet_manutencao"))
            row = rows.get(int(mid))
            if row is not None:
                apply_row_to_machine(m, row, json_manutencao=json_manut)
            else:
                db.add(_row_from_machine(int(mid), m))
        db.commit()
        rows = {r.maquina_id: r for r in db.query(TabletSessao).all()}
        for mid, m in dados_maquinas.items():
            if not isinstance(m, dict):
                continue
            json_manut = as_bool(m.get("tablet_manutencao"))
            row = rows.get(int(mid))
            if row is not None:
                apply_row_to_machine(m, row, json_manutencao=json_manut)
        preparar_pos_boot()
        for mid in dados_maquinas:
            save_sessao_sqlite(int(mid))
        persist()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
