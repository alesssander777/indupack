"""Gerenciamento operacional de terminais tablet (presença, comandos, logs)."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from storage.state import dados_maquinas, persist

OFFLINE_ACEITO_MS = 120_000
LOG_MAX = 120
_COMANDO_TTL_MS = 300_000

_TIPO_TITULO: dict[str, str] = {
    "conexao": "Conexão estabelecida",
    "desconexao": "Comunicação perdida",
    "reconexao": "Reconexão",
    "heartbeat": "Sincronização",
    "operador": "Troca de operador",
    "producao_inicio": "Início de produção",
    "producao_parada": "Parada registrada",
    "producao_retomada": "Produção retomada",
    "producao_fim": "Pedido finalizado",
    "erro": "Ocorrência",
    "reinicio": "Reinício do terminal",
    "kiosk": "Modo kiosk",
    "manutencao": "Manutenção",
    "reinicio_remoto": "Reinício solicitado",
}


def _now_ms() -> int:
    return int(time.time() * 1000)


def _fmt_epoch_ms(ms: int) -> str:
    if ms <= 0:
        return "—"
    try:
        return datetime.fromtimestamp(ms / 1000.0).strftime("%d/%m/%Y %H:%M:%S")
    except (OSError, OverflowError, ValueError):
        return "—"


def _maquina(mid: int) -> dict | None:
    if mid not in dados_maquinas:
        return None
    return dados_maquinas[mid]


def _label_maquina(status: str) -> str:
    s = str(status or "PARADA").strip().upper()
    return {
        "RODANDO": "Operacional",
        "PARADA": "Parada",
        "MANUTENCAO": "Manutenção",
    }.get(s, s.title() if s else "Parada")


def _logs_list(m: dict) -> list:
    raw = m.get("tablet_logs")
    if not isinstance(raw, list):
        raw = []
        m["tablet_logs"] = raw
    return raw


def append_log(
    maquina_id: int,
    tipo: str,
    detalhe: str = "",
    *,
    origem: str = "terminal",
    titulo: str | None = None,
) -> None:
    m = _maquina(maquina_id)
    if not m:
        return
    tipo_k = str(tipo or "erro").strip().lower()[:40]
    logs = _logs_list(m)
    logs.append(
        {
            "ts": _now_ms(),
            "tipo": tipo_k,
            "titulo": titulo or _TIPO_TITULO.get(tipo_k, tipo_k.replace("_", " ").title()),
            "detalhe": str(detalhe or "").strip()[:280],
            "origem": str(origem or "terminal")[:24],
        }
    )
    del logs[: max(0, len(logs) - LOG_MAX)]
    persist()


def list_logs(maquina_id: int, limit: int = 80) -> list[dict]:
    m = _maquina(maquina_id)
    if not m:
        return []
    logs = list(_logs_list(m))
    logs.sort(key=lambda x: int(x.get("ts") or 0), reverse=True)
    out: list[dict] = []
    for row in logs[:limit]:
        ts = int(row.get("ts") or 0)
        out.append(
            {
                "ts": ts,
                "ts_txt": _fmt_epoch_ms(ts),
                "tipo": row.get("tipo") or "",
                "titulo": row.get("titulo") or "",
                "detalhe": row.get("detalhe") or "",
                "origem": row.get("origem") or "",
            }
        )
    return out


def registrar_heartbeat(
    maquina_id: int,
    client_host: str | None,
    telemetry: dict[str, Any] | None = None,
) -> None:
    """Atualiza presença, bateria e detecta reconexão após offline."""
    m = _maquina(maquina_id)
    if not m:
        return
    now = _now_ms()
    prev = int(m.get("tablet_ultimo_acesso_epoch", 0) or 0)
    was_online = prev > 0 and (now - prev) <= OFFLINE_ACEITO_MS

    m["tablet_ultimo_acesso_epoch"] = now
    if client_host:
        m["tablet_ultimo_ip"] = str(client_host).strip()[:120]

    tel = telemetry if isinstance(telemetry, dict) else {}
    bat = tel.get("bateria_pct")
    if bat is not None and bat != "":
        try:
            pct = int(float(bat))
            pct = max(0, min(100, pct))
            m["tablet_bateria_pct"] = pct
        except (TypeError, ValueError):
            pass
    if "bateria_carregando" in tel:
        m["tablet_bateria_carregando"] = bool(tel.get("bateria_carregando"))

    if prev > 0 and not was_online:
        append_log(maquina_id, "reconexao", "Terminal voltou a comunicar com o servidor", origem="terminal")
    elif prev <= 0:
        append_log(maquina_id, "conexao", "Terminal conectado ao painel", origem="terminal")

    m["tablet_sessao_online"] = True
    persist()


def marcar_desconexao(maquina_id: int) -> None:
    m = _maquina(maquina_id)
    if not m:
        return
    if m.get("tablet_sessao_online"):
        append_log(maquina_id, "desconexao", "Sem comunicação com o servidor", origem="terminal")
        m["tablet_sessao_online"] = False
        persist()


def serializar_terminal_tablet(maquina_id: int) -> dict:
    """Bloco enviado ao tablet em /tablet/estado (comandos e modos)."""
    m = _maquina(maquina_id) or {}
    now = _now_ms()
    rein = int(m.get("tablet_reiniciar_em", 0) or 0)
    rein_ok = int(m.get("tablet_reiniciar_ok_em", 0) or 0)
    reiniciar = rein > rein_ok and (now - rein) < _COMANDO_TTL_MS
    return {
        "manutencao": bool(m.get("tablet_manutencao")),
        "manutencao_msg": str(m.get("tablet_manutencao_msg") or "TERMINAL EM MANUTENÇÃO").strip(),
        "kiosk": bool(m.get("tablet_kiosk")),
        "reiniciar": reiniciar,
        "bateria_pct": m.get("tablet_bateria_pct"),
        "bateria_carregando": bool(m.get("tablet_bateria_carregando")),
    }


def consumir_reinicio_tablet(maquina_id: int) -> None:
    m = _maquina(maquina_id)
    if not m:
        return
    rein = int(m.get("tablet_reiniciar_em", 0) or 0)
    if rein > 0:
        m["tablet_reiniciar_ok_em"] = _now_ms()
        persist()


def _bateria_label(m: dict) -> tuple[str, str]:
    raw = m.get("tablet_bateria_pct")
    if raw is None or raw == "":
        return "—", "indisponivel"
    try:
        pct = int(raw)
    except (TypeError, ValueError):
        return "—", "indisponivel"
    pct = max(0, min(100, pct))
    carregando = bool(m.get("tablet_bateria_carregando"))
    if carregando:
        return f"{pct}% · carregando", "carregando"
    if pct <= 15:
        return f"{pct}% · baixa", "baixa"
    return f"{pct}%", "ok"


def _terminal_status_label(*, online: bool, manutencao: bool) -> str:
    if manutencao:
        return "Em manutenção"
    if online:
        return "Online"
    return "Sem comunicação"


def _terminal_status_tom(*, online: bool, manutencao: bool) -> str:
    if manutencao:
        return "warn"
    if online:
        return "ok"
    return "off"


def listagem_terminais_admin(now_ms: int | None = None) -> list[dict]:
    if now_ms is None:
        now_ms = _now_ms()
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
        manut = bool(dm.get("tablet_manutencao"))
        kiosk = bool(dm.get("tablet_kiosk"))
        bat_txt, bat_tom = _bateria_label(dm)
        ago = (now_ms - last) // 1000 if last > 0 else -1
        rows.append(
            {
                "maquina_id": mid,
                "identificador": ident,
                "maquina_nome": titulo_maq,
                "tablet_codigo": vid,
                "online": online,
                "ultimo_acesso_ms": last,
                "ultimo_acesso_txt": _fmt_epoch_ms(last),
                "heartbeat_seg": ago if ago >= 0 else None,
                "ip": ip if ip else "—",
                "operador": op if op else "—",
                "operador_status_label": op.upper() if op else "Sem operador",
                "maquina_status": st,
                "maquina_status_label": _label_maquina(st),
                "maquina_status_tom": "ok" if st == "RODANDO" else ("warn" if st == "MANUTENCAO" else "neutral"),
                "terminal_status_label": _terminal_status_label(online=online, manutencao=manut),
                "terminal_status_tom": _terminal_status_tom(online=online, manutencao=manut),
                "terminal_conexao_label": "Online" if online else "Offline",
                "manutencao": manut,
                "kiosk": kiosk,
                "bateria_txt": bat_txt,
                "bateria_tom": bat_tom,
            }
        )
    return rows


def solicitar_reinicio(maquina_id: int, usuario: str = "") -> dict:
    m = _maquina(maquina_id)
    if not m:
        return {"ok": False, "erro": "maquina_nao_encontrada"}
    m["tablet_reiniciar_em"] = _now_ms()
    quem = str(usuario or "Supervisão").strip()[:80]
    append_log(maquina_id, "reinicio_remoto", f"Solicitado por {quem}", origem="supervisao")
    persist()
    return {"ok": True, "mensagem": "Comando enviado ao terminal. A página será recarregada no dispositivo."}


def set_kiosk(maquina_id: int, ativo: bool, usuario: str = "") -> dict:
    m = _maquina(maquina_id)
    if not m:
        return {"ok": False, "erro": "maquina_nao_encontrada"}
    m["tablet_kiosk"] = bool(ativo)
    quem = str(usuario or "Supervisão").strip()[:80]
    append_log(
        maquina_id,
        "kiosk",
        f"Modo kiosk {'ativado' if ativo else 'desativado'} — {quem}",
        origem="supervisao",
    )
    persist()
    return {"ok": True, "kiosk": bool(ativo)}


def set_manutencao(maquina_id: int, ativo: bool, usuario: str = "") -> dict:
    m = _maquina(maquina_id)
    if not m:
        return {"ok": False, "erro": "maquina_nao_encontrada"}
    m["tablet_manutencao"] = bool(ativo)
    if ativo and not str(m.get("tablet_manutencao_msg") or "").strip():
        m["tablet_manutencao_msg"] = "TERMINAL EM MANUTENÇÃO"
    quem = str(usuario or "Supervisão").strip()[:80]
    append_log(
        maquina_id,
        "manutencao",
        f"Manutenção {'ativada' if ativo else 'encerrada'} — {quem}",
        origem="supervisao",
    )
    persist()
    return {"ok": True, "manutencao": bool(ativo)}


def tablet_em_manutencao(maquina_id: int) -> bool:
    m = _maquina(maquina_id)
    return bool(m and m.get("tablet_manutencao"))


def bloqueio_manutencao_resposta() -> dict:
    return {
        "ok": False,
        "erro": "terminal_manutencao",
        "mensagem": "Terminal em manutenção — operação bloqueada pela supervisão.",
    }


def registrar_evento_tablet(maquina_id: int, tipo: str, detalhe: str = "") -> dict:
    allowed = frozenset(
        {
            "operador",
            "producao_inicio",
            "producao_parada",
            "producao_retomada",
            "producao_fim",
            "erro",
            "heartbeat",
        }
    )
    t = str(tipo or "").strip().lower()
    if t not in allowed:
        return {"ok": False, "erro": "tipo_invalido"}
    append_log(maquina_id, t, detalhe, origem="terminal")
    return {"ok": True}
