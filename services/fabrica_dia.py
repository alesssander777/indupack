"""Produção total do dia — soma dos pedidos finalizados hoje (todas as máquinas).

Não usa contador em tempo real da máquina nem quantidade do pedido em aberto.
Só entra no acumulado o que foi registrado ao finalizar pedido (tablet ou programação).
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from storage.state import pedidos, persist, resumo_fabrica


def _hoje() -> date:
    return date.today()


def _hoje_iso() -> str:
    return _hoje().isoformat()


def _parse_dd_mm_primeiro_token(s: str) -> Optional[date]:
    if not s or not isinstance(s, str):
        return None
    part = s.strip().split()[0]
    seg = part.split("/")
    if len(seg) != 2:
        return None
    try:
        d, m = int(seg[0]), int(seg[1])
    except ValueError:
        return None
    y = date.today().year
    try:
        return date(y, m, d)
    except ValueError:
        return None


def _data_referencia_finalizacao(p: dict) -> Optional[date]:
    iso = p.get("data_final_iso")
    if iso and isinstance(iso, str) and len(iso) >= 10:
        try:
            y, m, d = [int(x) for x in iso[:10].split("-")]
            return date(y, m, d)
        except (ValueError, TypeError):
            pass
    hf = p.get("hora_finalizacao")
    if hf:
        parsed = _parse_dd_mm_primeiro_token(str(hf))
        if parsed:
            return parsed
    dt = p.get("data")
    if dt:
        return _parse_dd_mm_primeiro_token(str(dt))
    return None


def _qtd_contabilizada_pedido_finalizado(p: dict) -> int:
    if "producao_total_final" in p:
        try:
            return max(0, int(p.get("producao_total_final") or 0))
        except (TypeError, ValueError):
            pass
    try:
        return max(0, int(p.get("quantidade") or 0))
    except (TypeError, ValueError):
        return 0


def total_producao_pedidos_finalizados_no_dia(d: date) -> int:
    total = 0
    for lista in pedidos.values():
        if not isinstance(lista, list):
            continue
        for p in lista:
            if not isinstance(p, dict) or not p.get("finalizado"):
                continue
            dref = _data_referencia_finalizacao(p)
            if dref != d:
                continue
            total += _qtd_contabilizada_pedido_finalizado(p)
    return total


def total_producao_pedidos_finalizados_maquina_no_dia(maquina_id: int, d: date) -> int:
    """Soma peças finalizadas hoje apenas na fila desta máquina (isolado por terminal)."""
    lista = pedidos.get(maquina_id, [])
    if not isinstance(lista, list):
        return 0
    total = 0
    for p in lista:
        if not isinstance(p, dict) or not p.get("finalizado"):
            continue
        dref = _data_referencia_finalizacao(p)
        if dref != d:
            continue
        total += _qtd_contabilizada_pedido_finalizado(p)
    return total


def garantir_dia_para_leitura() -> None:
    """Alinha dia_ref e produção do dia com a soma dos pedidos finalizados hoje (fonte da verdade)."""
    hoje = _hoje()
    hoje_iso = hoje.isoformat()
    novo_dia = resumo_fabrica.get("dia_ref") != hoje_iso
    resumo_fabrica["dia_ref"] = hoje_iso
    total = total_producao_pedidos_finalizados_no_dia(hoje)
    old = int(resumo_fabrica.get("producao_dia_total", 0) or 0)
    resumo_fabrica["producao_dia_total"] = total
    if novo_dia or old != total:
        persist()
