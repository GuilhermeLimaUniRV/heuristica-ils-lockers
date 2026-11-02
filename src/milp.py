#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MILP em PuLP para o problema de localização com função objetivo soma de frações.

Uso:
    python milp_pulp.py ni-40-nj-20-p-5-alpha-0.5.json

Modelo original:
    max Z(x) = sum_i (sum_j a[i][j] x[j]) / (sum_j b[i][j] x[j])
    s.a.     sum_j x[j] = p
             x[j] in {0,1}

Linearização exata usada no MILP:
    y[i]    = 1 / (sum_j b[i][j] x[j])
    w[i][j] = x[j] * y[i]

Então:
    max sum_i sum_j a[i][j] w[i][j]
    s.a. sum_j b[i][j] w[i][j] = 1, para todo i
         w[i][j] = x[j] y[i] via envoltória de McCormick,
         usando limites L[i] <= y[i] <= U[i].

Como x[j] é binária, a linearização de McCormick é exata.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import List, Sequence, Tuple


TIME_LIMIT_SECONDS = 1800
MIP_GAP = 1e-6
CBC_MSG = False


def load_instance(path: str | Path) -> Tuple[int, int, int, List[List[float]], List[List[float]]]:
    """Carrega a instância JSON com chaves ni, nj, p, a e b."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    ni = int(data["ni"])
    nj = int(data["nj"])
    p = int(data["p"])
    a = data["a"]
    b = data["b"]

    if len(a) != ni or len(b) != ni:
        raise ValueError("Dimensão inconsistente: len(a) ou len(b) diferente de ni.")
    if any(len(row) != nj for row in a) or any(len(row) != nj for row in b):
        raise ValueError("Dimensão inconsistente: alguma linha de a ou b tem tamanho diferente de nj.")
    if not (1 <= p <= nj):
        raise ValueError("O parâmetro p deve satisfazer 1 <= p <= nj.")

    return ni, nj, p, a, b


def objective_value(a: Sequence[Sequence[float]], b: Sequence[Sequence[float]], selected: Sequence[int]) -> float:
    """Calcula diretamente a função objetivo original para uma solução binária."""
    value = 0.0
    for ai, bi in zip(a, b):
        numerator = sum(ai[j] for j in selected)
        denominator = sum(bi[j] for j in selected)
        if denominator <= 0.0:
            raise ZeroDivisionError("Denominador não positivo encontrado ao avaliar a solução.")
        value += numerator / denominator
    return value


def compute_y_bounds(b: Sequence[Sequence[float]], p: int) -> Tuple[List[float], List[float]]:
    """
    Calcula limites para y[i] = 1 / sum_j b[i][j] x[j].

    Como exatamente p instalações são abertas:
        menor denominador possível = soma dos p menores b[i][j]
        maior denominador possível = soma dos p maiores b[i][j]

    Logo:
        L[i] = 1 / maior_denominador
        U[i] = 1 / menor_denominador
    """
    L: List[float] = []
    U: List[float] = []

    for i, row in enumerate(b):
        sorted_b = sorted(float(v) for v in row)
        min_den = sum(sorted_b[:p])
        max_den = sum(sorted_b[-p:])

        if min_den <= 0.0 or max_den <= 0.0:
            raise ValueError(
                f"Não foi possível calcular limites positivos para y[{i}]. "
                "Verifique se todos os valores de b são positivos."
            )

        L.append(1.0 / max_den)
        U.append(1.0 / min_den)

    return L, U


def solve_milp(instance_path: str | Path) -> None:
    """Monta e resolve o MILP usando PuLP/CBC."""
    try:
        import pulp
    except ImportError as exc:
        raise SystemExit(
            "Erro: a biblioteca PuLP não está instalada.\n"
            "Instale com: pip install pulp\n"
            "Depois execute novamente: python milp_pulp.py arquivo.json"
        ) from exc

    ni, nj, p, a, b = load_instance(instance_path)
    L, U = compute_y_bounds(b, p)

    start_total = time.perf_counter()

    model = pulp.LpProblem("MILP_Soma_de_Fracoes_Locker", pulp.LpMaximize)

    # Variável binária: x[j] = 1 se o candidato j é escolhido.
    x = pulp.LpVariable.dicts("x", range(nj), lowBound=0, upBound=1, cat=pulp.LpBinary)

    # Variável contínua: y[i] = 1 / denominador_i.
    y = {
        i: pulp.LpVariable(f"y_{i}", lowBound=L[i], upBound=U[i], cat=pulp.LpContinuous)
        for i in range(ni)
    }

    # Variável contínua: w[i,j] = x[j] * y[i].
    w = {
        (i, j): pulp.LpVariable(f"w_{i}_{j}", lowBound=0, upBound=U[i], cat=pulp.LpContinuous)
        for i in range(ni)
        for j in range(nj)
    }

    # Função objetivo linearizada.
    model += pulp.lpSum(float(a[i][j]) * w[(i, j)] for i in range(ni) for j in range(nj)), "Z"

    # Exatamente p armários/localidades escolhidos.
    model += pulp.lpSum(x[j] for j in range(nj)) == p, "cardinalidade"

    for i in range(ni):
        # Define y[i] implicitamente pela igualdade: sum_j b[i][j] * w[i,j] = 1.
        model += pulp.lpSum(float(b[i][j]) * w[(i, j)] for j in range(nj)) == 1.0, f"denominador_{i}"

        for j in range(nj):
            # McCormick para w[i,j] = x[j] * y[i], com L[i] <= y[i] <= U[i].
            model += w[(i, j)] <= U[i] * x[j], f"mcc_ubx_{i}_{j}"
            model += w[(i, j)] >= L[i] * x[j], f"mcc_lbx_{i}_{j}"
            model += w[(i, j)] <= y[i] - L[i] * (1 - x[j]), f"mcc_uby_{i}_{j}"
            model += w[(i, j)] >= y[i] - U[i] * (1 - x[j]), f"mcc_lby_{i}_{j}"

    solver = pulp.PULP_CBC_CMD(
        msg=CBC_MSG,
        timeLimit=TIME_LIMIT_SECONDS,
        gapRel=MIP_GAP,
    )

    model.solve(solver)
    total_time = time.perf_counter() - start_total

    status = pulp.LpStatus.get(model.status, "Status_desconhecido")
    selected = [j for j in range(nj) if (pulp.value(x[j]) or 0.0) >= 0.5]

    print(f"Status: {status}")

    if len(selected) != p:
        print("Aviso: a solução retornada não possui exatamente p instalações selecionadas.")
        print(f"Selecionados: {selected}")
        print(f"Tempo total (s): {total_time:.2f}")
        return

    true_obj = objective_value(a, b, selected)
    model_obj = pulp.value(model.objective)

    print(f"Solucao MILP: {true_obj:.2f}")
    print(f"Tempo total (s): {total_time:.2f}")
    print("Instalacoes selecionadas:", " ".join(str(j) for j in selected))

    # Esta linha ajuda a conferir se a linearização bateu com a função original.
    if model_obj is not None:
        print(f"Objetivo linearizado: {model_obj:.2f}")


def main() -> None:
    if len(sys.argv) != 2:
        print("Uso: python milp_pulp.py arquivo_instancia.json")
        raise SystemExit(1)

    solve_milp(sys.argv[1])


if __name__ == "__main__":
    main()
