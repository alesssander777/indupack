from datetime import date, datetime

from services import fabrica_dia, maquinas
from storage.state import dados_maquinas, pedidos, persist


def normalizar_turno_operacional(t: str) -> str:
    """Alinha turno do cadastro ao formato da programação (TURNO A/B/C ou COMERCIAL)."""
    raw = str(t or "").strip()
    if not raw:
        return ""
    s = raw.upper()
    if "COMERCIAL" in s:
        return "COMERCIAL"
    core = s.replace("TURNO", "").strip()
    if core in ("A", "B", "C"):
        return f"TURNO {core}"
    if s.startswith("TURNO ") and len(s) >= 8:
        return s
    return s


def salvar_pedido(
    id: int,
    cliente: str = "",
    produto: str = "",
    quantidade: int = 0,
    fardos: int = 0,
    descricao: str = "",
):
    data_hoje = datetime.now().strftime("%d/%m")

    if id not in pedidos:
        pedidos[id] = []

    if produto:
        partes = produto.split(" ")
        cod = partes[0] if len(partes) > 0 else ""
        medida = " ".join(partes[1:-1]) if len(partes) > 2 else produto
        peso = partes[-1] if len(partes) > 1 else ""
        medida_final = f"{medida} - {peso}"
    else:
        cod = ""
        medida_final = ""

    pedidos[id].append(
        {
            "data": data_hoje,
            "cliente": cliente,
            "cod": cod,
            "produto": medida_final,
            "quantidade": int(quantidade),
            "fardos": int(fardos),
            "descricao": descricao,
        }
    )

    persist()
    return {"ok": True}


def editar_pedido(id: int, index: int, campo, valor):
    if id not in pedidos:
        return {"ok": False, "erro": "maquina_nao_encontrada"}

    if index < 0 or index >= len(pedidos[id]):
        return {"ok": False, "erro": "index_invalido"}

    if not campo:
        return {"ok": False, "erro": "campo_invalido"}

    if campo in ("quantidade", "fardos"):
        try:
            valor = int(valor)
        except (TypeError, ValueError):
            valor = 0

    primeiro_aberto_antes = -1
    if campo == "finalizado":
        primeiro_aberto_antes = indice_primeiro_pedido_aberto(id)

    pedidos[id][index][campo] = valor

    if campo == "finalizado":
        marcar_on = (
            valor is True
            or valor == 1
            or (isinstance(valor, str) and valor.lower() in ("true", "1", "on", "yes"))
        )
        if marcar_on:
            p = pedidos[id][index]
            p["finalizado"] = True
            if not p.get("hora_finalizacao"):
                p["hora_finalizacao"] = datetime.now().strftime("%d/%m %H:%M:%S")
            p["data_final_iso"] = date.today().isoformat()
            if "producao_total_final" not in p:
                try:
                    p["producao_total_final"] = int(p.get("quantidade") or 0)
                except (TypeError, ValueError):
                    p["producao_total_final"] = 0

    persist()
    if campo == "finalizado":
        fabrica_dia.garantir_dia_para_leitura()
        if marcar_on and primeiro_aberto_antes == index:
            if str(dados_maquinas.get(id, {}).get("status", "")).upper() == "RODANDO":
                maquinas.set_status(id, "PARADA")
            maquinas.set_produzido_total(id, 0)
            maquinas.reset_tempo_producao(id)
        maquinas.invalidar_pedido_atual_fp(id)
        maquinas.alinhar_contadores_ordem_atual(id)
    return {"ok": True}


def deletar_pedido(id: int, index: int):
    if id not in pedidos:
        return {"ok": False, "erro": "maquina_nao_encontrada"}

    if index < 0 or index >= len(pedidos[id]):
        return {"ok": False, "erro": "index_invalido"}

    pedidos[id].pop(index)
    persist()
    maquinas.invalidar_pedido_atual_fp(id)
    maquinas.alinhar_contadores_ordem_atual(id)
    return {"ok": True}


def novo_pedido(id: int):
    if id not in pedidos:
        pedidos[id] = []

    pedidos[id].append(
        {
            "cliente": "",
            "produto": "",
            "quantidade": 0,
            "fardos": 0,
            "descricao": "",
        }
    )

    persist()
    return {"ok": True}


def reordenar_pedidos(id: int, indices: list):
    if id not in pedidos:
        return {"ok": False, "erro": "maquina_nao_encontrada"}

    lst = pedidos[id]
    n = len(lst)

    if not isinstance(indices, list) or len(indices) != n:
        return {"ok": False, "erro": "tamanho_invalido"}

    try:
        idxs = [int(i) for i in indices]
    except (TypeError, ValueError):
        return {"ok": False, "erro": "indices_invalidos"}

    if sorted(idxs) != list(range(n)):
        return {"ok": False, "erro": "permutacao_invalida"}

    pedidos[id] = [lst[i] for i in idxs]
    persist()
    maquinas.invalidar_pedido_atual_fp(id)
    maquinas.alinhar_contadores_ordem_atual(id)
    return {"ok": True}


def iniciar_producao_tablet(
    id: int,
    operador: str = "",
    turno: str = "",
    retomar: bool = False,
    operador_perfil_id: int | None = None,
):
    """Inicia ou retoma RODANDO. Modal nome/turno só no 1º início; retomar usa dados gravados no pedido."""
    ix = indice_primeiro_pedido_aberto(id)
    if ix < 0:
        return {"ok": False, "erro": "nenhum_pedido_em_aberto"}
    lista = pedidos[id]
    p = lista[ix]

    if retomar:
        op = str(p.get("operador_inicio") or "").strip()
        tu = normalizar_turno_operacional(str(p.get("turno_inicio") or ""))
        if not tu:
            tu = str(p.get("turno_inicio") or "").strip()
        if not op or not tu:
            return {"ok": False, "erro": "sem_registro_inicio_retomar"}
    else:
        oid = operador_perfil_id
        if oid is not None:
            from services import config_params_db

            prof = config_params_db.get_operator_profile(oid)
            if not prof:
                return {"ok": False, "erro": "operador_invalido"}
            op = str(prof.get("nome") or "").strip()
            tu = normalizar_turno_operacional(str(prof.get("turno_padrao") or ""))
            if not tu:
                tu = normalizar_turno_operacional(str(turno or ""))
            if not tu:
                tu = str(turno or "").strip().upper()
            if not op or not tu:
                return {"ok": False, "erro": "operador_turno_obrigatorios"}
        else:
            op = str(operador or "").strip()
            tu = normalizar_turno_operacional(str(turno or ""))
            if not tu:
                tu = str(turno or "").strip().upper()
            if not op or not tu:
                return {"ok": False, "erro": "operador_turno_obrigatorios"}
        if not str(p.get("operador_inicio") or "").strip():
            p["operador_inicio"] = op
            p["turno_inicio"] = tu
            p["hora_inicio_operacao"] = datetime.now().strftime("%d/%m %H:%M:%S")
            if oid is not None:
                p["operador_perfil_id_inicio"] = oid
            persist()

    try:
        qmeta = int(p.get("quantidade") or 0)
    except (TypeError, ValueError):
        qmeta = 0
    if qmeta <= 0:
        qmeta = int(dados_maquinas.get(id, {}).get("meta", 1000) or 1000)
    if qmeta <= 0:
        qmeta = 1000
    maquinas.update_contexto(
        id,
        {"operador_atual": op, "turno_atual": tu, "meta": qmeta},
    )
    maquinas.set_status(id, "RODANDO")
    try:
        from services import terminais

        acao = "Produção retomada" if retomar else "Início de produção"
        terminais.append_log(id, "producao_inicio" if not retomar else "producao_retomada", f"{acao} — {op}", origem="terminal")
    except Exception:
        pass
    return {"ok": True}


def indice_primeiro_pedido_aberto(id: int) -> int:
    """Primeiro pedido não finalizado na sequência (tablet só opera este índice)."""
    if id not in pedidos:
        return -1
    lista = pedidos[id]
    for i, p in enumerate(lista):
        if not bool(p.get("finalizado")):
            return i
    return -1


def finalizar_pedido_tablet(
    id: int,
    index: int,
    operador_final: str,
    producao_final: int,
    turno_final: str = "",
    operador_perfil_id: int | None = None,
):
    oid = operador_perfil_id
    if oid is not None:
        from services import config_params_db

        prof = config_params_db.get_operator_profile(oid)
        if not prof:
            return {"ok": False, "erro": "operador_invalido"}
        of = str(prof.get("nome") or "").strip()
        tf = normalizar_turno_operacional(str(prof.get("turno_padrao") or ""))
        if not tf:
            tf = normalizar_turno_operacional(str(turno_final or ""))
        if not tf:
            tf = str(turno_final or "").strip().upper()
    else:
        of = str(operador_final or "").strip()
        tf = normalizar_turno_operacional(str(turno_final or ""))
        if not tf:
            tf = str(turno_final or "").strip().upper()
    if not of or not tf:
        return {"ok": False, "erro": "operador_turno_obrigatorios"}
    if id not in pedidos:
        return {"ok": False, "erro": "maquina_nao_encontrada"}
    esperado = indice_primeiro_pedido_aberto(id)
    if esperado < 0:
        return {"ok": False, "erro": "nenhum_pedido_em_aberto"}
    if index != esperado:
        return {"ok": False, "erro": "sequencia_invalida"}
    if index < 0 or index >= len(pedidos[id]):
        return {"ok": False, "erro": "index_invalido"}

    p = pedidos[id][index]
    p["finalizado"] = True
    p["operador_final"] = of
    p["turno_final"] = tf
    if oid is not None:
        p["operador_perfil_id_final"] = oid
    p["hora_finalizacao"] = datetime.now().strftime("%d/%m %H:%M:%S")
    p["data_final_iso"] = date.today().isoformat()
    try:
        p["producao_total_final"] = int(producao_final)
    except (TypeError, ValueError):
        p["producao_total_final"] = 0

    persist()
    fabrica_dia.garantir_dia_para_leitura()
    # Contador da máquina é só do pedido atual; ao finalizar, zera para o próximo.
    maquinas.set_produzido_total(id, 0)
    maquinas.reset_tempo_producao(id)
    # Terminal não deve ficar “RODANDO” sem pedido ativo — operador precisa iniciar de novo no próximo.
    maquinas.set_status(id, "PARADA")
    maquinas.invalidar_pedido_atual_fp(id)
    maquinas.alinhar_contadores_ordem_atual(id)
    try:
        from services import terminais

        prod = str(p.get("produto") or p.get("cod") or "").strip()
        terminais.append_log(
            id,
            "producao_fim",
            f"Pedido finalizado — {of}" + (f" · {prod}" if prod else ""),
            origem="terminal",
        )
    except Exception:
        pass
    return {"ok": True}
