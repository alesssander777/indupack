"""
Backup INDUPACK: SQLite (API nativa .backup), ZIP do projeto e agendamento leve em thread.
Não inclui a pasta `backups/` no ZIP completo (evita recursão e arquivos gigantes).
"""

from __future__ import annotations

import logging
import os
import re
import sqlite3
import threading
import time
import zipfile
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("indupack.backup")

_ROOT = Path(__file__).resolve().parent.parent
from storage.paths import DB_PATH, DADOS_JSON_PATH

_DB_SOURCE = DB_PATH
_BACKUPS_ROOT = _ROOT / "backups"
_DIR_DB = _BACKUPS_ROOT / "database"
_DIR_SYSTEM = _BACKUPS_ROOT / "system"

# Pastas e ficheiros incluídos no ZIP “sistema completo”
_FULL_ZIP_TOP_FILES = (
    "main.py",
    "requirements.txt",
    "dados.json",
    "indupack.db",
    "usuarios_indupack.json",
)
_FULL_ZIP_DIRS = ("routes", "templates", "static", "database", "storage", "services")

_SKIP_DIR_NAMES = frozenset(
    {
        "__pycache__",
        ".git",
        ".svn",
        ".venv",
        "venv",
        "env",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "backups",
        "node_modules",
    }
)

_RE_DB_NAME = re.compile(r"^backup_db_\d{4}_\d{2}_\d{2}_\d{2}_\d{2}\.db$")
_RE_ZIP_NAME = re.compile(r"^indupack_full_backup_\d{4}_\d{2}_\d{2}_\d{2}_\d{2}\.zip$")

_auto_stop = threading.Event()
_auto_thread: threading.Thread | None = None
_auto_lock = threading.Lock()
_last_db_mono = 0.0
_last_full_mono = 0.0


def _ensure_dirs() -> None:
    _DIR_DB.mkdir(parents=True, exist_ok=True)
    _DIR_SYSTEM.mkdir(parents=True, exist_ok=True)


def timestamp_slug(now: datetime | None = None) -> str:
    """Ex.: 2026_05_12_20_10 (data e hora local)."""
    dt = now or datetime.now()
    return dt.strftime("%Y_%m_%d_%H_%M")


def _prune_directory(folder: Path, pattern: re.Pattern[str], max_files: int) -> None:
    if max_files <= 0 or not folder.is_dir():
        return
    matches = sorted(
        (p for p in folder.iterdir() if p.is_file() and pattern.match(p.name)),
        key=lambda p: p.stat().st_mtime,
    )
    while len(matches) > max_files:
        victim = matches.pop(0)
        try:
            victim.unlink()
            logger.info("Backup antigo removido: %s", victim.name)
        except OSError as e:
            logger.warning("Não foi possível remover backup antigo %s: %s", victim, e)


def backup_database() -> dict:
    """
    Cópia consistente do SQLite via API `.backup()` (adequado com WAL ativo).
    """
    _ensure_dirs()
    name = f"backup_db_{timestamp_slug()}.db"
    dest = _DIR_DB / name
    if dest.exists():
        time.sleep(1.1)
        name = f"backup_db_{timestamp_slug()}.db"
        dest = _DIR_DB / name

    if not _DB_SOURCE.is_file():
        try:
            dest.touch()
        except OSError as e:
            return {"ok": False, "erro": "db_inexistente", "detalhe": str(e)}
        return {
            "ok": True,
            "tipo": "database",
            "arquivo": name,
            "caminho": str(dest.relative_to(_ROOT)),
            "aviso": "indupack.db ainda não existia; criado ficheiro vazio de backup.",
        }

    try:
        src = sqlite3.connect(_DB_SOURCE, timeout=30.0)
        try:
            dst = sqlite3.connect(dest, timeout=30.0)
            try:
                with dst:
                    src.backup(dst)
            finally:
                dst.close()
        finally:
            src.close()
    except sqlite3.Error as e:
        if dest.exists():
            try:
                dest.unlink()
            except OSError:
                pass
        return {"ok": False, "erro": "sqlite_backup", "detalhe": str(e)}

    max_keep = int(os.environ.get("INDUPACK_BACKUP_MAX_DB_FILES", "48") or "48")
    _prune_directory(_DIR_DB, _RE_DB_NAME, max_keep)

    return {
        "ok": True,
        "tipo": "database",
        "arquivo": name,
        "caminho": str(dest.relative_to(_ROOT)),
        "bytes": dest.stat().st_size,
    }


def _add_tree_to_zip(zf: zipfile.ZipFile, rel_root: Path) -> None:
    if not rel_root.is_dir():
        return
    for dirpath, dirnames, filenames in os.walk(rel_root, topdown=True):
        dp = Path(dirpath)
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIR_NAMES and not d.endswith(".egg-info")]
        for fn in filenames:
            if fn.endswith((".pyc", ".pyo")):
                continue
            full = dp / fn
            try:
                rel = full.relative_to(_ROOT)
            except ValueError:
                continue
            arc = str(rel).replace("\\", "/")
            try:
                zf.write(full, arcname=arc, compress_type=zipfile.ZIP_DEFLATED)
            except OSError as e:
                logger.warning("ZIP: ignorado %s (%s)", full, e)


def backup_full_system_zip() -> dict:
    """ZIP do projeto (sem pasta backups/, sem __pycache__)."""
    _ensure_dirs()
    name = f"indupack_full_backup_{timestamp_slug()}.zip"
    dest = _DIR_SYSTEM / name
    if dest.exists():
        time.sleep(1.1)
        name = f"indupack_full_backup_{timestamp_slug()}.zip"
        dest = _DIR_SYSTEM / name

    tmp = dest.with_suffix(dest.suffix + ".tmp")
    try:
        if tmp.exists():
            tmp.unlink()
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for fname in _FULL_ZIP_TOP_FILES:
                p = _ROOT / fname
                if p.is_file():
                    zf.write(p, arcname=fname.replace("\\", "/"))
            for p in (DB_PATH, DADOS_JSON_PATH):
                if p.is_file() and p.resolve() not in {_ROOT.joinpath(n).resolve() for n in ("indupack.db", "dados.json")}:
                    zf.write(p, arcname=f"data/{p.name}")
            for dname in _FULL_ZIP_DIRS:
                _add_tree_to_zip(zf, _ROOT / dname)
        os.replace(tmp, dest)
    except Exception as e:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        return {"ok": False, "erro": "zip_falhou", "detalhe": str(e)}

    max_keep = int(os.environ.get("INDUPACK_BACKUP_MAX_ZIP_FILES", "24") or "24")
    _prune_directory(_DIR_SYSTEM, _RE_ZIP_NAME, max_keep)

    return {
        "ok": True,
        "tipo": "system",
        "arquivo": name,
        "caminho": str(dest.relative_to(_ROOT)),
        "bytes": dest.stat().st_size,
    }


def _file_entry(path: Path) -> dict:
    st = path.stat()
    return {
        "nome": path.name,
        "bytes": st.st_size,
        "mtime_iso": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
    }


def list_backups() -> dict:
    _ensure_dirs()
    db_files = sorted(
        (_file_entry(p) for p in _DIR_DB.iterdir() if p.is_file() and _RE_DB_NAME.match(p.name)),
        key=lambda x: x["mtime_iso"],
        reverse=True,
    )
    zip_files = sorted(
        (_file_entry(p) for p in _DIR_SYSTEM.iterdir() if p.is_file() and _RE_ZIP_NAME.match(p.name)),
        key=lambda x: x["mtime_iso"],
        reverse=True,
    )
    return {"ok": True, "database": db_files, "system": zip_files}


def resolve_safe_backup_path(kind: str, filename: str) -> Path | None:
    base = filename.replace("\\", "/").split("/")[-1]
    if not base or base in (".", ".."):
        return None
    if kind == "database" and _RE_DB_NAME.match(base):
        p = _DIR_DB / base
        return p if p.is_file() else None
    if kind == "system" and _RE_ZIP_NAME.match(base):
        p = _DIR_SYSTEM / base
        return p if p.is_file() else None
    return None


def _auto_enabled() -> bool:
    return os.environ.get("INDUPACK_AUTO_BACKUP", "1").strip().lower() not in (
        "0",
        "false",
        "off",
        "no",
    )


def _interval_hours(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or str(raw).strip() == "":
        return default
    try:
        v = float(raw)
        return v if v > 0 else 0.0
    except ValueError:
        return default


def _auto_worker() -> None:
    global _last_db_mono, _last_full_mono
    db_hours = _interval_hours("INDUPACK_AUTO_BACKUP_DB_HOURS", 6.0)
    full_hours = _interval_hours("INDUPACK_AUTO_BACKUP_FULL_HOURS", 24.0)
    try:
        delay_first = max(0, int(os.environ.get("INDUPACK_AUTO_BACKUP_FIRST_DELAY_SEC", "180") or "180"))
    except ValueError:
        delay_first = 180
    if delay_first > 0 and _auto_stop.wait(float(delay_first)):
        return

    with _auto_lock:
        _last_db_mono = 0.0
        # Primeiro ZIP completo só após um intervalo (evita pico CPU/disco no arranque).
        _last_full_mono = time.monotonic()

    while not _auto_stop.is_set():
        if not _auto_enabled():
            if _auto_stop.wait(timeout=60.0):
                break
            continue

        now = time.monotonic()
        with _auto_lock:
            last_db = _last_db_mono
            last_full = _last_full_mono

        did = False
        if db_hours > 0 and (last_db == 0.0 or (now - last_db) >= db_hours * 3600.0):
            r = {}
            try:
                r = backup_database()
                if r.get("ok"):
                    logger.info("Backup automático DB: %s", r.get("arquivo"))
                else:
                    logger.warning("Backup automático DB falhou: %s", r)
            except Exception:
                logger.exception("Backup automático DB — exceção")
                r = {"ok": False}
            with _auto_lock:
                if r.get("ok"):
                    _last_db_mono = time.monotonic()
                else:
                    # Falha: nova tentativa após ~5 min (sem bloquear 6h por erro transitório).
                    retry_delay = min(300.0, max(60.0, db_hours * 3600.0 * 0.02))
                    _last_db_mono = time.monotonic() - db_hours * 3600.0 + retry_delay
            did = True

        now = time.monotonic()
        with _auto_lock:
            last_full = _last_full_mono

        if full_hours > 0 and (last_full == 0.0 or (now - last_full) >= full_hours * 3600.0):
            r = {}
            try:
                r = backup_full_system_zip()
                if r.get("ok"):
                    logger.info("Backup automático ZIP: %s", r.get("arquivo"))
                else:
                    logger.warning("Backup automático ZIP falhou: %s", r)
            except Exception:
                logger.exception("Backup automático ZIP — exceção")
                r = {"ok": False}
            with _auto_lock:
                if r.get("ok"):
                    _last_full_mono = time.monotonic()
                else:
                    retry_delay = min(600.0, max(120.0, full_hours * 3600.0 * 0.02))
                    _last_full_mono = time.monotonic() - full_hours * 3600.0 + retry_delay
            did = True

        wait = 30.0 if did else 60.0
        if _auto_stop.wait(timeout=wait):
            break


def start_auto_backup_scheduler() -> None:
    global _auto_thread
    if not _auto_enabled():
        logger.info("Backups automáticos desativados (INDUPACK_AUTO_BACKUP).")
        return
    with _auto_lock:
        if _auto_thread and _auto_thread.is_alive():
            return
        _auto_stop.clear()
        _auto_thread = threading.Thread(target=_auto_worker, name="indupack-auto-backup", daemon=True)
        _auto_thread.start()
    logger.info("Agendador de backup iniciado (thread em segundo plano).")


def stop_auto_backup_scheduler() -> None:
    global _auto_thread
    _auto_stop.set()
    t = _auto_thread
    if t and t.is_alive():
        t.join(timeout=5.0)
    _auto_thread = None
