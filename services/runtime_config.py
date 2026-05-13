"""Cache leve de parâmetros lidos do armazenamento de configuração (invalidado ao gravar)."""

from __future__ import annotations

import threading
from typing import Any

_lock = threading.Lock()
_full: dict[str, Any] | None = None


def invalidate() -> None:
    global _full
    with _lock:
        _full = None


def _safe_hex(raw: str) -> str:
    s = str(raw or "").strip()
    if len(s) == 7 and s[0] == "#" and all(c in "0123456789abcdefABCDEF" for c in s[1:]):
        return "#" + s[1:].lower()
    return "#1a4a62"


def _hex_rgb(h: str) -> tuple[int, int, int]:
    h = _safe_hex(h).lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_hex(rgb: tuple[int, int, int]) -> str:
    r, g, b = (max(0, min(255, x)) for x in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"


def _mix_white(rgb: tuple[int, int, int], w: float) -> tuple[int, int, int]:
    return tuple(int(c * (1.0 - w) + 255.0 * w) for c in rgb)


def _scale(rgb: tuple[int, int, int], f: float) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(c * f))) for c in rgb)


def _visual_block(vis: dict) -> dict[str, str]:
    nome = str(vis.get("nome_empresa") or "").strip() or "INDUPACK"
    cor = _safe_hex(str(vis.get("cor_principal") or ""))
    rgb = _hex_rgb(cor)
    logo = str(vis.get("logo_url") or "").strip()
    if logo and not logo.startswith("/"):
        logo = "/" + logo.lstrip("/")
    titulo = str(vis.get("titulo_navegador") or "").strip()
    if not titulo:
        titulo = f"{nome} — Sistema de Gestão Industrial"
    return {
        "nome_empresa": nome,
        "cor_principal": cor,
        "cor_header_top": _rgb_hex(_mix_white(rgb, 0.11)),
        "cor_header_mid": cor,
        "cor_header_deep": _rgb_hex(_scale(rgb, 0.8)),
        "cor_header_edge": _rgb_hex(_scale(rgb, 0.48)),
        "cor_escura": _rgb_hex(_scale(rgb, 0.88)),
        "cor_clara_soft": _rgb_hex(_mix_white(_scale(rgb, 0.92), 0.22)),
        "logo_url": logo,
        "logo_src": logo if logo else "/logo",
        "titulo_navegador": titulo,
    }


def _load() -> dict[str, Any]:
    global _full
    with _lock:
        if _full is None:
            from services import config_params_db

            cfg = config_params_db.get_merged_config()
            p = cfg.get("producao") or {}
            vis = cfg.get("visual") or {}
            prod = {
                "reset_os_automatico": bool(p.get("reset_os_automatico", True)),
                "parada_max_minutos": int(p.get("parada_max_minutos") or 480),
                "meta_padrao_global": int(p.get("meta_padrao_global") or 1000),
                "eficiencia_metodo": str(p.get("eficiencia_metodo") or "padrao"),
                "progresso_modo": str(p.get("progresso_modo") or "linear"),
                "producao_total_modo": str(p.get("producao_total_modo") or "substituicao"),
            }
            _full = {"producao": prod, "visual": _visual_block(vis if isinstance(vis, dict) else {})}
        return _full


def production_flags() -> dict[str, Any]:
    return dict(_load()["producao"])


def visual_branding() -> dict[str, str]:
    """Identidade visual ativa (MES) — usada nas templates Jinja e invalidada ao gravar configurações."""
    return dict(_load()["visual"])
