"""Catálogo fixo de produtos (código, medida, peso) para selects de pedido/programação."""

import html as html_lib

CATALOGO = [
    {"codigo": "2594", "medida": "15x22x8", "peso": "3KG"},
    {"codigo": "1956", "medida": "18x28x10", "peso": "5KG"},
    {"codigo": "2503", "medida": "18x35x10", "peso": "7,5KG"},
    {"codigo": "2767", "medida": "22x35x10,5", "peso": "10KG"},
    {"codigo": "1869", "medida": "24x35x12", "peso": "10KG"},
    {"codigo": "2170", "medida": "24x34x14,5", "peso": "15KG"},
    {"codigo": "2152", "medida": "28x32x18", "peso": "18KG"},
    {"codigo": "2164", "medida": "28x40x14", "peso": "20KG"},
    {"codigo": "2345", "medida": "28x40x18", "peso": "25KG"},
    {"codigo": "2597", "medida": "31x34x18", "peso": ""},
]


def valor_opcao(item: dict) -> str:
    partes = [item["codigo"], item["medida"]]
    peso = (item.get("peso") or "").strip()
    if peso:
        partes.append(peso)
    return " ".join(partes)


def rotulo_opcao(item: dict) -> str:
    peso = (item.get("peso") or "").strip()
    if peso:
        return f"{item['codigo']} - {item['medida']} - {peso}"
    return f"{item['codigo']} - {item['medida']}"


def build_options_html(produtos_cadastrados: list) -> str:
    """Opções do select: catálogo fixo primeiro, depois produtos cadastrados via prompt (sem duplicar)."""
    vistos = set()
    blocos = []

    for item in CATALOGO:
        val = valor_opcao(item)
        lbl = rotulo_opcao(item)
        vistos.add(val)
        vistos.add(lbl)
        blocos.append(
            f'<option value="{html_lib.escape(val, quote=True)}">'
            f"{html_lib.escape(lbl)}</option>"
        )

    for custo in produtos_cadastrados or []:
        c = (custo or "").strip()
        if not c or c in vistos:
            continue
        vistos.add(c)
        blocos.append(
            f'<option value="{html_lib.escape(c, quote=True)}">'
            f"{html_lib.escape(c)}</option>"
        )

    return "".join(blocos)
