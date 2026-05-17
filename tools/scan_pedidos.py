import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from storage.paths import DB_PATH, DADOS_JSON_PATH, LEGACY_DB_PATH, LEGACY_DADOS_JSON_PATH

def count_pedidos_json(path: Path):
    if not path.is_file():
        return None
    d = json.loads(path.read_text(encoding="utf-8-sig"))
    p = d.get("pedidos", d)
    if not isinstance(p, dict):
        return 0
    return sum(len(v) for v in p.values() if isinstance(v, list))


def count_pedidos_db(path: Path):
    if not path.is_file():
        return None
    conn = sqlite3.connect(str(path))
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='mes_operacional_chunks'"
    )
    if cur.fetchone() is None:
        conn.close()
        return None
    row = conn.execute(
        "SELECT payload_json FROM mes_operacional_chunks WHERE chunk_key='pedidos'"
    ).fetchone()
    conn.close()
    if not row:
        return 0
    p = json.loads(row[0])
    return sum(len(v) for v in p.values() if isinstance(v, list))


for label, p in [
    ("DB_PATH", DB_PATH),
    ("DADOS_JSON", DADOS_JSON_PATH),
    ("LEGACY_DB", LEGACY_DB_PATH),
    ("LEGACY_JSON", LEGACY_DADOS_JSON_PATH),
]:
    nj = count_pedidos_json(p) if p.suffix == ".json" else None
    nd = count_pedidos_db(p) if p.suffix == ".db" else None
    print(label, p, "json", nj, "db", nd)

broot = ROOT / "backups"
if broot.is_dir():
    for p in sorted(broot.rglob("*.db"))[-8:]:
        print("backup", p.name, count_pedidos_db(p))
for p in ROOT.glob("dados.json*"):
    print("glob", p.name, count_pedidos_json(p))
