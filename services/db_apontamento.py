"""Persistência de apontamentos no SQLite — complementa o JSON sem substituí-lo."""
from __future__ import annotations

import logging
from datetime import datetime

from storage.state import dados_maquinas, pedidos

logger = logging.getLogger(__name__)


def _produto_pedido_corrente(maq_id: int) -> str:
    lista = pedidos.get(maq_id) or []
    for p in lista:
        if p.get("finalizado"):
            continue
        cod = str(p.get("cod") or "").strip()
        prod = str(p.get("produto") or "").strip()
        cliente = str(p.get("cliente") or "").strip()
        partes = [x for x in (cod, prod) if x]
        if cliente and partes:
            return f"{cliente} · {' '.join(partes)}"
        if partes:
            return " ".join(partes)
        if cliente:
            return cliente
    return ""


def record_apontamento_total(maq_id: int, total: int) -> None:
    """
    Grava um snapshot de apontamento após total produzido válido.
    Falhas no DB não interrompem o MES (JSON continua fonte operacional).
    """
    try:
        from database.database import SessionLocal
        from database.models import Apontamento
    except Exception as exc:  # pragma: no cover - ambiente sem deps
        logger.warning("SQLite indisponível: %s", exc)
        return

    dm = dados_maquinas.get(maq_id) or {}
    operador = str(dm.get("operador_atual") or "").strip()
    turno = str(dm.get("turno_atual") or "").strip()
    status = str(dm.get("status") or "").strip()
    produto = _produto_pedido_corrente(maq_id) or "—"

    row = Apontamento(
        maquina=int(maq_id),
        operador=operador[:200],
        produto=produto[:500],
        quantidade=int(total),
        status=status[:80],
        horario=datetime.now(),
        turno=turno[:80],
    )

    try:
        with SessionLocal() as session:
            session.add(row)
            session.commit()
    except Exception as exc:
        logger.warning("Falha ao gravar apontamento (máquina %s): %s", maq_id, exc)
