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
    from storage.mes_persist import save_operational_state

    save_operational_state(pedidos, produtos_cadastrados, dados_maquinas, resumo_fabrica)
