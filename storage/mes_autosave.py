"""Gravação periódica do estado MES (protege operação entre deploys/restarts)."""

from __future__ import annotations

import logging
import os
import threading
import time

logger = logging.getLogger("indupack.autosave")

_stop = threading.Event()
_thread: threading.Thread | None = None
_lock = threading.Lock()


def _interval_seconds() -> float:
    raw = os.environ.get("INDUPACK_AUTOSAVE_SEC", "30")
    try:
        return max(0.0, float(raw))
    except (TypeError, ValueError):
        return 30.0


def start_mes_autosave() -> None:
    """Thread daemon: persist() a cada N segundos (0 = desligado)."""
    global _thread
    sec = _interval_seconds()
    if sec <= 0:
        return
    with _lock:
        if _thread is not None and _thread.is_alive():
            return
        _stop.clear()

        def _loop() -> None:
            while not _stop.wait(sec):
                try:
                    from storage.state import persist

                    if persist():
                        logger.debug("Autosave MES OK")
                except Exception as e:
                    logger.warning("Autosave MES falhou: %s", e)

        _thread = threading.Thread(target=_loop, name="indupack-mes-autosave", daemon=True)
        _thread.start()
        logger.info("Autosave MES ativo a cada %ss", int(sec))


def stop_mes_autosave() -> None:
    _stop.set()
