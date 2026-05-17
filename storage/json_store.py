import json
import os
import shutil
import threading
import time

ARQUIVO = "dados.json"
_arquivo_lock = threading.Lock()


def _default_maquina_record():
    return {
        "produzido": 0,
        "meta": 1000,
        "status": "PARADA",
        "nome": "",
        "setor": "",
        "observacao": "",
        "tablet_vinculado": "",
        "tablet_ultimo_acesso_epoch": 0,
        "tablet_ultimo_ip": "",
        "tablet_bateria_pct": None,
        "tablet_bateria_carregando": False,
        "tablet_sessao_online": False,
        "tablet_manutencao": False,
        "tablet_manutencao_msg": "TERMINAL EM MANUTENÇÃO",
        "tablet_kiosk": False,
        "tablet_reiniciar_em": 0,
        "tablet_reiniciar_ok_em": 0,
        "tablet_logs": [],
        "ativo": True,
    }


def _default_dados_maquinas():
    return {i: {**_default_maquina_record()} for i in range(1, 7)}


def _normalize_pedidos_keys(d):
    if not isinstance(d, dict):
        return {}
    out = {}
    for k, v in d.items():
        try:
            ik = int(k)
        except (TypeError, ValueError):
            continue
        if isinstance(v, list):
            out[ik] = v
    return out


def _merge_dados_maquinas(saved):
    """Mescla todas as chaves inteiras; arquivo vazio → 6 máquinas legadas (1–6)."""
    if not isinstance(saved, dict) or not saved:
        return _default_dados_maquinas()
    out = {}
    for k, v in saved.items():
        try:
            ik = int(k)
        except (TypeError, ValueError):
            continue
        if isinstance(v, dict):
            merged = {**_default_maquina_record(), **v}
            _normalize_tablet_fields_inplace(merged)
            out[ik] = merged
    return out


def _normalize_tablet_fields_inplace(m: dict) -> None:
    from storage.tablet_normalize import normalize_tablet_fields

    normalize_tablet_fields(m)


def _default_resumo_fabrica():
    return {
        "dia_ref": "",
        "producao_dia_total": 0,
    }


def _merge_resumo_fabrica(saved):
    base = _default_resumo_fabrica()
    if not isinstance(saved, dict):
        return base
    for k in base:
        if k in saved:
            base[k] = saved[k]
    if "producao_dia_total" in base:
        try:
            base["producao_dia_total"] = int(base["producao_dia_total"] or 0)
        except (TypeError, ValueError):
            base["producao_dia_total"] = 0
    return base


def _arquivar_json_ilegivel() -> None:
    """Remove `dados.json` ilegível (vazio, binário, JSON inválido) para um .bak com timestamp."""
    if not os.path.isfile(ARQUIVO):
        return
    try:
        bkp = f"{ARQUIVO}.invalid_{int(time.time())}.bak"
        shutil.move(ARQUIVO, bkp)
    except OSError:
        try:
            os.remove(ARQUIVO)
        except OSError:
            pass


def _retorno_padrao_gravado() -> tuple:
    """Estado inicial persistido (evita ficar sem `dados.json` após arquivo ilegível)."""
    maq = _default_dados_maquinas()
    rf = _default_resumo_fabrica()
    salvar_dados({}, [], maq, rf)
    return {}, [], maq, rf


def carregar_dados():
    if not os.path.exists(ARQUIVO):
        return {}, [], _default_dados_maquinas(), _default_resumo_fabrica()

    try:
        with open(ARQUIVO, "rb") as f:
            blob = f.read()
    except OSError:
        return {}, [], _default_dados_maquinas(), _default_resumo_fabrica()

    if not blob or not blob.strip():
        _arquivar_json_ilegivel()
        return _retorno_padrao_gravado()

    try:
        text = blob.decode("utf-8-sig").strip()
    except UnicodeDecodeError:
        _arquivar_json_ilegivel()
        return _retorno_padrao_gravado()

    if not text:
        _arquivar_json_ilegivel()
        return _retorno_padrao_gravado()

    try:
        raw = json.loads(text)
    except json.JSONDecodeError:
        _arquivar_json_ilegivel()
        return _retorno_padrao_gravado()

    if not isinstance(raw, dict):
        _arquivar_json_ilegivel()
        return _retorno_padrao_gravado()

    if "pedidos" in raw:
        pedidos = _normalize_pedidos_keys(raw.get("pedidos", {}))
        produtos = raw.get("produtos_cadastrados", [])
        if not isinstance(produtos, list):
            produtos = []
        maquinas = _merge_dados_maquinas(raw.get("dados_maquinas", {}))
        rf = _merge_resumo_fabrica(raw.get("resumo_fabrica", {}))
        return pedidos, produtos, maquinas, rf

    pedidos = _normalize_pedidos_keys(raw)
    return pedidos, [], _default_dados_maquinas(), _default_resumo_fabrica()


def salvar_dados(pedidos, produtos_cadastrados, dados_maquinas, resumo_fabrica=None):
    rf = resumo_fabrica if isinstance(resumo_fabrica, dict) else _default_resumo_fabrica()
    payload = {
        "pedidos": pedidos,
        "produtos_cadastrados": produtos_cadastrados,
        "dados_maquinas": dados_maquinas,
        "resumo_fabrica": rf,
    }
    with _arquivo_lock:
        with open(ARQUIVO, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
