"""Resumo para o painel administrativo (configurações / MES)."""

from __future__ import annotations

from sqlalchemy import text

from database.database import engine
from services import backup_indupack, maquinas
from services.tablets_admin import listagem_terminais_admin


INDUPACK_APP_VERSION = "2.0.0"


def database_conectado() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def resumo_backups() -> dict:
    raw = backup_indupack.list_backups()
    dbs = list(raw.get("database") or [])
    zips = list(raw.get("system") or [])
    todos = dbs + zips
    ultimo = ""
    for e in todos:
        t = str(e.get("mtime_iso") or "")
        if t and (not ultimo or t > ultimo):
            ultimo = t
    total_bytes = 0
    for e in todos:
        try:
            total_bytes += int(e.get("bytes") or 0)
        except (TypeError, ValueError):
            pass
    return {
        "count_db": len(dbs),
        "count_zip": len(zips),
        "count_total": len(todos),
        "total_bytes": total_bytes,
        "ultimo_iso": ultimo,
    }


def resumo_painel_admin() -> dict:
    rows = listagem_terminais_admin()
    vinc = sum(1 for r in rows if str(r.get("tablet_codigo") or "").strip())
    return {
        "ok": True,
        "versao": INDUPACK_APP_VERSION,
        "servidor_online": True,
        "banco_conectado": database_conectado(),
        "maquinas_ativas": len(maquinas.ids_maquinas_ordenadas()),
        "maquinas_cadastradas": len(maquinas.ids_todas_maquinas_ordenadas()),
        "terminais_tablet": len(rows),
        "tablets_com_codigo": vinc,
        "backup": resumo_backups(),
    }
