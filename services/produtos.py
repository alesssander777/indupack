from storage.state import persist, produtos_cadastrados


def add_produto(nome: str):
    if nome not in produtos_cadastrados:
        produtos_cadastrados.append(nome)
        persist()
    return {"ok": True}
