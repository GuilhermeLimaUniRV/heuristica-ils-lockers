#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch do MILP exato para confrontar com a heurística (ILS).

Estratégia (orientação do professor):
- roda as instâncias em ordem crescente de dificuldade (por n, depois p);
- cada instância tem limite de tempo (padrão: 30 min);
- quando uma instância ATINGE o tempo limite SEM provar o ótimo, as
  instâncias subsequentes (maiores) são CENSURADAS, pois o problema cresce
  exponencialmente e também não seriam resolvidas no tempo.

Guarda o CONJUNTO FINAL de locais escolhidos:
  - Locais_MILP : solução ótima (ou melhor encontrada) do MILP
  - Locais_ILS  : solução do ILS (uma execução representativa, reprodutível)
E compara valor (Z) e os próprios locais escolhidos.

Saída: milp_vs_ils.xlsx
"""

import glob
import os
import random
import re
import shutil
import time

import pandas as pd
import pulp

import guilherme as ils_mod
from milp import load_instance, compute_y_bounds, objective_value


PASTA = os.path.dirname(os.path.abspath(__file__))
INST_DIR = os.path.join(PASTA, "instancias")
ILS_XLSX = os.path.join(PASTA, "resultados_experimentos.xlsx")
OUT_XLSX = os.path.join(PASTA, "milp_vs_ils.xlsx")

TIME_LIMIT = 1800     # 30 min por instância (professor: testar 30 ou 60 min)
MIP_GAP = 1e-6
SEED_ILS = 975        # semente da execução representativa do ILS


def alpha_do_nome(nome):
    m = re.search(r"alpha-([0-9.]+)\.json$", nome)
    return float(m.group(1)) if m else float("nan")


def resolve_milp(path, time_limit):
    """Resolve pelo MILP. Retorna (status, obj, tempo, provou, locais)."""
    ni, nj, p, a, b = load_instance(path)
    L, U = compute_y_bounds(b, p)

    t0 = time.perf_counter()
    model = pulp.LpProblem("MILP", pulp.LpMaximize)
    x = pulp.LpVariable.dicts("x", range(nj), 0, 1, pulp.LpBinary)
    y = {i: pulp.LpVariable(f"y_{i}", L[i], U[i]) for i in range(ni)}
    w = {(i, j): pulp.LpVariable(f"w_{i}_{j}", 0, U[i]) for i in range(ni) for j in range(nj)}

    model += pulp.lpSum(float(a[i][j]) * w[(i, j)] for i in range(ni) for j in range(nj))
    model += pulp.lpSum(x[j] for j in range(nj)) == p
    for i in range(ni):
        model += pulp.lpSum(float(b[i][j]) * w[(i, j)] for j in range(nj)) == 1.0
        for j in range(nj):
            model += w[(i, j)] <= U[i] * x[j]
            model += w[(i, j)] >= L[i] * x[j]
            model += w[(i, j)] <= y[i] - L[i] * (1 - x[j])
            model += w[(i, j)] >= y[i] - U[i] * (1 - x[j])

    solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=time_limit, gapRel=MIP_GAP)
    model.solve(solver)
    tempo = time.perf_counter() - t0

    status = pulp.LpStatus.get(model.status, "?")
    selected = sorted(j for j in range(nj) if (pulp.value(x[j]) or 0.0) >= 0.5)
    obj = objective_value(a, b, selected) if len(selected) == p else None
    provou = (status == "Optimal") and (tempo < time_limit * 0.98)
    return status, obj, tempo, provou, selected


def solucao_ils(path):
    """Execução representativa e reprodutível do ILS (Guloso). Retorna (Z, locais)."""
    a, b, ni, nj, p = ils_mod.load_instance(path)
    random.seed(SEED_ILS)
    init = ils_mod.greedy_initial_solution(a, b, p)
    final, zf = ils_mod.ils(init, a, b, nj)
    return zf, sorted(final)


def main():
    arquivos = glob.glob(os.path.join(INST_DIR, "*.json"))

    def chave(path):
        nome = os.path.basename(path)
        ni = int(re.search(r"ni-(\d+)", nome).group(1))
        p = int(re.search(r"-p-(\d+)", nome).group(1))
        return (ni, p, alpha_do_nome(nome))

    arquivos.sort(key=chave)  # ordem crescente de dificuldade

    linhas = []
    censurar = False
    for path in arquivos:
        nome = os.path.basename(path)
        ni = int(re.search(r"ni-(\d+)", nome).group(1))
        p = int(re.search(r"-p-(\d+)", nome).group(1))
        alpha = alpha_do_nome(nome)

        if censurar:
            print(f"[CENSURADA] {nome}")
            linhas.append({"Instancia": nome, "ni": ni, "p": p, "alpha": alpha,
                           "MILP_status": "CENSURADA", "MILP_Z": None, "MILP_tempo_s": None,
                           "Locais_MILP": "", "ILS_Z": None, "Locais_ILS": "",
                           "Bate_Z": None, "Mesmos_locais": None, "Provou_otimo": False})
            continue

        print(f"[RODANDO] {nome} ...", flush=True)
        try:
            status, z_milp, tempo, provou, locais_milp = resolve_milp(path, TIME_LIMIT)
        except Exception as e:
            status, z_milp, tempo, provou, locais_milp = f"ERRO:{type(e).__name__}", None, None, False, []
            print(f"   ERRO ao resolver {nome}: {e}")

        z_ils, locais_ils = solucao_ils(path)
        bate_z = (z_milp is not None and abs(z_milp - z_ils) < 0.01)
        mesmos = (locais_milp == locais_ils) if locais_milp else None

        print(f"   status={status} | Z_MILP={z_milp} | t={tempo if tempo is None else round(tempo,1)}s "
              f"| provou={provou} | Z_ILS={z_ils:.4f} | bate_Z={bate_z} | mesmos_locais={mesmos}")

        linhas.append({"Instancia": nome, "ni": ni, "p": p, "alpha": alpha,
                       "MILP_status": status,
                       "MILP_Z": round(z_milp, 4) if z_milp else None,
                       "MILP_tempo_s": round(tempo, 1) if tempo else None,
                       "Locais_MILP": " ".join(map(str, locais_milp)),
                       "ILS_Z": round(z_ils, 4),
                       "Locais_ILS": " ".join(map(str, locais_ils)),
                       "Bate_Z": bate_z, "Mesmos_locais": mesmos, "Provou_otimo": provou})

        if not provou:
            print(f"   >>> Tempo limite atingido sem ótimo. Censurando as maiores a partir daqui.")
            censurar = True

    pd.DataFrame(linhas).to_excel(OUT_XLSX, sheet_name="MILP_vs_ILS", index=False)
    print(f"\nConcluído. Resultados em: {OUT_XLSX}")


if __name__ == "__main__":
    main()
