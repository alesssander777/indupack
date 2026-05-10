from . import json_store

pedidos, produtos_cadastrados, dados_maquinas, resumo_fabrica = json_store.carregar_dados()


def persist():
    json_store.salvar_dados(pedidos, produtos_cadastrados, dados_maquinas, resumo_fabrica)
