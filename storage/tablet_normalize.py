"""Normalização de campos de terminal (sem dependências de serviços)."""


def as_bool(value) -> bool:
    if value is True or value is False:
        return bool(value)
    if isinstance(value, (int, float)):
        return value != 0
    s = str(value or "").strip().lower()
    if s in ("1", "true", "yes", "sim", "on"):
        return True
    if s in ("0", "false", "no", "nao", "não", "off", ""):
        return False
    return bool(value)


def normalize_tablet_fields(m: dict) -> None:
    m["tablet_manutencao"] = as_bool(m.get("tablet_manutencao"))
    m["tablet_kiosk"] = as_bool(m.get("tablet_kiosk"))
    m["tablet_bateria_carregando"] = as_bool(m.get("tablet_bateria_carregando"))
    m["tablet_sessao_online"] = as_bool(m.get("tablet_sessao_online"))
    if not str(m.get("tablet_manutencao_msg") or "").strip():
        m["tablet_manutencao_msg"] = "TERMINAL EM MANUTENÇÃO"
    for key in (
        "tablet_ultimo_acesso_epoch",
        "tablet_reiniciar_em",
        "tablet_reiniciar_ok_em",
    ):
        try:
            m[key] = int(m.get(key) or 0)
        except (TypeError, ValueError):
            m[key] = 0
    bat = m.get("tablet_bateria_pct")
    if bat is None or bat == "":
        m["tablet_bateria_pct"] = None
    else:
        try:
            m["tablet_bateria_pct"] = max(0, min(100, int(float(bat))))
        except (TypeError, ValueError):
            m["tablet_bateria_pct"] = None
    if not isinstance(m.get("tablet_logs"), list):
        m["tablet_logs"] = []
