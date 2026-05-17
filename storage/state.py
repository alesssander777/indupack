"""Estado operacional em memória (cache) — persistência em SQLite via mes_persist."""

from __future__ import annotations

# Dicts/listas mutáveis — outros módulos importam por referência
pedidos: dict = {}
produtos_cadastrados: list = []
dados_maquinas: dict = {}
resumo_fabrica: dict = {}


def reload_from_store() -> None:
    """Recarrega pedidos/máquinas do SQLite (ou migra JSON legado)."""
    from storage.mes_persist import load_operational_state

    p, prod, maq, rf = load_operational_state()
    pedidos.clear()
    pedidos.update(p)
    produtos_cadastrados.clear()
    produtos_cadastrados.extend(prod)
    dados_maquinas.clear()
    dados_maquinas.update(maq)
    resumo_fabrica.clear()
    resumo_fabrica.update(rf)


def persist() -> None:
    """Persiste estado operacional no SQLite + espelho dados.json."""
    import logging

    from storage.mes_persist import _pedidos_count, save_operational_state

    logger = logging.getLogger("indupack.mes_persist")
    n = _pedidos_count(pedidos)
    save_operational_state(pedidos, produtos_cadastrados, dados_maquinas, resumo_fabrica)
    logger.info("Gravado: %s pedidos na fila | volume OK", n)
