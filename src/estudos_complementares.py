#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Estudos complementares ao experimento principal (Capítulo 4 do TFC).

A) CALIBRAÇÃO DOS PARÂMETROS DO ILS (Seção 3.6 / objetivo específico 3)
   - Instâncias de calibração DISJUNTAS das do experimento principal:
     um exemplar por porte (ni = 50, 90, 180; nj = ni/2; p = 8), gerados com
     outra semente (1) e outro fator de decaimento da utilidade (alpha = 0,75).
   - Delineamento um-fator-por-vez em torno da configuração de referência
     (perturbação = 1 troca; parada após 100 iterações sem melhora;
     máx. 1000 iterações; GRASP alpha = 0,8 e decaimento = 0,9):
       * intensidade da perturbação k in {1, 2, 3}
       * iterações sem melhora     NI in {25, 50, 100, 200}
       * alpha da LRC do GRASP          in {0,50; 0,65; 0,80; 0,95}
   - 5 sementes próprias (distintas das do experimento principal).

B) ITERAÇÕES ATÉ A CONVERGÊNCIA (hipótese H2)
   - Replica, com contadores, as 5 primeiras sementes do experimento principal
     nas 24 instâncias e nas duas variantes. Como o código é determinístico
     dada a semente, os valores de Z devem coincidir exatamente com os da aba
     'Bruto' de resultados_experimentos.xlsx (validação da instrumentação).

O código do orientador (guilherme.py) NÃO é modificado: suas funções são
reutilizadas; apenas a função objetivo é envolvida por um contador de
avaliações, e o laço do ILS é reproduzido com contadores de iterações.

Saídas: calibracao_parametros.xlsx e iteracoes_convergencia.xlsx
Uso:    python estudos_complementares.py
"""

import glob
import json
import os
import random
import re
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

import guilherme as ils_mod
from gerar_instancias import gerar_uma_instancia

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # raiz do repositório
RES = os.path.join(RAIZ, "resultados")
INST_DIR = os.path.join(RAIZ, "dados", "instancias")
CALIB_DIR = os.path.join(RAIZ, "dados", "instancias_calibracao")
OUT_CALIB = os.path.join(RES, "calibracao_parametros.xlsx")
OUT_ITER = os.path.join(RES, "iteracoes_convergencia.xlsx")
N_WORKERS = 4

# ---------------- contador de avaliações da função objetivo ----------------
_ORIG_OBJ = ils_mod.objective
_N_EVAL = [0]


def _objective_contado(solution, a, b):
    _N_EVAL[0] += 1
    return _ORIG_OBJ(solution, a, b)


ils_mod.objective = _objective_contado   # as funções do módulo passam a usar o contador


# ---------------- ILS instrumentado (mesma lógica de guilherme.ils) ----------------
def roda_ils(a, b, nj, p, variante, seed, k=1, ni_max=100, max_iter=1000,
             g_alpha=0.8, g_decay=0.9):
    random.seed(seed)
    _N_EVAL[0] = 0
    t0 = time.perf_counter()
    if variante == "ILS-Guloso":
        init = ils_mod.greedy_initial_solution(a, b, p)
    else:
        init = ils_mod.grasp_initial_solution(a, b, p, alpha=g_alpha, decay=g_decay)
    t_constr = time.perf_counter() - t0
    z_ini = ils_mod.objective(init, a, b)

    best, bv = ils_mod.local_search_first_improvement(init, a, b, nj)
    eval_best, t_best, it_best, n_melhorias = _N_EVAL[0], time.perf_counter() - t0, 0, 0
    sem_melhora, it = 0, 0
    for it in range(1, max_iter + 1):
        cand = ils_mod.perturb(best, nj, k)
        cand, cv = ils_mod.local_search_first_improvement(cand, a, b, nj)
        if cv > bv + ils_mod.EPS:
            best, bv = cand, cv
            sem_melhora = 0
            n_melhorias += 1
            it_best, eval_best, t_best = it, _N_EVAL[0], time.perf_counter() - t0
        else:
            sem_melhora += 1
        if sem_melhora >= ni_max:
            break
    t_total = time.perf_counter() - t0
    return {"Z_inicial": z_ini, "Z_final": bv, "Locais": " ".join(map(str, sorted(best))),
            "Iteracoes": it, "Iter_melhor": it_best, "N_melhorias": n_melhorias,
            "Aval_total": _N_EVAL[0], "Aval_ate_melhor": eval_best,
            "Tempo_s": t_total, "Tempo_construcao_s": t_constr, "Tempo_ate_melhor_s": t_best,
            "Atingiu_max_iter": it >= max_iter}


# ---------------- A) calibração ----------------
CALIB_CONFIGS = [
    # (nome, k, NI, alpha_grasp, variantes)
    ("Referência (k=1, NI=100, α=0,80)", 1, 100, 0.80, ("ILS-Guloso", "ILS-GRASP")),
    ("Perturbação k=2",                  2, 100, 0.80, ("ILS-Guloso", "ILS-GRASP")),
    ("Perturbação k=3",                  3, 100, 0.80, ("ILS-Guloso", "ILS-GRASP")),
    ("Parada NI=25",                     1,  25, 0.80, ("ILS-Guloso", "ILS-GRASP")),
    ("Parada NI=50",                     1,  50, 0.80, ("ILS-Guloso", "ILS-GRASP")),
    ("Parada NI=200",                    1, 200, 0.80, ("ILS-Guloso", "ILS-GRASP")),
    ("GRASP α=0,50",                     1, 100, 0.50, ("ILS-GRASP",)),
    ("GRASP α=0,65",                     1, 100, 0.65, ("ILS-GRASP",)),
    ("GRASP α=0,95",                     1, 100, 0.95, ("ILS-GRASP",)),
]
CALIB_SEEDS = random.Random(2027).sample(range(0, 5001), 5)


def gera_instancias_calibracao():
    os.makedirs(CALIB_DIR, exist_ok=True)
    np.random.seed(1)                      # semente distinta da do experimento (0)
    caminhos = []
    for ni in (50, 90, 180):
        nj, p, alpha = ni // 2, 8, 0.75     # alpha fora da grade principal {0,6; 0,9}
        _, data = gerar_uma_instancia(ni, nj, p, alpha)
        nome = "calib-ni-%d-nj-%d-p-%d-alpha-%.2f.json" % (ni, nj, p, alpha)
        data["name"] = nome
        caminho = os.path.join(CALIB_DIR, nome)
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=1)
        caminhos.append(caminho)
    return caminhos


def unidade_calibracao(args):
    caminho, seed = args
    a, b, ni, nj, p = ils_mod.load_instance(caminho)
    linhas = []
    for nome, k, nimax, galpha, variantes in CALIB_CONFIGS:
        for v in variantes:
            r = roda_ils(a, b, nj, p, v, seed, k=k, ni_max=nimax, g_alpha=galpha)
            linhas.append({"Instancia": os.path.basename(caminho), "ni": ni, "nj": nj, "p": p,
                           "Configuracao": nome, "k": k, "NI": nimax, "GRASP_alpha": galpha,
                           "Variante": v, "Semente": seed, **r})
    return linhas


# ---------------- B) iterações no experimento principal ----------------
MAIN_SEEDS = random.Random(2026).sample(range(0, 5001), 30)[:5]   # mesmas do runner


def unidade_iteracoes(args):
    caminho, seed = args
    a, b, ni, nj, p = ils_mod.load_instance(caminho)
    linhas = []
    for v in ("ILS-Guloso", "ILS-GRASP"):
        r = roda_ils(a, b, nj, p, v, seed)
        linhas.append({"Instancia": os.path.basename(caminho), "ni": ni, "nj": nj, "p": p,
                       "Variante": v, "Semente": seed, **r})
    return linhas


def _executa(unidades, func, rotulo):
    linhas = []
    t0 = time.perf_counter()
    with Pool(N_WORKERS) as pool:
        for n, res in enumerate(pool.imap_unordered(func, unidades), 1):
            linhas.extend(res)
            print(f"[{rotulo}] {n}/{len(unidades)} unidades | {time.perf_counter()-t0:.0f}s",
                  flush=True)
    return pd.DataFrame(linhas)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    # ---- A) calibração ----
    calib = gera_instancias_calibracao()
    print("Instâncias de calibração:", [os.path.basename(c) for c in calib])
    print("Sementes de calibração:", CALIB_SEEDS, flush=True)
    dfa = _executa([(c, s) for c in calib for s in CALIB_SEEDS], unidade_calibracao, "calibracao")
    dfa.to_excel(OUT_CALIB, sheet_name="Bruto", index=False)
    print("Calibração salva em", OUT_CALIB, flush=True)

    # ---- B) iterações ----
    arqs = sorted(glob.glob(os.path.join(INST_DIR, "*.json")))
    print("Sementes replicadas:", MAIN_SEEDS, flush=True)
    dfb = _executa([(c, s) for c in arqs for s in MAIN_SEEDS], unidade_iteracoes, "iteracoes")

    # validação: os Z devem coincidir com o experimento principal
    bruto = pd.read_excel(os.path.join(RES, "resultados_experimentos.xlsx"), sheet_name="Bruto")
    ok = 0
    for _, r in dfb.iterrows():
        suf = "Guloso" if r["Variante"] == "ILS-Guloso" else "GRASP"
        ref = bruto[(bruto["Instancia"] == r["Instancia"]) & (bruto["Semente"] == r["Semente"])]
        if len(ref) and abs(ref.iloc[0]["Zfin_" + suf] - r["Z_final"]) < 1e-3 \
                and abs(ref.iloc[0]["Zini_" + suf] - r["Z_inicial"]) < 1e-3:
            ok += 1
    val = pd.DataFrame([{"Execucoes_replicadas": len(dfb), "Coincidem_com_experimento": ok}])
    with pd.ExcelWriter(OUT_ITER, engine="openpyxl") as w:
        dfb.to_excel(w, sheet_name="Bruto", index=False)
        val.to_excel(w, sheet_name="Validacao", index=False)
    print(f"Iterações salvas em {OUT_ITER} | validação: {ok}/{len(dfb)} coincidem", flush=True)


if __name__ == "__main__":
    main()
