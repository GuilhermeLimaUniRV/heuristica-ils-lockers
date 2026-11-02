#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerador de instâncias para o problema de localização de lockers
com função objetivo de soma de frações.

Baseado no gerador original do orientador: o modelo de
atratividade (utilidade, theta, nível de serviço, a e b) é mantido idêntico.
A única diferença é que aqui ele é parametrizado e executado em lote para
produzir todas as instâncias do experimento de uma só vez.

Grade experimental (3 x 4 x 2 = 24 instâncias):
    ni (clientes)      : 50, 90, 180
    nj (candidatos)    : ni // 2   (regra nj = ni/2)
    p  (lockers)       : 2, 4, 8, 11
    alpha (decaimento) : 0.6, 0.9

Saída: arquivos JSON em dados/instancias/, no formato lido por guilherme.py e milp.py.
"""

import json
import os

import numpy as np
import scipy.spatial


# =========================
# Grade do experimento
# =========================
NI_VALUES = [50, 90, 180]        # número de clientes (portes pequeno, médio, grande)
P_VALUES = [2, 4, 8, 11]         # número de lockers a instalar
ALPHA_VALUES = [0.6, 0.9]        # fator de decaimento da utilidade com a distância
SEED = 0                         # semente para reprodutibilidade da geração

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dados", "instancias")


def gerar_uma_instancia(ni, nj, p, alpha):
    """
    Gera uma instância seguindo o modelo do orientador.

    Retorna o dicionário 'data' pronto para ser salvo em JSON.
    """
    # coordenadas cartesianas dos clientes e dos locais candidatos
    cxyi = np.random.randint(1, 1000, (ni, 2))
    cxyj = np.random.randint(1, 1000, (nj, 2))
    # demanda de cada cliente
    d = np.random.randint(1, 100, (ni, 1))

    # distâncias euclidianas cliente-local (escala /100)
    dist = scipy.spatial.distance.cdist(cxyi, cxyj) / 100
    # utilidade de cada local para cada cliente (decrescente com a distância)
    utility = -dist * alpha
    # disposição do cliente em utilizar o local (termo exponencial do Logit)
    theta = np.exp(utility)
    # função em degraus do nível de serviço percebido
    s = np.where(dist <= 1, 1, np.where(dist <= 2, 0.5, np.where(dist <= 3, 0.2, 0)))
    # atratividade ponderada pela demanda e denominador (termo de acesso)
    a = np.multiply(np.multiply(d, s), theta)
    b = np.multiply(d, theta)

    file_name = "ni-%d-nj-%d-p-%d-alpha-%.1f.json" % (ni, nj, p, alpha)
    data = {
        "name": file_name,
        "ni": ni,
        "nj": nj,
        "p": p,
        "b": b.tolist(),
        "a": a.tolist(),
        "cxyi": cxyi.tolist(),
        "cxyj": cxyj.tolist(),
    }
    return file_name, data


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    np.random.seed(SEED)

    total = 0
    for ni in NI_VALUES:
        nj = ni // 2  # regra nj = ni / 2
        for alpha in ALPHA_VALUES:
            for p in P_VALUES:
                if not (0 < p <= nj):
                    print(f"IGNORADA: p={p} inválido para nj={nj} (exige 0 < p <= nj).")
                    continue
                file_name, data = gerar_uma_instancia(ni, nj, p, alpha)
                path = os.path.join(OUT_DIR, file_name)
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=1)
                total += 1
                print(f"[{total:02d}] gerada: {file_name}")

    print(f"\n{total} instâncias geradas em: {OUT_DIR}")


if __name__ == "__main__":
    main()
