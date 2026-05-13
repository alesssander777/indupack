"""Métricas consolidadas para a HOME (resumo de máquinas + produção diária da fábrica)."""

from services import maquinas
from services.fabrica_dia import garantir_dia_para_leitura
from services.producao_snapshot import _status_from_maquina
from storage.state import dados_maquinas, resumo_fabrica


def resumo_home() -> dict:
    garantir_dia_para_leitura()

    rodando = parada = manut = 0

    for i in maquinas.ids_maquinas_ordenadas():
        dm = dados_maquinas.get(i) or {}
        _, _, _, kind = _status_from_maquina(dm)
        if kind == "run":
            rodando += 1
        elif kind == "maint":
            manut += 1
        else:
            parada += 1

    produ_dia = int(resumo_fabrica.get("producao_dia_total", 0) or 0)
    produ_txt = f"{produ_dia:,}".replace(",", ".")

    return {
        "rodando": rodando,
        "paradas": parada,
        "manutencao": manut,
        "producao_dia_total": produ_dia,
        "producao_dia_total_txt": produ_txt,
        "producao_total_txt": produ_txt,
    }
