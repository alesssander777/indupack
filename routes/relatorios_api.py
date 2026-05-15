"""API JSON e exportação do módulo Relatórios (admin / supervisor)."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from services import indupack_auth
from services.relatorios_service import (
    build_pdf_bytes,
    build_workbook_bytes,
    enviar_pdf_email,
    meta_filtros,
    montar_relatorio,
    parse_filtros,
    stub_agendamento_relatorios,
)

router = APIRouter(prefix="/api/relatorios", tags=["relatorios"])


def _check(request: Request, route_name: str):
    return indupack_auth.require_api_role(request, route_name)


@router.get("/meta")
def relatorios_meta(request: Request):
    err = _check(request, "relatorios_data")
    if err:
        return err
    return JSONResponse(meta_filtros())


@router.get("/dados")
def relatorios_dados(
    request: Request,
    inicio: str | None = None,
    fim: str | None = None,
    maquina: str | None = None,
    operador: str | None = None,
    turno: str | None = None,
    produto: str | None = None,
    setor: str | None = None,
):
    err = _check(request, "relatorios_data")
    if err:
        return err
    flt = parse_filtros(inicio, fim, maquina, operador, turno, produto, setor)
    return JSONResponse(montar_relatorio(flt))


@router.get("/agendamento-stub")
def relatorios_agendamento_stub(request: Request):
    err = _check(request, "relatorios_data")
    if err:
        return err
    return JSONResponse({"ok": True, "estrutura_futura": stub_agendamento_relatorios()})


def _payload_from_query(request: Request):
    q = request.query_params
    flt = parse_filtros(
        q.get("inicio"),
        q.get("fim"),
        q.get("maquina"),
        q.get("operador"),
        q.get("turno"),
        q.get("produto"),
        q.get("setor"),
    )
    err = _check(request, "relatorios_export")
    return flt, err


@router.get("/export.xlsx")
def relatorios_export_xlsx(request: Request):
    flt, err = _payload_from_query(request)
    if err is not None:
        return err
    payload = montar_relatorio(flt)
    titulo = f"INDUPACK_Relatorio_{flt.inicio.date()}_{flt.fim.date()}"
    data = build_workbook_bytes(payload, titulo)
    fn = f"indupack_relatorio_{flt.inicio.date()}_{flt.fim.date()}.xlsx"
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{fn}"'},
    )


@router.get("/export.pdf")
def relatorios_export_pdf(request: Request):
    flt, err = _payload_from_query(request)
    if err is not None:
        return err
    payload = montar_relatorio(flt)
    titulo = f"Período {flt.inicio.date()} a {flt.fim.date()}"
    data = build_pdf_bytes(payload, titulo)
    fn = f"indupack_relatorio_{flt.inicio.date()}_{flt.fim.date()}.pdf"
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fn}"'},
    )


@router.post("/email-pdf")
async def relatorios_email_pdf(request: Request):
    err = _check(request, "relatorios_email")
    if err:
        return err
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        body = {}
    dest = str(body.get("email") or "").strip()
    if not dest or "@" not in dest:
        return JSONResponse(
            {
                "ok": False,
                "erro": "email_invalido",
                "mensagem": "Informe um endereço de e-mail válido.",
            },
            status_code=400,
        )
    flt = parse_filtros(
        body.get("inicio"),
        body.get("fim"),
        body.get("maquina"),
        body.get("operador"),
        body.get("turno"),
        body.get("produto"),
        body.get("setor"),
    )
    payload = montar_relatorio(flt)
    titulo = f"Relatório {flt.inicio.date()} a {flt.fim.date()}"
    pdf = build_pdf_bytes(payload, titulo)
    fn = f"indupack_relatorio_{flt.inicio.date()}_{flt.fim.date()}.pdf"
    assunto = str(body.get("assunto") or f"INDUPACK — Relatório {flt.inicio.date()} a {flt.fim.date()}")
    corpo = str(body.get("corpo") or "Segue o relatório em PDF gerado pela central analítica INDUPACK.")
    r = enviar_pdf_email(dest, assunto, corpo, pdf, fn)
    status = 200 if r.get("ok") else 503
    return JSONResponse(r, status_code=status)
