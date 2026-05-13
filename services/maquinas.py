import time

from storage.state import dados_maquinas, pedidos, persist


def _now_ms() -> int:
    return int(time.time() * 1000)


def ids_maquinas_ordenadas() -> list[int]:
    """Máquinas ativas (chão de fábrica / home / produção)."""
    out = []
    for mid in sorted(dados_maquinas.keys()):
        m = dados_maquinas.get(mid) or {}
        if m.get("ativo", True) is False:
            continue
        out.append(mid)
    return out


def ids_todas_maquinas_ordenadas() -> list[int]:
    """Todas as máquinas cadastradas (admin / configurações)."""
    return sorted(dados_maquinas.keys())


def proximo_id_maquina_livre() -> int:
    if not dados_maquinas:
        return 1
    return max(dados_maquinas.keys()) + 1


def criar_maquina(
    id: int,
    nome: str = "",
    setor: str = "",
    meta_padrao: int = 1000,
    status_inicial: str = "PARADA",
    observacao: str = "",
    tablet_vinculado: str = "",
) -> dict:
    """Registra nova máquina no armazenamento e fila de pedidos vazia."""
    try:
        mid = int(id)
    except (TypeError, ValueError):
        return {"ok": False, "erro": "id_invalido"}
    if mid < 1:
        return {"ok": False, "erro": "id_invalido"}
    if mid in dados_maquinas:
        return {"ok": False, "erro": "id_duplicado"}

    st = str(status_inicial or "PARADA").strip().upper()
    if st == "MANUTENCAO":
        st = "MANUTENÇÃO"
    if st not in ("PARADA", "RODANDO", "MANUTENÇÃO"):
        st = "PARADA"

    try:
        meta = int(meta_padrao)
    except (TypeError, ValueError):
        meta = 1000
    if meta < 1:
        meta = 1000

    dados_maquinas[mid] = {
        "produzido": 0,
        "meta": meta,
        "status": st,
        "nome": str(nome or "").strip(),
        "setor": str(setor or "").strip(),
        "observacao": str(observacao or "").strip(),
        "tablet_vinculado": str(tablet_vinculado or "").strip(),
        "ativo": True,
    }
    if mid not in pedidos:
        pedidos[mid] = []
    persist()
    return {"ok": True, "id": mid}


def add_producao(id: int, valor: int):
    if id not in dados_maquinas:
        return {"ok": False, "erro": "maquina_nao_encontrada"}
    v = int(valor)
    if v <= 0:
        return {"ok": False, "erro": "valor_invalido"}
    if str(dados_maquinas[id].get("status", "")).upper() != "RODANDO":
        return {"ok": False, "erro": "maquina_parada"}
    dados_maquinas[id]["produzido"] += v
    persist()
    return {"ok": True}


def _append_historico_parada(m: dict, now: int) -> None:
    """Ao retomar (PARADA→RODANDO), fecha o período de parada e grava histórico."""
    pe = int(m.get("parada_inicio_epoch", 0) or 0)
    if pe <= 0:
        return
    dur = max(0, (now - pe) // 1000)
    m["paradas_total_s"] = int(m.get("paradas_total_s", 0) or 0) + dur
    hist = m.get("historico_paradas")
    if not isinstance(hist, list):
        hist = []
    motivo = str(m.get("motivo_parada") or "").strip()
    op_p = str(m.get("pausa_operador") or m.get("operador_atual") or "").strip()
    tu_p = str(m.get("pausa_turno") or m.get("turno_atual") or "").strip()
    hist.append(
        {
            "inicio_epoch": pe,
            "retorno_epoch": now,
            "duracao_s": dur,
            "motivo": motivo,
            "operador": op_p,
            "turno": tu_p,
        }
    )
    m["historico_paradas"] = hist[-300:]
    m["motivo_parada"] = ""
    m["parada_inicio_epoch"] = 0
    m["pausa_operador"] = ""
    m["pausa_turno"] = ""
    m["ultimo_retorno_epoch"] = now


def set_status(id: int, novo: str):
    if id not in dados_maquinas:
        return {"ok": False, "erro": "maquina_nao_encontrada"}
    m = dados_maquinas[id]
    now = _now_ms()
    st = str(novo).upper()
    cur = str(m.get("status", "PARADA")).upper()
    if st == "PARADA" and cur == "RODANDO":
        epoch = int(m.get("producao_sessao_epoch", 0) or 0)
        if epoch > 0:
            m["tempo_producao_s"] = int(m.get("tempo_producao_s", 0) or 0) + max(0, (now - epoch) // 1000)
        m["producao_sessao_epoch"] = 0
    elif st == "RODANDO" and cur == "PARADA":
        _append_historico_parada(m, now)
        if int(m.get("producao_sessao_epoch", 0) or 0) <= 0:
            m["producao_sessao_epoch"] = now
    elif st == "RODANDO" and cur != "RODANDO":
        if int(m.get("producao_sessao_epoch", 0) or 0) <= 0:
            m["producao_sessao_epoch"] = now
    m["status"] = novo
    persist()
    return {"ok": True}


def reset_tempo_producao(id: int):
    if id not in dados_maquinas:
        return
    m = dados_maquinas[id]
    m["tempo_producao_s"] = 0
    m["producao_sessao_epoch"] = 0


def fingerprint_pedido_operacional(maq_id: int) -> str:
    """Identifica o pedido atualmente operável (primeiro não finalizado) na sequência."""
    lista = pedidos.get(maq_id) or []
    for i, p in enumerate(lista):
        if not bool(p.get("finalizado")):
            def _s(k: str) -> str:
                return str(p.get(k) or "").strip()

            q = p.get("quantidade", "")
            return f"{i}|{_s('data')}|{_s('cod')}|{_s('cliente')}|{q}"
    return "__vazio__"


def alinhar_contadores_ordem_atual(maq_id: int) -> bool:
    """
    Se a OS/pedido operacional mudou (troca de fila, finalização, novo pedido),
    zera medições da ordem anterior na máquina — espelho do MES real.
    Retorna True se aplicou reset.
    """
    if maq_id not in dados_maquinas:
        return False
    fp = fingerprint_pedido_operacional(maq_id)
    m = dados_maquinas[maq_id]
    prev = str(m.get("pedido_atual_fp") or "")
    if fp == prev:
        return False
    try:
        from services.runtime_config import production_flags

        if not production_flags().get("reset_os_automatico", True):
            m["pedido_atual_fp"] = fp
            persist()
            return False
    except Exception:
        pass
    m["pedido_atual_fp"] = fp
    m["produzido"] = 0
    reset_tempo_producao(maq_id)
    m["motivo_parada"] = ""
    m["parada_inicio_epoch"] = 0
    m["operador_atual"] = ""
    m["turno_atual"] = ""
    m["hora_inicio"] = ""
    persist()
    return True


def invalidar_pedido_atual_fp(maq_id: int) -> None:
    """Força reavaliação na próxima leitura (ex.: após finalizar manualmente)."""
    if maq_id in dados_maquinas:
        dados_maquinas[maq_id]["pedido_atual_fp"] = ""


def registrar_presenca_tablet(maquina_id: int, client_host: str | None) -> None:
    """Atualiza último contato do terminal operacional (para painel /tablets)."""
    if maquina_id not in dados_maquinas:
        return
    m = dados_maquinas[maquina_id]
    m["tablet_ultimo_acesso_epoch"] = _now_ms()
    if client_host:
        m["tablet_ultimo_ip"] = str(client_host).strip()[:120]
    persist()


def set_produzido_total(id: int, total: int, exige_rodando: bool = False):
    if id not in dados_maquinas:
        return {"ok": False, "erro": "maquina_nao_encontrada"}
    if exige_rodando and str(dados_maquinas[id].get("status", "")).upper() != "RODANDO":
        return {"ok": False, "erro": "maquina_parada"}
    if total < 0:
        total = 0
    new = int(total)
    dados_maquinas[id]["produzido"] = new
    persist()
    try:
        from services import db_apontamento

        db_apontamento.record_apontamento_total(id, new)
    except Exception:
        pass
    return {"ok": True}


def update_contexto(id: int, payload: dict):
    if id not in dados_maquinas:
        return {"ok": False, "erro": "maquina_nao_encontrada"}
    if not isinstance(payload, dict):
        return {"ok": False, "erro": "payload_invalido"}

    allowed = {
        "operador_atual",
        "turno_atual",
        "hora_inicio",
        "motivo_parada",
        "parada_inicio_epoch",
        "pausa_operador",
        "pausa_turno",
        "paradas_total_s",
        "ultimo_retorno_epoch",
        "status",
        "meta",
        "tempo_producao_s",
        "producao_sessao_epoch",
    }
    for k, v in payload.items():
        if k in allowed:
            dados_maquinas[id][k] = v

    persist()
    return {"ok": True}


def listar_maquinas_para_config() -> list[dict]:
    """Lista todas as máquinas para o painel de parâmetros (sem monitoramento)."""
    out: list[dict] = []
    for mid in ids_todas_maquinas_ordenadas():
        m = dados_maquinas.get(mid) or {}
        try:
            meta = int(m.get("meta", 1000) or 1000)
        except (TypeError, ValueError):
            meta = 1000
        out.append(
            {
                "id": mid,
                "nome": str(m.get("nome") or ""),
                "setor": str(m.get("setor") or ""),
                "meta": meta,
                "ativo": bool(m.get("ativo", True)),
                "status": str(m.get("status") or "PARADA"),
                "tablet_vinculado": str(m.get("tablet_vinculado") or ""),
            }
        )
    return out


def atualizar_maquina_config(
    mid: int,
    nome: str = "",
    setor: str = "",
    meta: int | None = None,
    ativo: bool | None = None,
) -> dict:
    if mid not in dados_maquinas:
        return {"ok": False, "erro": "maquina_nao_encontrada"}
    m = dados_maquinas[mid]
    m["nome"] = str(nome or "").strip()
    m["setor"] = str(setor or "").strip()
    if meta is not None:
        try:
            meta_i = int(meta)
        except (TypeError, ValueError):
            meta_i = int(m.get("meta", 1000) or 1000)
        m["meta"] = max(1, meta_i)
    if ativo is not None:
        m["ativo"] = bool(ativo)
    persist()
    return {"ok": True}
