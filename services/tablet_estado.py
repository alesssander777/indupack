"""Estado serializado para a interface tablet (pedidos + máquina)."""

from datetime import date

from services import fabrica_dia, maquinas, terminais
from services.fabrica_dia import total_producao_pedidos_finalizados_maquina_no_dia
from storage.state import dados_maquinas, pedidos


def _fardos_serial(raw) -> int | str:
    if raw is None or raw == "":
        return ""
    try:
        n = int(float(raw))
        return n if n >= 0 else ""
    except (TypeError, ValueError):
        return ""


def _pedido_serial(p: dict) -> dict:
    out = {
        "cliente": p.get("cliente") or "",
        "cod": p.get("cod") or "",
        "produto": p.get("produto") or "",
        "quantidade": p.get("quantidade", ""),
        "fardos": _fardos_serial(p.get("fardos")),
        "etiqueta": p.get("etiqueta") or "",
        "descricao": p.get("descricao") or "",
        "data": p.get("data") or "",
        "finalizado": bool(p.get("finalizado")),
        "etiqueta_feita": bool(p.get("etiqueta_feita")),
    }
    if "producao_total_final" in p:
        try:
            out["producao_total_final"] = int(p.get("producao_total_final") or 0)
        except (TypeError, ValueError):
            out["producao_total_final"] = 0
    for k in ("operador_inicio", "turno_inicio", "hora_inicio_operacao", "operador_final", "turno_final"):
        if p.get(k):
            out[k] = str(p.get(k) or "").strip()
    return out


def estado_tablet(maquina_id: int) -> dict:
    fabrica_dia.garantir_dia_para_leitura()
    maquinas.alinhar_contadores_ordem_atual(maquina_id)
    lista = pedidos.get(maquina_id, [])
    dm = dados_maquinas.get(maquina_id, {})
    hp = dm.get("historico_paradas")
    if not isinstance(hp, list):
        hp = []
    producao_dia_maq = total_producao_pedidos_finalizados_maquina_no_dia(maquina_id, date.today())
    return {
        "ok": True,
        "producao_dia_maquina": int(producao_dia_maq),
        "pedidos": [_pedido_serial(p) for p in lista],
        "terminal": terminais.serializar_terminal_tablet(maquina_id),
        "maquina": {
            "id": int(maquina_id),
            "nome": str(dm.get("nome") or "").strip(),
            "setor": str(dm.get("setor") or "").strip(),
            "observacao": str(dm.get("observacao") or "").strip(),
            "tablet_vinculado": str(dm.get("tablet_vinculado") or "").strip(),
            "status": str(dm.get("status", "PARADA")),
            "produzido": int(dm.get("produzido", 0) or 0),
            "meta": int(dm.get("meta", 1000) or 1000),
            "operador_atual": dm.get("operador_atual") or "",
            "turno_atual": dm.get("turno_atual") or "",
            "hora_inicio": dm.get("hora_inicio") or "",
            "motivo_parada": dm.get("motivo_parada") or "",
            "parada_inicio_epoch": int(dm.get("parada_inicio_epoch", 0) or 0),
            "paradas_total_s": int(dm.get("paradas_total_s", 0) or 0),
            "tempo_producao_s": int(dm.get("tempo_producao_s", 0) or 0),
            "producao_sessao_epoch": int(dm.get("producao_sessao_epoch", 0) or 0),
            "historico_paradas": hp[-80:],
        },
    }
