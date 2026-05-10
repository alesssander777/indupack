"""Listagem administrativa de terminais tablet (vinculados às máquinas)."""

from __future__ import annotations

import time
from datetime import datetime

from storage.state import dados_maquinas

# Sem ping há este intervalo → exibido como offline (tablet faz poll em /tablet/estado).
OFFLINE_ACEITO_MS = 120_000


def _fmt_epoch_ms(ms: int) -> str:
    if ms <= 0:
        return "—"
    try:
        dt = datetime.fromtimestamp(ms / 1000.0)
        return dt.strftime("%d/%m/%Y %H:%M:%S")
    except (OSError, OverflowError, ValueError):
        return "—"


def listagem_terminais_admin(now_ms: int | None = None) -> list[dict]:
    if now_ms is None:
        now_ms = int(time.time() * 1000)
    rows: list[dict] = []
    for mid in sorted(dados_maquinas.keys()):
        dm = dados_maquinas[mid]
        vid = str(dm.get("tablet_vinculado") or "").strip()
        nome_m = str(dm.get("nome") or "").strip()
        titulo_maq = nome_m if nome_m else f"Máquina {mid}"
        ident = vid if vid else f"Terminal máquina {mid}"
        last = int(dm.get("tablet_ultimo_acesso_epoch", 0) or 0)
        online = last > 0 and (now_ms - last) <= OFFLINE_ACEITO_MS
        st = str(dm.get("status", "PARADA") or "PARADA").strip().upper()
        op = str(dm.get("operador_atual") or "").strip()
        ip = str(dm.get("tablet_ultimo_ip") or "").strip()
        rows.append(
            {
                "maquina_id": mid,
                "identificador": ident,
                "maquina_nome": titulo_maq,
                "tablet_codigo": vid,
                "online": online,
                "ultimo_acesso_ms": last,
                "ultimo_acesso_txt": _fmt_epoch_ms(last),
                "ip": ip if ip else "—",
                "operador": op if op else "—",
                "maquina_status": st,
            }
        )
    return rows
