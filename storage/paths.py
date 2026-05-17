"""Caminhos de dados persistentes (Render disk / volume / local)."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("INDUPACK_DATA_DIR", str(ROOT))).resolve()

try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    pass

DB_PATH = DATA_DIR / "indupack.db"
DADOS_JSON_PATH = DATA_DIR / "dados.json"

# Legado: ficheiros na raiz do projeto (migração automática na 1ª subida)
LEGACY_DB_PATH = ROOT / "indupack.db"
LEGACY_DADOS_JSON_PATH = ROOT / "dados.json"
