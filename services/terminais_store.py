"""Persistência SQLite das sessões de terminal (complementa dados.json)."""

from __future__ import annotations

import time
from datetime import datetime, timezone

from database.database import SessionLocal
from database.models import TabletSessao
from storage.state import dados_maquinas, persist
from storage.tablet_normalize import as_bool, normalize_tablet_fields

_COMANDO_TTL_MS = 300_000


def _now_ms() -> int:
    return int(time.time() * 1000)


def _row_from_machine(mid: int, m: dict) -> TabletSessao:
    normalize_tablet_fields(m)
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
        updated_at=now,
    )


def apply_row_to_machine(m: dict, row: TabletSessao) -> None:
    m["tablet_vinculado"] = str(row.tablet_vinculado or "").strip()
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
    normalize_tablet_fields(m)


def save_sessao_sqlite(maquina_id: int) -> None:
    """Grava estado de terminal da máquina no SQLite."""
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
            row.updated_at = src.updated_at
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def commit_terminal(maquina_id: int | None = None) -> None:
    """Persiste terminal no SQLite + dados.json."""
    if maquina_id is not None:
        m = dados_maquinas.get(maquina_id)
        if m:
            normalize_tablet_fields(m)
        save_sessao_sqlite(maquina_id)
    else:
        for mid in list(dados_maquinas.keys()):
            normalize_tablet_fields(dados_maquinas[mid])
            save_sessao_sqlite(mid)
    persist()


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
    Após restart do servidor: offline até novo heartbeat, sem forçar manutenção.
    Consome reinícios remotos expirados para não recarregar o tablet à toa.
    """
    now = _now_ms()
    for mid, m in dados_maquinas.items():
        if not isinstance(m, dict):
            continue
        normalize_tablet_fields(m)
        _limpar_comandos_expirados(m, now)
        # Nunca ativar manutenção por causa do boot — só o valor já persistido.
        m["tablet_sessao_online"] = False


def bootstrap_terminal_sessions() -> None:
    """
    Sincroniza SQLite ↔ memória na subida do app.
    SQLite é fonte de verdade para sessão de terminal; JSON mantém logs e backup.
    """
    db = SessionLocal()
    try:
        rows = {r.maquina_id: r for r in db.query(TabletSessao).all()}
        for mid, m in list(dados_maquinas.items()):
            if not isinstance(m, dict):
                continue
            normalize_tablet_fields(m)
            row = rows.get(int(mid))
            if row is not None:
                apply_row_to_machine(m, row)
            else:
                db.add(_row_from_machine(int(mid), m))
        db.commit()
        rows = {r.maquina_id: r for r in db.query(TabletSessao).all()}
        for mid, m in dados_maquinas.items():
            if not isinstance(m, dict):
                continue
            row = rows.get(int(mid))
            if row is not None:
                apply_row_to_machine(m, row)
        preparar_pos_boot()
        for mid in dados_maquinas:
            save_sessao_sqlite(int(mid))
        persist()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def export_sessoes_backup() -> list[dict]:
    """Snapshot das sessões (útil para diagnóstico / backup)."""
    db = SessionLocal()
    try:
        out = []
        for row in db.query(TabletSessao).order_by(TabletSessao.maquina_id):
            out.append(
                {
                    "maquina_id": row.maquina_id,
                    "tablet_vinculado": row.tablet_vinculado,
                    "manutencao": row.manutencao,
                    "kiosk": row.kiosk,
                    "ultimo_acesso_epoch": row.ultimo_acesso_epoch,
                    "sessao_online": row.sessao_online,
                    "updated_at": row.updated_at.isoformat() if row.updated_at else "",
                }
            )
        return out
    finally:
        db.close()
