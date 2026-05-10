import html as html_lib
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from starlette.responses import Response
from fastapi.templating import Jinja2Templates

from services import indupack_auth
from services import maquinas as maquinas_service
from services.catalogo_produtos import build_options_html
from services.home_resumo import resumo_home
from services.producao_snapshot import card_primeiro_pedido
from services.tablet_estado import estado_tablet
from services.tablets_admin import listagem_terminais_admin
from storage.state import dados_maquinas, pedidos, produtos_cadastrados

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter()

_LOGIN_ERROS = {
    "sem_permissao": "Você não tem permissão para acessar este módulo.",
    "invalido": (
        "Usuário ou senha incorretos. "
        "Na instalação padrão, o usuário admin usa a senha indupack2024 "
        "(demais contas: supervisor2024, operador2024, manutencao2024). "
        "Altere essas senhas em produção."
    ),
}


def _nome_topo(request: Request) -> str:
    return indupack_auth.template_user(request)


# Ícone do saco nos cards — raster enviado pela equipe (fundo preto removido no asset PNG).
_PR_CARD_BAG_MEDIA = (
    '<img src="/static/images/indupack-card-bag-icon.png" alt="" '
    'class="pr-card__media-icon" width="220" height="147" '
    'loading="lazy" decoding="async" />'
)


def _esc_prog(val) -> str:
    return html_lib.escape(str(val if val is not None else ""), quote=False)


def _prog_cell_op_inicio(p: dict) -> str:
    oi = str(p.get("operador_inicio") or "").strip()
    ti = str(p.get("turno_inicio") or "").strip()
    hi = str(p.get("hora_inicio_operacao") or "").strip()
    if not oi and not ti:
        return "—"
    main = " · ".join(x for x in (oi, ti) if x)
    if hi:
        return (
            f'<span class="prog-op-main">{_esc_prog(main)}</span><br>'
            f'<span class="prog-op-sub">{_esc_prog(hi)}</span>'
        )
    return f'<span class="prog-op-main">{_esc_prog(main)}</span>'


def _prog_cell_op_fim(p: dict) -> str:
    if not p.get("finalizado"):
        return "—"
    of = str(p.get("operador_final") or "").strip()
    tf = str(p.get("turno_final") or "").strip()
    hf = str(p.get("hora_finalizacao") or "").strip()
    if not of and not tf:
        return "—"
    main = " · ".join(x for x in (of, tf) if x)
    if hf:
        return (
            f'<span class="prog-op-main">{_esc_prog(main)}</span><br>'
            f'<span class="prog-op-sub">{_esc_prog(hf)}</span>'
        )
    return f'<span class="prog-op-main">{_esc_prog(main)}</span>'


def _historico_paradas_rows(maquina_id: int, limit: int = 15) -> list:
    """Últimas paradas gravadas (para programação administrativa)."""
    dm = dados_maquinas.get(maquina_id, {})
    hp = dm.get("historico_paradas")
    if not isinstance(hp, list) or not hp:
        return []

    def fmt_ms(ms):
        if not ms:
            return "—"
        try:
            ts = int(ms) / 1000.0
            return datetime.fromtimestamp(ts).strftime("%d/%m/%Y, %H:%M:%S")
        except (TypeError, ValueError, OSError):
            return "—"

    def fmt_dur(sec):
        if sec is None:
            return "—"
        try:
            s = max(0, int(sec))
            h, r = divmod(s, 3600)
            m, s2 = divmod(r, 60)
            return f"{h:02d}:{m:02d}:{s2:02d}"
        except (TypeError, ValueError):
            return "—"

    rows = []
    for h in reversed(hp):
        if len(rows) >= limit:
            break
        rows.append(
            {
                "inicio": fmt_ms(h.get("inicio_epoch")),
                "retorno": fmt_ms(h.get("retorno_epoch")),
                "duracao": fmt_dur(h.get("duracao_s")),
                "motivo": str(h.get("motivo") or ""),
            }
        )
    return rows


@router.get("/logo")
def logo():
    path_logo = BASE_DIR / "logo.png"
    if not path_logo.is_file():
        return Response(status_code=404)
    return FileResponse(path_logo)


@router.get("/login", response_class=HTMLResponse)
def login_get(request: Request):
    if indupack_auth.session_user(request):
        return RedirectResponse("/", status_code=302)
    erro = request.query_params.get("erro", "")
    msg = _LOGIN_ERROS.get(erro, "") if erro else ""
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"erro_msg": msg},
    )


@router.post("/login")
async def login_post(request: Request):
    form = await request.form()
    username = str(form.get("username") or "")
    password = str(form.get("password") or "")
    user = indupack_auth.authenticate(username, password)
    if not user:
        return RedirectResponse("/login?erro=invalido", status_code=302)
    indupack_auth.set_session(request, user)
    ids_tbl = maquinas_service.ids_maquinas_ordenadas()
    tid = ids_tbl[0] if ids_tbl else 1
    if user.get("role") == indupack_auth.ROLE_OPERADOR:
        return RedirectResponse(f"/tablet/{tid}", status_code=302)
    return RedirectResponse("/", status_code=302)


@router.get("/logout")
def logout(request: Request):
    indupack_auth.clear_session(request)
    return RedirectResponse("/login", status_code=302)


def _home_response(request: Request, logical_path: str):
    g = indupack_auth.guard_page(request, logical_path)
    if g:
        return g
    ids_tbl = maquinas_service.ids_maquinas_ordenadas()
    tablet_primeiro_id = ids_tbl[0] if ids_tbl else 1
    su = indupack_auth.session_user(request)
    if su and su.get("role") == indupack_auth.ROLE_OPERADOR:
        return RedirectResponse(f"/tablet/{tablet_primeiro_id}", status_code=302)
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={
            "resumo": resumo_home(),
            "usuario_nome": _nome_topo(request),
        },
    )


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    return _home_response(request, "/")


@router.get("/home", response_class=HTMLResponse)
def home_path(request: Request):
    """Alias da HOME (mesmo conteúdo que /)."""
    return _home_response(request, "/home")


@router.get("/relatorios", response_class=HTMLResponse)
def relatorios(request: Request):
    g = indupack_auth.guard_page(request, "/relatorios")
    if g:
        return g
    return templates.TemplateResponse(
        request=request,
        name="relatorios.html",
        context={"usuario_nome": _nome_topo(request)},
    )


@router.get("/tablets", response_class=HTMLResponse)
def tablets_admin(request: Request):
    """Central administrativa de terminais — não confundir com /tablet/{id} (operação)."""
    g = indupack_auth.guard_page(request, "/tablets")
    if g:
        return g
    return templates.TemplateResponse(
        request=request,
        name="tablets.html",
        context={
            "usuario_nome": _nome_topo(request),
            "terminais": listagem_terminais_admin(),
        },
    )


@router.get("/configuracoes", response_class=HTMLResponse)
def configuracoes(request: Request):
    g = indupack_auth.guard_page(request, "/configuracoes")
    if g:
        return g
    return templates.TemplateResponse(
        request=request,
        name="configuracoes.html",
        context={"usuario_nome": _nome_topo(request)},
    )


@router.get("/manutencao", response_class=HTMLResponse)
def manutencao(request: Request):
    g = indupack_auth.guard_page(request, "/manutencao")
    if g:
        return g
    return templates.TemplateResponse(
        request=request,
        name="manutencao.html",
        context={"usuario_nome": _nome_topo(request)},
    )


@router.get("/producao1")
@router.get("/producao1/")
def producao1_alias():
    """Atalho legado — mesmo painel que /producao."""
    return RedirectResponse(url="/producao", status_code=307)


@router.get("/tablet1")
@router.get("/tablet1/")
def tablet1_alias():
    """Atalho legado — terminal da máquina 1 (/tablet/1)."""
    return RedirectResponse(url="/tablet/1", status_code=307)


@router.get("/producao", response_class=HTMLResponse)
def producao(request: Request):
    g = indupack_auth.guard_page(request, "/producao")
    if g:
        return g
    maquinas_html = ""
    # Painel sem scroll no front quando ≤6; com mais máquinas, liberar rolagem no template
    maquina_ids = maquinas_service.ids_maquinas_ordenadas()

    for i in maquina_ids:
        d = card_primeiro_pedido(i)
        dm = dados_maquinas.get(i, {})
        nome_m = str(dm.get("nome") or "").strip()
        setor_m = str(dm.get("setor") or "").strip()
        titulo = nome_m if nome_m else f"Máquina {i:02d}"
        cliente = _esc_prog(d["cliente"])
        produto = _esc_prog(d["produto"])
        quantidade_txt = _esc_prog(d["quantidade_txt"])
        descricao = _esc_prog(d["descricao"])
        titulo_esc = _esc_prog(titulo)
        setor_esc = _esc_prog(setor_m) if setor_m else ""
        cor = d["status_cor"]
        pct = d["progress_pct"]
        produzido = d["produzido"]
        faltam = int(d.get("faltam", 0) or 0)
        efic = int(d.get("eficiencia_pct", pct) or 0)
        st_line = _esc_prog(d.get("status_line") or d["status"])
        st_kind = d.get("status_kind") or "stop"
        operador_esc = _esc_prog(d.get("operador_atual", "---"))
        tparado_esc = _esc_prog(d.get("tempo_parado_txt", "—"))

        setor_block = ""
        if setor_m:
            setor_block = f'<span class="pr-card__setor" id="p{i}-setor">{setor_esc}</span>'

        maquinas_html += f"""
        <article class="pr-card" data-maquina="{i}" onclick="window.location.href='/programacao/{i}'">
            <div class="pr-card__inner">
                <header class="pr-card__head">
                    <div class="pr-card__identity">
                        <h2 class="pr-card__title" id="p{i}-titulo">{titulo_esc}</h2>
                        {setor_block}
                    </div>
                    <div class="pr-status pr-status--{st_kind}" id="p{i}-status-wrap">
                        <span id="p{i}-status">{st_line}</span>
                    </div>
                    <div class="pr-card__progress-block">
                        <div class="pr-progress" aria-hidden="true">
                            <div class="pr-progress__track">
                                <div class="pr-progress__fill" id="p{i}-progress" style="background:{cor}; width:{pct}%;"></div>
                            </div>
                        </div>
                        <div class="pr-card__progress-meta">
                            <span class="pr-card__pct" id="p{i}-pctlbl">{pct}%</span>
                            <span class="pr-card__qty-line" aria-live="polite">
                                <span id="p{i}-produzido">{produzido}</span><span class="pr-card__qty-sep">/</span><span id="p{i}-qmeta">{quantidade_txt}</span>
                            </span>
                        </div>
                    </div>
                </header>
                <div class="pr-card__body">
                    <div class="pr-card__body-split">
                        <div class="pr-card__info-stack">
                            <div class="pr-kpi">
                                <span class="pr-kpi__lab">Cliente</span>
                                <span class="pr-kpi__val" id="p{i}-cliente">{cliente}</span>
                            </div>
                            <div class="pr-kpi">
                                <span class="pr-kpi__lab">Produto</span>
                                <span class="pr-kpi__val" id="p{i}-produto">{produto}</span>
                            </div>
                            <div class="pr-kpi">
                                <span class="pr-kpi__lab">Quantidade</span>
                                <span class="pr-kpi__val" id="p{i}-quantidade">{quantidade_txt}</span>
                            </div>
                            <div class="pr-kpi">
                                <span class="pr-kpi__lab">Observação</span>
                                <span class="pr-kpi__val pr-kpi__val--note" id="p{i}-descricao">{descricao}</span>
                            </div>
                        </div>
                        <div class="pr-card__media-slot" aria-hidden="true">
                            {_PR_CARD_BAG_MEDIA}
                        </div>
                    </div>
                </div>
                <footer class="pr-card__foot">
                    <div class="pr-foot">
                        <span class="pr-foot__k">Operador</span>
                        <span class="pr-foot__v" id="p{i}-operador">{operador_esc}</span>
                    </div>
                    <div class="pr-foot">
                        <span class="pr-foot__k">Eficiência</span>
                        <span class="pr-foot__v" id="p{i}-efic">{efic}%</span>
                    </div>
                    <div class="pr-foot">
                        <span class="pr-foot__k">Produzidos</span>
                        <span class="pr-foot__v" id="p{i}-foot-prod">{produzido}</span>
                    </div>
                    <div class="pr-foot">
                        <span class="pr-foot__k">Faltam</span>
                        <span class="pr-foot__v" id="p{i}-faltam">{faltam}</span>
                    </div>
                    <div class="pr-foot">
                        <span class="pr-foot__k">Tempo parado</span>
                        <span class="pr-foot__v" id="p{i}-tparado">{tparado_esc}</span>
                    </div>
                </footer>
            </div>
        </article>
        """

    return templates.TemplateResponse(
        request=request,
        name="producao.html",
        context={
            "maquinas": maquinas_html,
            "usuario_nome": _nome_topo(request),
            "maquinas_count": len(maquina_ids),
        },
    )


@router.get("/programacao/{id}", response_class=HTMLResponse)
def programacao_maquina(request: Request, id: int):
    g = indupack_auth.guard_page(request, f"/programacao/{id}")
    if g:
        return g
    lista = pedidos.get(id, [])
    opcoes_produtos = build_options_html(produtos_cadastrados)

    linhas = ""

    for idx, p in enumerate(lista):
        ordem = f"{idx+1}º"
        cell_ini = _prog_cell_op_inicio(p)
        cell_fim = _prog_cell_op_fim(p)

        linhas += f"""
        <div class="linha linha-draggable {"finalizado" if p.get("finalizado") else ""}"
            draggable="true"
            data-pedido-index="{idx}"
            title="Arraste para reordenar">

            <div class="ordem">{ordem}</div>

            <input value="{p.get("data","")}" onchange="editar({id},{idx},'data',this.value)">
            <input value="{p.get("cod","")}" onchange="editar({id},{idx},'cod',this.value)">
            <input value="{p.get("produto","")}" onchange="editar({id},{idx},'produto',this.value)">
            <input value="{p.get("quantidade","")}" onchange="editar({id},{idx},'quantidade',this.value)">
            <input value="{p.get("fardos","")}" onchange="editar({id},{idx},'fardos',this.value)">
            <div class="prog-pill-wrap" title="Etiqueta impressa / conferida">
            <input type="checkbox" class="cb-etiqueta-feita prog-pill-input"
            {"checked" if p.get("etiqueta_feita") else ""}
            onchange="etiquetaFeitaCheckboxChange({id},{idx},this)">
            <span class="prog-pill-face" aria-hidden="true"></span>
            </div>
            <input value="{p.get("descricao","")}" onchange="editar({id},{idx},'descricao',this.value)">

            <div class="prog-pill-wrap" title="Pedido finalizado — toque para alternar">
            <input type="checkbox" class="cb-finalizado prog-pill-input"
            {"checked" if p.get("finalizado") else ""}
            onchange="finalizadoCheckboxChange({id},{idx},this)">
            <span class="prog-pill-face" aria-hidden="true"></span>
            </div>

            <div class="prog-op-cell">{cell_ini}</div>
            <div class="prog-op-cell">{cell_fim}</div>

            <button type="button" class="delete" onclick="pedirExcluirPedido({idx})">🗑</button>

        </div>
        """

    return templates.TemplateResponse(
        request=request,
        name="programacao.html",
        context={
            "id": id,
            "opcoes_produtos": opcoes_produtos,
            "linhas": linhas,
            "historico_paradas_rows": _historico_paradas_rows(id),
            "usuario_nome": _nome_topo(request),
        },
    )


@router.get("/pedido/{id}", response_class=HTMLResponse)
def pedido(request: Request, id: int):
    g = indupack_auth.guard_page(request, f"/pedido/{id}")
    if g:
        return g
    opcoes = build_options_html(produtos_cadastrados)

    return templates.TemplateResponse(
        request=request,
        name="pedido.html",
        context={"id": id, "opcoes": opcoes, "usuario_nome": _nome_topo(request)},
    )


@router.get("/serigrafia", response_class=HTMLResponse)
def serigrafia(request: Request):
    g = indupack_auth.guard_page(request, "/serigrafia")
    if g:
        return g
    return templates.TemplateResponse(
        request=request,
        name="serigrafia.html",
        context={"usuario_nome": _nome_topo(request)},
    )


@router.get("/impressao", response_class=HTMLResponse)
def impressao(request: Request):
    g = indupack_auth.guard_page(request, "/impressao")
    if g:
        return g
    return templates.TemplateResponse(
        request=request,
        name="impressao.html",
        context={"usuario_nome": _nome_topo(request)},
    )


@router.get("/expedicao", response_class=HTMLResponse)
def expedicao(request: Request):
    g = indupack_auth.guard_page(request, "/expedicao")
    if g:
        return g
    return templates.TemplateResponse(
        request=request,
        name="expedicao.html",
        context={"usuario_nome": _nome_topo(request)},
    )


@router.get("/tablet/{id}", response_class=HTMLResponse)
def tablet(request: Request, id: int):
    host = request.client.host if request.client else None
    maquinas_service.registrar_presenca_tablet(id, host)
    boot = estado_tablet(id)
    return templates.TemplateResponse(
        request=request,
        name="tablet.html",
        context={"id": id, "estado_boot": boot},
    )


@router.get("/tablet/{id}/pedidos", response_class=HTMLResponse)
def tablet_pedidos_maquina(request: Request, id: int):
    """Fila / ordens da máquina — navegação isolada do terminal tablet (sem dashboard geral)."""
    lista = pedidos.get(id, [])
    return templates.TemplateResponse(
        request=request,
        name="tablet_pedidos.html",
        context={
            "id": id,
            "pedidos": lista,
        },
    )


@router.get("/maquina/{id}/pedidos")
def maquina_pedidos_alias(request: Request, id: int):
    """Alias estável: mesmo conteúdo que /tablet/{id}/pedidos."""
    return RedirectResponse(url=f"/tablet/{id}/pedidos", status_code=307)
