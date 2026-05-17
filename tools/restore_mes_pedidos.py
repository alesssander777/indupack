"""
Lista todas as fontes de programação (pedidos) e aplica fusão no volume atual.

Uso (na raiz do projeto):
  python tools/restore_mes_pedidos.py
  python tools/restore_mes_pedidos.py --apply
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from database import init_db  # noqa: E402
from storage.mes_persist import (  # noqa: E402
    _discover_db_snapshots,
    _discover_json_snapshots,
    _load_chunks_from_sqlite,
    _load_from_json_file,
    _merge_operational_states,
    _pedidos_count,
    _chunks_to_state,
    _load_chunks_from_db_path,
    load_operational_state,
    save_operational_state,
)
from storage.paths import DB_PATH, DADOS_JSON_PATH, LEGACY_DB_PATH  # noqa: E402


def _report(label: str, st) -> None:
    n = _pedidos_count(st[0])
    by = {k: len(v) for k, v in st[0].items() if isinstance(v, list)}
    print(f"  {label}: {n} pedidos {by or '{}'}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Recuperar filas MES de backups")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Grava estado fundido em SQLite + dados.json",
    )
    args = parser.parse_args()

    init_db()
    print("Volume:", DB_PATH.parent)
    print("DB:", DB_PATH)
    print("JSON:", DADOS_JSON_PATH)
    print()

    candidates = []
    labels = []

    chunks = _load_chunks_from_sqlite()
    if chunks:
        st = _chunks_to_state(chunks)
        candidates.append(st)
        labels.append("SQLite atual")
        _report("SQLite atual", st)

    js = _load_from_json_file()
    if js:
        candidates.append(js)
        labels.append("dados.json")
        _report("dados.json", js)

    leg = _load_chunks_from_db_path(LEGACY_DB_PATH)
    if leg:
        st = _chunks_to_state(leg)
        candidates.append(st)
        labels.append("indupack.db legado")
        _report("indupack.db legado", st)

    for name, st in _discover_json_snapshots():
        candidates.append(st)
        labels.append(name)
        _report(f"JSON extra ({name})", st)

    for name, st in _discover_db_snapshots():
        candidates.append(st)
        labels.append(name)
        _report(f"DB backup ({name})", st)

    if not candidates:
        print("\nNenhuma fonte encontrada.")
        return 1

    merged = _merge_operational_states(*candidates, labels=labels)
    pedidos, produtos, maquinas, resumo, n, src = merged
    print(f"\nFusao: {src.replace(chr(0x2192), '->')}")
    for k, v in sorted(pedidos.items()):
        print(f"  Máquina {k}: {len(v)} pedido(s)")

    max_before = max(_pedidos_count(c[0]) for c in candidates)
    if n < max_before:
        print(f"\nERRO: fusão ({n}) < máximo em disco ({max_before}). Não aplicar.")
        return 2

    if args.apply:
        save_operational_state(pedidos, produtos, maquinas, resumo, mirror_json=True)
        load_operational_state()
        print("\nEstado gravado e recarregado.")
    else:
        print("\nDry-run. Use --apply para gravar.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
