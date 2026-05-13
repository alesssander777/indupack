"""Dados exibidos nos cards de /producao: sempre o primeiro pedido da programação."""

from services import maquinas
from storage.state import dados_maquinas, pedidos


def _fmt_text(val) -> str:
    if val is None:
        return "---"
    if isinstance(val, str) and not val.strip():
        return "---"
    return str(val).strip()


def _fmt_tempo_parado_acumulado(dm: dict) -> str:
    """Tempo total em paradas acumulado (s) → HH:MM:SS ou —."""
    try:
        s = int(dm.get("paradas_total_s", 0) or 0)
    except (TypeError, ValueError):
        return "—"
    if s <= 0:
        return "—"
    h, r = divmod(max(0, s), 3600)
    m, s2 = divmod(r, 60)
    return f"{h:02d}:{m:02d}:{s2:02d}"


def _status_from_maquina(dm: dict) -> tuple[str, str, str, str]:
    """rótulo curto, cor hex, linha com emoji (painel), kind: run|stop|maint."""
    s = str(dm.get("status") or "PARADA").strip().upper()
    motivo = str(dm.get("motivo_parada") or "").lower()
    maint_por_motivo = "manuten" in motivo

    if s == "RODANDO":
        return "RODANDO", "#16a34a", "RODANDO", "run"
    if s in ("MANUTENÇÃO", "MANUTENCAO") or (s == "PARADA" and maint_por_motivo):
        return "MANUTENÇÃO", "#ca8a04", "MANUTENÇÃO", "maint"
    if s == "PARADA":
        return "PARADA", "#dc2626", "PARADA", "stop"
    return s or "PARADA", "#64748b", s or "PARADA", "stop"


def card_primeiro_pedido(maquina_id: int) -> dict:
    lista = pedidos.get(maquina_id, [])
    dm = dados_maquinas.get(maquina_id, {})
    produzido = int(dm.get("produzido", 0) or 0)
    meta_dm = int(dm.get("meta", 1000) or 1000)
    st_label, st_cor, st_line, st_kind = _status_from_maquina(dm)
    operador = _fmt_text(dm.get("operador_atual"))
    tempo_parado_txt = _fmt_tempo_parado_acumulado(dm)

    if not lista:
        alvo = meta_dm if meta_dm > 0 else 1000
        progress_pct = 0
        if alvo > 0:
            progress_pct = min(100, int(round(100 * produzido / alvo)))
        faltam = max(0, alvo - produzido)
        return {
            "cliente": "---",
            "produto": "---",
            "quantidade_txt": "---",
            "descricao": "---",
            "quantidade_meta": alvo,
            "status": st_label,
            "status_cor": st_cor,
            "status_line": st_line,
            "status_kind": st_kind,
            "produzido": produzido,
            "meta_maquina": meta_dm,
            "progress_pct": progress_pct,
            "alvo": alvo,
            "faltam": faltam,
            "eficiencia_pct": progress_pct,
            "operador_atual": operador,
            "tempo_parado_txt": tempo_parado_txt,
        }

    p = lista[0]
    cliente = _fmt_text(p.get("cliente"))
    produto = _fmt_text(p.get("produto"))
    descricao = _fmt_text(p.get("descricao"))

    raw_q = p.get("quantidade", None)
    quantidade_txt = "---"
    quantidade_meta = 1000
    if raw_q is not None and raw_q != "":
        try:
            qv = int(raw_q)
            quantidade_txt = str(qv)
            quantidade_meta = qv if qv > 0 else 1000
        except (TypeError, ValueError):
            quantidade_txt = "---"

    alvo = quantidade_meta if quantidade_meta and quantidade_meta > 0 else meta_dm
    if alvo <= 0:
        alvo = meta_dm if meta_dm > 0 else 1000
    progress_pct = 0
    if alvo and alvo > 0:
        progress_pct = min(100, int(round(100 * produzido / alvo)))
    faltam = max(0, alvo - produzido)

    return {
        "cliente": cliente,
        "produto": produto,
        "quantidade_txt": quantidade_txt,
        "descricao": descricao,
        "quantidade_meta": quantidade_meta,
        "status": st_label,
        "status_cor": st_cor,
        "status_line": st_line,
        "status_kind": st_kind,
        "produzido": produzido,
        "meta_maquina": meta_dm,
        "progress_pct": progress_pct,
        "alvo": alvo,
        "faltam": faltam,
        "eficiencia_pct": progress_pct,
        "operador_atual": operador,
        "tempo_parado_txt": tempo_parado_txt,
    }


def snapshot_todas_maquinas() -> dict:
    ids = maquinas.ids_maquinas_ordenadas()
    return {str(i): card_primeiro_pedido(i) for i in ids}
