"""Parâmetros globais em SQLite + operadores + motivos de parada."""

from __future__ import annotations

import copy
import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database.database import SessionLocal
from database import models as orm_models

SETTINGS_ROW_ID = 1

DEFAULT_CONFIG: dict = {
    "producao": {
        "parada_max_minutos": 480,
        "meta_padrao_global": 1000,
        "eficiencia_metodo": "padrao",
        "progresso_modo": "linear",
        "producao_total_modo": "substituicao",
        "reset_os_automatico": True,
    },
    "visual": {
        "nome_empresa": "INDUPACK",
        "logo_url": "",
        "cor_principal": "#1a4a62",
        "fullscreen_padrao": False,
        "titulo_navegador": "Indupack — MES",
    },
    "seguranca": {
        "sessao_max_minutos": 10080,
        "logout_auto_minutos": 0,
        "multiplos_logins": True,
        "admin_padrao_aviso": True,
    },
}


def _deep_merge(base: dict, patch: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in patch.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def _session() -> Session:
    return SessionLocal()


def ensure_settings_row(db: Session) -> orm_models.SystemSettings:
    row = db.get(orm_models.SystemSettings, SETTINGS_ROW_ID)
    if row is None:
        row = orm_models.SystemSettings(
            id=SETTINGS_ROW_ID,
            config_json=json.dumps(DEFAULT_CONFIG, ensure_ascii=False),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def get_merged_config() -> dict:
    with _session() as db:
        row = ensure_settings_row(db)
        try:
            raw = json.loads(row.config_json or "{}")
        except json.JSONDecodeError:
            raw = {}
        return _deep_merge(DEFAULT_CONFIG, raw if isinstance(raw, dict) else {})


def save_merged_config(patch: dict) -> dict:
    if not isinstance(patch, dict):
        patch = {}
    merged = _deep_merge(get_merged_config(), patch)
    with _session() as db:
        row = ensure_settings_row(db)
        row.config_json = json.dumps(merged, ensure_ascii=False)
        db.commit()
    _invalidate_runtime()
    return merged


def session_max_age_seconds() -> int:
    cfg = get_merged_config()
    try:
        mins = int(cfg.get("seguranca", {}).get("sessao_max_minutos", 10080) or 10080)
    except (TypeError, ValueError):
        mins = 10080
    mins = max(30, min(mins, 525600))
    return mins * 60


def _invalidate_runtime() -> None:
    try:
        from services import runtime_config

        runtime_config.invalidate()
    except Exception:
        pass


def seed_stop_motives_if_empty() -> None:
    seeds = [
        ("setup", "Setup", "producao", 10),
        ("manutencao", "Manutenção", "manutencao", 20),
        ("limpeza", "Limpeza", "producao", 30),
        ("troca_bobina", "Troca de bobina", "producao", 40),
        ("sem_operador", "Sem operador", "operacional", 50),
        ("falta_material", "Falta de material", "logistica", 60),
    ]
    with _session() as db:
        cnt = db.scalar(select(func.count()).select_from(orm_models.StopMotive))
        if (cnt or 0) > 0:
            return
        for cod, rot, cat, ordem in seeds:
            db.add(
                orm_models.StopMotive(
                    codigo=cod,
                    rotulo=rot,
                    categoria=cat,
                    ativo=True,
                    ordem=ordem,
                )
            )
        db.commit()


def list_operators() -> list[dict]:
    with _session() as db:
        rows = db.scalars(select(orm_models.OperatorProfile).order_by(orm_models.OperatorProfile.id)).all()
        return [
            {
                "id": r.id,
                "nome": r.nome,
                "turno_padrao": r.turno_padrao,
                "nivel_acesso": r.nivel_acesso,
                "ativo": bool(r.ativo),
                "created_at": r.created_at.isoformat(timespec="seconds") if r.created_at else "",
            }
            for r in rows
        ]


def create_operator(nome: str, turno: str, nivel: str, ativo: bool = True) -> dict:
    nome = str(nome or "").strip()
    if not nome:
        return {"ok": False, "erro": "nome_obrigatorio"}
    with _session() as db:
        r = orm_models.OperatorProfile(
            nome=nome,
            turno_padrao=str(turno or "").strip(),
            nivel_acesso=str(nivel or "operador").strip().lower()[:80],
            ativo=bool(ativo),
            created_at=datetime.now(),
        )
        db.add(r)
        db.commit()
        db.refresh(r)
        return {"ok": True, "id": r.id}


def update_operator(oid: int, nome: str, turno: str, nivel: str, ativo: bool) -> dict:
    with _session() as db:
        r = db.get(orm_models.OperatorProfile, oid)
        if r is None:
            return {"ok": False, "erro": "nao_encontrado"}
        nome = str(nome or "").strip()
        if not nome:
            return {"ok": False, "erro": "nome_obrigatorio"}
        r.nome = nome
        r.turno_padrao = str(turno or "").strip()
        r.nivel_acesso = str(nivel or "operador").strip().lower()[:80]
        r.ativo = bool(ativo)
        db.commit()
        return {"ok": True}


def delete_operator(oid: int) -> dict:
    with _session() as db:
        r = db.get(orm_models.OperatorProfile, oid)
        if r is None:
            return {"ok": False, "erro": "nao_encontrado"}
        db.delete(r)
        db.commit()
        return {"ok": True}


def get_operator_profile(oid: int) -> dict | None:
    with _session() as db:
        r = db.get(orm_models.OperatorProfile, oid)
        if r is None or not bool(r.ativo):
            return None
        return {
            "id": r.id,
            "nome": str(r.nome or "").strip(),
            "turno_padrao": str(r.turno_padrao or "").strip(),
            "nivel_acesso": str(r.nivel_acesso or "").strip(),
        }


def list_operadores_para_tablet() -> list[dict]:
    """Operadores ativos para seleção no tablet (somente leitura operacional)."""
    with _session() as db:
        rows = db.scalars(
            select(orm_models.OperatorProfile)
            .where(orm_models.OperatorProfile.ativo.is_(True))
            .order_by(orm_models.OperatorProfile.nome, orm_models.OperatorProfile.id)
        ).all()
        return [
            {
                "id": r.id,
                "nome": str(r.nome or "").strip(),
                "turno_padrao": str(r.turno_padrao or "").strip(),
            }
            for r in rows
        ]


def list_stop_motives() -> list[dict]:
    with _session() as db:
        rows = db.scalars(
            select(orm_models.StopMotive).order_by(orm_models.StopMotive.ordem, orm_models.StopMotive.id)
        ).all()
        return [
            {
                "id": r.id,
                "codigo": r.codigo,
                "rotulo": r.rotulo,
                "categoria": r.categoria,
                "ativo": bool(r.ativo),
                "ordem": r.ordem,
            }
            for r in rows
        ]


def create_stop_motive(codigo: str, rotulo: str, categoria: str, ativo: bool = True) -> dict:
    cod = str(codigo or "").strip().lower().replace(" ", "_")[:64]
    rot = str(rotulo or "").strip()
    if not cod or not rot:
        return {"ok": False, "erro": "codigo_rotulo_obrigatorios"}
    with _session() as db:
        exists = db.scalar(select(orm_models.StopMotive.id).where(orm_models.StopMotive.codigo == cod))
        if exists is not None:
            return {"ok": False, "erro": "codigo_duplicado"}
        mx = db.scalar(select(func.max(orm_models.StopMotive.ordem)))
        ordem = int(mx or 0) + 10
        r = orm_models.StopMotive(
            codigo=cod,
            rotulo=rot,
            categoria=str(categoria or "geral").strip()[:80],
            ativo=bool(ativo),
            ordem=ordem,
        )
        db.add(r)
        db.commit()
        db.refresh(r)
        return {"ok": True, "id": r.id}


def update_stop_motive(sid: int, rotulo: str, categoria: str, ativo: bool, ordem: int | None = None) -> dict:
    with _session() as db:
        r = db.get(orm_models.StopMotive, sid)
        if r is None:
            return {"ok": False, "erro": "nao_encontrado"}
        r.rotulo = str(rotulo or "").strip()[:200]
        r.categoria = str(categoria or "geral").strip()[:80]
        r.ativo = bool(ativo)
        if ordem is not None:
            try:
                r.ordem = int(ordem)
            except (TypeError, ValueError):
                pass
        db.commit()
        return {"ok": True}


def delete_stop_motive(sid: int) -> dict:
    with _session() as db:
        r = db.get(orm_models.StopMotive, sid)
        if r is None:
            return {"ok": False, "erro": "nao_encontrado"}
        db.delete(r)
        db.commit()
        return {"ok": True}


def save_logo_file(content: bytes, filename: str) -> dict:
    ext = Path(filename or "").suffix.lower()
    if ext not in (".png", ".jpg", ".jpeg", ".webp", ".svg"):
        ext = ".png"
    root = Path(__file__).resolve().parent.parent / "static" / "uploads"
    root.mkdir(parents=True, exist_ok=True)
    dest = root / f"logo_empresa{ext}"
    dest.write_bytes(content[:2_000_000])
    url = f"/static/uploads/{dest.name}"
    save_merged_config({"visual": {"logo_url": url}})
    return {"ok": True, "logo_url": url}


def build_completo_payload() -> dict:
    """Carga única para a página de configurações (admin)."""
    from datetime import datetime

    from services import config_admin, indupack_auth

    painel = dict(config_admin.resumo_painel_admin())
    painel["usuarios"] = len(indupack_auth.get_users())
    painel["servidor_iso"] = datetime.now().isoformat(timespec="seconds")
    from services import maquinas

    return {
        "ok": True,
        "settings": get_merged_config(),
        "maquinas": maquinas.listar_maquinas_para_config(),
        "operadores": list_operators(),
        "paradas": list_stop_motives(),
        "painel": painel,
    }
