from fastapi import APIRouter, Request

from services import indupack_auth
from services import maquinas, pedidos, produtos
from services.producao_snapshot import snapshot_todas_maquinas
from services.tablet_estado import estado_tablet

router = APIRouter()


@router.get("/add/{id}/{valor}")
def add(request: Request, id: int, valor: int):
    err = indupack_auth.require_api_role(request, "add_producao")
    if err:
        return err
    return maquinas.add_producao(id, valor)


@router.get("/status/{id}/{novo}")
def status(request: Request, id: int, novo: str):
    from services import terminais

    if terminais.tablet_em_manutencao(id):
        return terminais.bloqueio_manutencao_resposta()
    return maquinas.set_status(id, novo)


@router.post("/maquina/contexto/{id}")
async def maquina_contexto(id: int, request: Request):
    from services import terminais

    if terminais.tablet_em_manutencao(id):
        return terminais.bloqueio_manutencao_resposta()
    body = await request.json()
    return maquinas.update_contexto(id, body if isinstance(body, dict) else {})


@router.post("/produzido_total/{id}")
async def produzido_total(id: int, request: Request):
    err = indupack_auth.require_api_role(request, "produzido_total")
    if err:
        return err
    body = await request.json()
    total = body.get("total", 0) if isinstance(body, dict) else 0
    try:
        total_i = int(total)
    except (TypeError, ValueError):
        total_i = 0
    return maquinas.set_produzido_total(id, total_i)


@router.post("/tablet/produzido_delta/{id}")
async def tablet_produzido_delta(id: int, request: Request):
    """Apontamento no tablet = total ABSOLUTO produzido (recontagem do pallet), não incremento."""
    from services import terminais

    if terminais.tablet_em_manutencao(id):
        return terminais.bloqueio_manutencao_resposta()
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        body = {}
    raw = body.get("total")
    if raw is None:
        return {"ok": False, "erro": "total_obrigatorio"}
    try:
        total_i = int(raw)
    except (TypeError, ValueError):
        return {"ok": False, "erro": "valor_invalido"}
    if total_i < 0:
        return {"ok": False, "erro": "valor_invalido"}
    return maquinas.set_produzido_total(id, total_i, exige_rodando=True)


@router.get("/add_produto")
def add_produto(request: Request, nome: str):
    err = indupack_auth.require_api_role(request, "add_produto")
    if err:
        return err
    return produtos.add_produto(nome)


@router.get("/salvar_pedido/{id}")
def salvar_pedido(
    request: Request,
    id: int,
    cliente: str = "",
    produto: str = "",
    quantidade: int = 0,
    fardos: int = 0,
    descricao: str = "",
):
    err = indupack_auth.require_api_role(request, "salvar_pedido")
    if err:
        return err
    return pedidos.salvar_pedido(
        id,
        cliente=cliente,
        produto=produto,
        quantidade=quantidade,
        fardos=fardos,
        descricao=descricao,
    )


@router.post("/editar/{id}/{index}")
async def editar_pedido(id: int, index: int, request: Request):
    err = indupack_auth.require_api_role(request, "editar_pedido")
    if err:
        return err
    dados = await request.json()
    campo = dados.get("campo")
    valor = dados.get("valor")
    return pedidos.editar_pedido(id, index, campo, valor)


@router.get("/deletar/{id}")
def deletar_pedido(request: Request, id: int, index: int = -1):
    err = indupack_auth.require_api_role(request, "deletar_pedido")
    if err:
        return err
    return pedidos.deletar_pedido(id, index)


@router.get("/novo_pedido/{id}")
def novo_pedido(request: Request, id: int):
    err = indupack_auth.require_api_role(request, "novo_pedido")
    if err:
        return err
    return pedidos.novo_pedido(id)


@router.post("/reordenar/{id}")
async def reordenar(id: int, request: Request):
    err = indupack_auth.require_api_role(request, "reordenar")
    if err:
        return err
    body = await request.json()
    indices = body.get("indices")
    if not isinstance(indices, list):
        return {"ok": False, "erro": "payload_invalido"}
    return pedidos.reordenar_pedidos(id, indices)


@router.get("/producao/atual")
def producao_atual(request: Request):
    err = indupack_auth.require_api_role(request, "producao_atual")
    if err:
        return err
    return snapshot_todas_maquinas()


@router.post("/maquinas")
async def criar_maquina_endpoint(request: Request):
    err = indupack_auth.require_api_role(request, "criar_maquina")
    if err:
        return err
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        return {"ok": False, "erro": "payload_invalido"}

    raw_id = body.get("id")
    if raw_id is None or raw_id == "":
        mid = maquinas.proximo_id_maquina_livre()
    else:
        try:
            mid = int(raw_id)
        except (TypeError, ValueError):
            return {"ok": False, "erro": "id_invalido"}

    return maquinas.criar_maquina(
        mid,
        nome=str(body.get("nome") or ""),
        setor=str(body.get("setor") or ""),
        meta_padrao=body.get("quantidade_maxima_padrao", body.get("meta_padrao", 1000)),
        status_inicial=str(body.get("status_inicial") or "PARADA"),
        observacao=str(body.get("observacao") or ""),
        tablet_vinculado=str(body.get("tablet_vinculado") or ""),
    )


@router.get("/tablet/estado/{id}")
def tablet_estado_endpoint(request: Request, id: int):
    host = request.client.host if request.client else None
    q = request.query_params
    telemetry: dict = {}
    if q.get("bateria") is not None:
        telemetry["bateria_pct"] = q.get("bateria")
    if q.get("carregando") is not None:
        telemetry["bateria_carregando"] = q.get("carregando") in ("1", "true", "True", "yes")
    maquinas.registrar_presenca_tablet(id, host, telemetry or None)
    return estado_tablet(id)


@router.post("/tablet/reinicio-ack/{id}")
def tablet_reinicio_ack(id: int):
    from services import terminais

    terminais.consumir_reinicio_tablet(id)
    terminais.append_log(id, "reinicio", "Sessão do terminal recarregada", origem="terminal")
    return {"ok": True}


@router.post("/tablet/evento/{id}")
async def tablet_evento_endpoint(id: int, request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        body = {}
    from services import terminais

    return terminais.registrar_evento_tablet(id, str(body.get("tipo") or ""), str(body.get("detalhe") or ""))


@router.get("/tablet/operadores")
def tablet_operadores_list():
    """Lista operadores ativos (SQLite) para o tablet — somente leitura operacional (mesmo perfil de /tablet/estado)."""
    from services import config_params_db

    return {"ok": True, "operadores": config_params_db.list_operadores_para_tablet()}


@router.post("/tablet/iniciar/{id}")
async def tablet_iniciar_producao(id: int, request: Request):
    from services import terminais

    if terminais.tablet_em_manutencao(id):
        return terminais.bloqueio_manutencao_resposta()
    try:
        body = await request.json()
    except Exception:
        body = {}
    retomar = bool(body.get("retomar")) if isinstance(body, dict) else False
    op = body.get("operador", "") if isinstance(body, dict) else ""
    tu = body.get("turno", "") if isinstance(body, dict) else ""
    oid = None
    if isinstance(body, dict):
        raw = body.get("operador_perfil_id")
        if raw is not None and raw != "":
            try:
                oid = int(raw)
            except (TypeError, ValueError):
                oid = None
            if oid is not None and oid < 1:
                oid = None
    return pedidos.iniciar_producao_tablet(id, op, tu, retomar=retomar, operador_perfil_id=oid)


@router.post("/tablet/finalizar/{id}/{index}")
async def tablet_finalizar(id: int, index: int, request: Request):
    from services import terminais

    if terminais.tablet_em_manutencao(id):
        return terminais.bloqueio_manutencao_resposta()
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        body = {}
    operador_final = body.get("operador_final", "")
    turno_final = body.get("turno_final", "")
    producao_final = body.get("producao_final", 0)
    oid = None
    raw = body.get("operador_perfil_id")
    if raw is not None and raw != "":
        try:
            oid = int(raw)
        except (TypeError, ValueError):
            oid = None
        if oid is not None and oid < 1:
            oid = None
    return pedidos.finalizar_pedido_tablet(
        id, index, operador_final, producao_final, turno_final, operador_perfil_id=oid
    )
