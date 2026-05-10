"""Autenticação INDUPACK: usuários, sessão, perfis e permissões."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
from pathlib import Path

from starlette.responses import RedirectResponse

BASE_DIR = Path(__file__).resolve().parent.parent
USUARIOS_JSON = BASE_DIR / "usuarios_indupack.json"

ROLE_ADMIN = "admin"
ROLE_SUPERVISOR = "supervisor"
ROLE_OPERADOR = "operador"
ROLE_MANUTENCAO = "manutencao"

ALL_ROLES = frozenset({ROLE_ADMIN, ROLE_SUPERVISOR, ROLE_OPERADOR, ROLE_MANUTENCAO})
TABLET_ROLES = frozenset({ROLE_ADMIN, ROLE_SUPERVISOR, ROLE_OPERADOR, ROLE_MANUTENCAO})
FLOOR_ROLES = frozenset({ROLE_ADMIN, ROLE_SUPERVISOR, ROLE_MANUTENCAO})


def _pbkdf2_hash(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 120_000)
    return f"{salt}:{dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    if not stored or ":" not in stored:
        return False
    salt_hex, h_hex = stored.split(":", 1)
    try:
        salt = bytes.fromhex(salt_hex)
        expect = bytes.fromhex(h_hex)
    except ValueError:
        return False
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return secrets.compare_digest(dk, expect)


def _default_seed_users() -> list[dict]:
    """Senhas iniciais — altere em produção via usuarios_indupack.json."""
    seeds = [
        ("admin", "indupack2024", "Administrador", ROLE_ADMIN),
        ("supervisor", "supervisor2024", "Supervisor", ROLE_SUPERVISOR),
        ("operador", "operador2024", "Operador", ROLE_OPERADOR),
        ("manutencao", "manutencao2024", "Manutenção", ROLE_MANUTENCAO),
    ]
    out = []
    for user, pw, cargo, role in seeds:
        out.append(
            {
                "username": user,
                "password_hash": _pbkdf2_hash(pw),
                "cargo": cargo,
                "role": role,
            }
        )
    return out


def _load_users_file() -> list[dict]:
    if not USUARIOS_JSON.is_file():
        data = {"users": _default_seed_users()}
        with open(USUARIOS_JSON, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return list(data["users"])
    with open(USUARIOS_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    users = data.get("users")
    if not isinstance(users, list):
        return []
    return users


_USERS_CACHE: list[dict] | None = None


def get_users() -> list[dict]:
    global _USERS_CACHE
    if _USERS_CACHE is None:
        _USERS_CACHE = _load_users_file()
    return _USERS_CACHE


def reload_users() -> None:
    global _USERS_CACHE
    _USERS_CACHE = None


def authenticate(username: str, password: str) -> dict | None:
    u = (username or "").strip().lower()
    if not u or not password:
        return None
    for row in get_users():
        if str(row.get("username", "")).strip().lower() != u:
            continue
        if verify_password(password, str(row.get("password_hash", ""))):
            role = str(row.get("role", "")).strip().lower()
            if role not in ALL_ROLES:
                role = ROLE_OPERADOR
            return {
                "username": str(row.get("username", "")).strip(),
                "cargo": str(row.get("cargo", row.get("username", ""))),
                "role": role,
            }
    return None


def session_user(request) -> dict | None:
    uid = request.session.get("user")
    if not uid:
        return None
    return {
        "username": uid,
        "cargo": request.session.get("cargo", uid),
        "role": request.session.get("role", ROLE_OPERADOR),
    }


def set_session(request, user: dict) -> None:
    request.session["user"] = user["username"]
    request.session["cargo"] = user["cargo"]
    request.session["role"] = user["role"]


def clear_session(request) -> None:
    request.session.clear()


def role_may_access_path(role: str, path: str) -> bool:
    """Regras de páginas HTML (prefixo)."""
    path = path.split("?", 1)[0].rstrip("/") or "/"
    if path.startswith("/tablet"):
        return role in TABLET_ROLES
    if path.startswith("/programacao") or path.startswith("/pedido"):
        return role in {ROLE_ADMIN, ROLE_SUPERVISOR}
    if path in {"/relatorios"}:
        return role in {ROLE_ADMIN, ROLE_SUPERVISOR}
    if path in {"/tablets"}:
        return role in {ROLE_ADMIN, ROLE_SUPERVISOR, ROLE_MANUTENCAO}
    if path in {"/configuracoes"}:
        return role == ROLE_ADMIN
    if path in {"/manutencao"}:
        return role in {ROLE_ADMIN, ROLE_MANUTENCAO}
    if path in {"/producao"}:
        return role in FLOOR_ROLES
    if path in {"/", "", "/home"}:
        return role in FLOOR_ROLES or role == ROLE_OPERADOR
    # Demais módulos internos (placeholder)
    if path.startswith("/serigrafia") or path.startswith("/impressao") or path.startswith("/expedicao"):
        return role == ROLE_ADMIN
    return role == ROLE_ADMIN


def api_allowed(role: str, route_name: str) -> bool:
    """route_name: identificador estável por endpoint."""
    tablet = {
        "tablet_estado",
        "tablet_iniciar",
        "tablet_finalizar",
        "tablet_produzido_delta",
        "maquina_contexto",
        "status_maquina",
    }
    if route_name in tablet:
        return role in TABLET_ROLES
    if route_name == "producao_atual":
        return role in FLOOR_ROLES
    if route_name in {"add_producao", "produzido_total"}:
        return role in {ROLE_ADMIN, ROLE_SUPERVISOR, ROLE_MANUTENCAO}
    if route_name == "criar_maquina":
        return role == ROLE_ADMIN
    if route_name in {
        "editar_pedido",
        "deletar_pedido",
        "novo_pedido",
        "reordenar",
        "salvar_pedido",
        "add_produto",
    }:
        return role in {ROLE_ADMIN, ROLE_SUPERVISOR}
    return role == ROLE_ADMIN


def api_error_response():
    from fastapi.responses import JSONResponse

    return JSONResponse({"ok": False, "erro": "nao_autorizado"}, status_code=401)


def require_api_role(request, route_name: str):
    su = session_user(request)
    if not su:
        return api_error_response()
    if not api_allowed(su["role"], route_name):
        return api_error_response()
    return None


def redirect_login():
    return RedirectResponse(url="/login", status_code=302)


def redirect_forbidden():
    return RedirectResponse(url="/login?erro=sem_permissao", status_code=302)


def guard_page(request, logical_path: str):
    """
    logical_path: caminho para checagem (ex.: '/', '/producao', '/programacao/1').
    Retorna RedirectResponse ou None.
    """
    su = session_user(request)
    if not su:
        return redirect_login()
    if not role_may_access_path(su["role"], logical_path):
        return redirect_forbidden()
    return None


def template_user(request) -> str:
    su = session_user(request)
    if not su:
        return "—"
    return str(su.get("cargo") or su.get("username") or "—")
