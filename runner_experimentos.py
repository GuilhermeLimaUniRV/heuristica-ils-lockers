#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Runner de experimentos: executa as duas variantes do ILS (Guloso e GRASP)
sobre todas as instâncias, coleta valor da função objetivo (Z) e tempo, e
exporta os resultados para um arquivo Excel.

IMPORTANTE: este script NÃO reimplementa o algoritmo. Ele reutiliza,
sem alterações, as funções do arquivo do orientador (guilherme.py):
    - greedy_initial_solution / grasp_initial_solution (construções)
    - objective (função objetivo)
    - ils (Iterated Local Search)
    - constantes GRASP_ALPHA, GRASP_DECAY, MAX_ITER, NO_IMPROVE_MAX

Uso:
    python runner_experimentos.py            # experimento completo (24 x 2 x 30)
    python runner_experimentos.py smoke      # teste rápido (2 instâncias x 3 sementes)
"""

import glob
import os
import random
import re
import sys
import time

import numpy as np
import pandas as pd

import guilherme as ils_mod  # reutiliza o código do orientador, sem modificá-lo


# =========================
# Configuração do experimento
# =========================
# 30 sementes distintas, sorteadas aleatoriamente no intervalo [0, 5000].
# A semente-mestra fixa (2026) garante que esse sorteio seja sempre o mesmo,
# preservando a replicabilidade do experimento.
_SEED_RNG = random.Random(2026)
SEEDS = _SEED_RNG.sample(range(0, 5001), 30)
VARIANTES = ["ILS-Guloso", "ILS-GRASP"]
INST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instancias")
OUT_XLSX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resultados_experimentos.xlsx")

# limite de tempo por execução, conforme a metodologia (1 hora de CPU).
# Aplicado apenas em sistemas POSIX (Linux/Docker), via signal.
TIME_LIMIT_S = 3600


class TimeLimitExceeded(Exception):
    pass


def _run_com_limite(func, *args):
    """Executa func com limite de tempo, quando o SO suportar (Linux/Docker)."""
    try:
        import signal

        def _handler(signum, frame):
            raise TimeLimitExceeded()

        signal.signal(signal.SIGALRM, _handler)
        signal.alarm(TIME_LIMIT_S)
        try:
            return func(*args)
        finally:
            signal.alarm(0)
    except (ImportError, AttributeError):
        # Windows: sem SIGALRM. Instâncias são pequenas; roda sem o limite rígido.
        return func(*args)


def alpha_do_nome(nome):
    """Extrai o alpha do nome do arquivo (ex.: ...-alpha-0.6.json -> 0.6)."""
    m = re.search(r"alpha-([0-9.]+)\.json$", nome)
    return float(m.group(1)) if m else float("nan")


def executa_uma(a, b, nj, p, variante, seed):
    """Roda uma execução (uma variante, uma semente) reutilizando guilherme.py."""
    random.seed(seed)  # semente global usada pela construção GRASP e pela perturbação
    t0 = time.perf_counter()

    if variante == "ILS-Guloso":
        init = ils_mod.greedy_initial_solution(a, b, p)
    else:
        init = ils_mod.grasp_initial_solution(
            a, b, p, alpha=ils_mod.GRASP_ALPHA, decay=ils_mod.GRASP_DECAY
        )

    z_inicial = ils_mod.objective(init, a, b)
    sol_final, z_final = _run_com_limite(ils_mod.ils, init, a, b, nj)
    tempo = time.perf_counter() - t0
    return z_inicial, z_final, tempo, sorted(sol_final)


def main():
    smoke = len(sys.argv) > 1 and sys.argv[1].lower() == "smoke"

    arquivos = glob.glob(os.path.join(INST_DIR, "*.json"))
    if not arquivos:
        print(f"Nenhuma instância encontrada em {INST_DIR}. Rode antes gerar_instancias.py.")
        sys.exit(1)

    # ordena por porte (ni), depois p, depois alpha -> processa da menor para a maior
    def _chave(path):
        nome = os.path.basename(path)
        mni = re.search(r"ni-(\d+)", nome)
        mp = re.search(r"-p-(\d+)", nome)
        return (int(mni.group(1)) if mni else 0,
                int(mp.group(1)) if mp else 0,
                alpha_do_nome(nome))

    arquivos.sort(key=_chave)

    seeds = SEEDS[:3] if smoke else SEEDS
    if smoke:
        arquivos = arquivos[:2]
        print(f"[MODO SMOKE] {len(arquivos)} instâncias x {len(seeds)} sementes.\n")

    linhas = []
    total = len(arquivos) * len(VARIANTES) * len(seeds)
    feito = 0

    for path in arquivos:
        a, b, ni, nj, p = ils_mod.load_instance(path)
        nome = os.path.basename(path)
        alpha = alpha_do_nome(nome)

        for variante in VARIANTES:
            for r, seed in enumerate(seeds, start=1):
                z_ini, z_fim, tempo, locais = executa_uma(a, b, nj, p, variante, seed)
                linhas.append({
                    "Instancia": nome,
                    "ni": ni, "nj": nj, "p": p, "alpha": alpha,
                    "Variante": variante,
                    "Rodada": r, "Semente": seed,
                    "Z_inicial": round(z_ini, 4),
                    "Z_final": round(z_fim, 4),
                    "Tempo_s": round(tempo, 4),
                    "Locais": " ".join(map(str, locais)),
                })
                feito += 1
                print(f"[{feito}/{total}] {nome} | {variante} | rodada {r} (sem={seed}) "
                      f"| Z={z_fim:.3f} | t={tempo:.3f}s")

    df = pd.DataFrame(linhas)
    exporta_excel(df)
    print(f"\nConcluído. Resultados em: {OUT_XLSX}")


def _matriz_tempo(df, variante):
    """Matriz de tempo: linhas (ni,p,alpha) x colunas (Rodada/Semente)."""
    sub = df[df["Variante"] == variante]
    return sub.pivot_table(index=["ni", "p", "alpha"],
                           columns=["Rodada", "Semente"], values="Tempo_s")


def exporta_excel(df):
    """
    Gera:
      - Aba 'Bruto': Guloso e GRASP lado a lado (pareados), incluindo o
        CONJUNTO DE LOCAIS escolhido por cada variante (Locais_Guloso/Locais_GRASP).
      - Abas 'Tempo_Guloso' e 'Tempo_GRASP': matriz de tempos.
    Médias, desvios e testes ficam a cargo do usuário.
    """
    idx = ["Instancia", "ni", "nj", "p", "alpha", "Rodada", "Semente"]
    vals = ["Z_inicial", "Z_final", "Tempo_s", "Locais"]
    ren = {"Z_inicial": "Zini", "Z_final": "Zfin", "Tempo_s": "Tempo", "Locais": "Locais"}

    gul = (df[df["Variante"] == "ILS-Guloso"][idx + vals]
           .rename(columns={v: f"{ren[v]}_Guloso" for v in vals}))
    gra = (df[df["Variante"] == "ILS-GRASP"][idx + vals]
           .rename(columns={v: f"{ren[v]}_GRASP" for v in vals}))
    wide = gul.merge(gra, on=idx)

    ordem = idx + ["Zini_Guloso", "Zini_GRASP", "Zfin_Guloso", "Zfin_GRASP",
                   "Tempo_Guloso", "Tempo_GRASP", "Locais_Guloso", "Locais_GRASP"]
    wide = wide[[c for c in ordem if c in wide.columns]]

    with pd.ExcelWriter(OUT_XLSX, engine="openpyxl") as w:
        wide.to_excel(w, sheet_name="Bruto", index=False)
        _matriz_tempo(df, "ILS-Guloso").to_excel(w, sheet_name="Tempo_Guloso")
        _matriz_tempo(df, "ILS-GRASP").to_excel(w, sheet_name="Tempo_GRASP")


if __name__ == "__main__":
    main()
