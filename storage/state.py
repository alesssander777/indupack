"""Estado operacional em memória (cache) — persistência em SQLite via mes_persist."""

from __future__ import annotations

# Dicts/listas mutáveis — outros módulos importam por referência
pedidos: dict = {}
produtos_cadastrados: list = []
dados_maquinas: dict = {}
resumo_fabrica: dict = {}


def ensure_operational_state_synced() -> bool:
    """
    Disco é fonte de verdade: se a memória ficou atrás (deploy, reload, F5),
    recarrega antes de montar a página.
    """
    import logging

    from storage.mes_persist import _load_disk_snapshot_minimal, _pedidos_count

    disk = _load_disk_snapshot_minimal()
    if disk is None:
        return False
    disk_n = _pedidos_count(disk[0])
    mem_n = _pedidos_count(pedidos)
    if disk_n > mem_n:
        logging.getLogger("indupack.mes_persist").warning(
            "Memória com %s pedidos, disco com %s — recarregando do volume",
            mem_n,
            disk_n,
        )
        reload_from_store()
        return True
    return False


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


def persist(*, allow_reduce: bool = False) -> bool:
    """
    Persiste estado operacional no SQLite + espelho dados.json.
    allow_reduce=True só em exclusão explícita de pedido na programação.
    """
    import logging

    from storage.mes_persist import _coalesce_with_disk, _pedidos_count, save_operational_state

    logger = logging.getLogger("indupack.mes_persist")

    merged_p, merged_m, can_save = _coalesce_with_disk(
        pedidos, dados_maquinas, allow_reduce=allow_reduce
    )
    pedidos.clear()
    pedidos.update(merged_p)
    dados_maquinas.clear()
    dados_maquinas.update(merged_m)

    if not can_save:
        logger.warning("Recarregando estado do disco após gravação bloqueada")
        reload_from_store()
        return False

    n = _pedidos_count(pedidos)
    ok = save_operational_state(
        pedidos,
        produtos_cadastrados,
        dados_maquinas,
        resumo_fabrica,
        allow_reduce=allow_reduce,
    )
    if ok:
        logger.info("Gravado: %s pedidos na fila", n)
    else:
        reload_from_store()
    return ok
