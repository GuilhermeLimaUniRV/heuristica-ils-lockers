#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ILS para o problema de localização de lockers com função objetivo de soma de frações.

Uso:
    python ils.py ni-40-nj-20-p-5-alpha-0.5.json

Opcionalmente, é possível informar uma semente aleatória:
    python ils.py ni-40-nj-20-p-5-alpha-0.5.json 123

Para trocar a construção inicial, altere manualmente no bloco main():
    sol_init = greedy_initial_solution(a, b, p)
    # sol_init = grasp_initial_solution(a, b, p, alpha=GRASP_ALPHA)

ou comente/descomente as linhas correspondentes.
"""

import json
import random
import sys
import time
from typing import List, Sequence, Tuple


# =========================
# Parâmetros do algoritmo
# =========================
MAX_ITER = 1000          # número máximo de iterações da ILS
NO_IMPROVE_MAX = 100     # parada após esse número de iterações sem melhora
PERTURB_SWAPS = 1        # perturbação com apenas uma troca, conforme o projeto
GRASP_ALPHA = 0.8        # parâmetro alpha da LRC/RCL do GRASP
GRASP_DECAY = 0.9        # decaimento multiplicativo do alpha a cada seleção
EPS = 1e-10              # tolerância numérica para considerar melhora
DEFAULT_SEED = 0         # semente padrão, para reprodutibilidade


# =========================
# Leitura da instância
# =========================
def load_instance(path: str) -> Tuple[List[List[float]], List[List[float]], int, int, int]:
    """Lê a instância JSON e retorna a, b, ni, nj e p."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    a = data["a"]
    b = data["b"]
    ni = int(data.get("ni", len(a)))
    nj = int(data.get("nj", len(a[0]) if a else 0))
    p = int(data["p"])

    if len(a) != ni or len(b) != ni:
        raise ValueError("Dimensão inconsistente: ni não confere com as matrizes a e b.")
    if any(len(row) != nj for row in a) or any(len(row) != nj for row in b):
        raise ValueError("Dimensão inconsistente: alguma linha de a ou b não possui nj colunas.")
    if not (0 < p <= nj):
        raise ValueError("O parâmetro p deve satisfazer 0 < p <= nj.")

    return a, b, ni, nj, p


# =========================
# Função objetivo
# =========================
def objective(solution: Sequence[int], a: List[List[float]], b: List[List[float]]) -> float:
    """
    Calcula Z(x) = soma_i (sum_j a_ij x_j) / (sum_j b_ij x_j).

    A solução é representada por uma lista de índices dos locais abertos.
    """
    total = 0.0
    for i in range(len(a)):
        num = 0.0
        den = 0.0
        for j in solution:
            num += a[i][j]
            den += b[i][j]
        if den > EPS:
            total += num / den
    return total


def greedy_scores(a: List[List[float]], b: List[List[float]]) -> List[float]:
    """
    Calcula S_j = (sum_i a_ij) / (sum_i b_ij) para cada candidato j.
    """
    ni = len(a)
    nj = len(a[0])
    scores = []
    for j in range(nj):
        sum_a = sum(a[i][j] for i in range(ni))
        sum_b = sum(b[i][j] for i in range(ni))
        scores.append(sum_a / sum_b if sum_b > EPS else 0.0)
    return scores


# =========================
# Construções iniciais
# =========================
def greedy_initial_solution(a: List[List[float]], b: List[List[float]], p: int) -> List[int]:
    """
    Construção gulosa determinística:
    seleciona os p candidatos com maior escore S_j.
    """
    scores = greedy_scores(a, b)
    candidates = list(range(len(scores)))
    candidates.sort(key=lambda j: scores[j], reverse=True)
    return sorted(candidates[:p])


def grasp_initial_solution(
    a: List[List[float]],
    b: List[List[float]],
    p: int,
    alpha: float = GRASP_ALPHA,
    decay: float = GRASP_DECAY,
) -> List[int]:
    """
    Construção GRASP com Lista Restrita de Candidatos (LRC/RCL).

    RCL = {j | S_j >= S_min + alpha * (S_max - S_min)}.
    Após cada seleção, alpha recebe alpha * decay.
    """
    scores = greedy_scores(a, b)
    remaining = set(range(len(scores)))
    solution = []
    current_alpha = alpha

    while len(solution) < p:
        rem_list = list(remaining)
        s_values = [scores[j] for j in rem_list]
        s_min = min(s_values)
        s_max = max(s_values)
        threshold = s_min + current_alpha * (s_max - s_min)

        rcl = [j for j in rem_list if scores[j] >= threshold - EPS]
        chosen = random.choice(rcl)

        solution.append(chosen)
        remaining.remove(chosen)
        current_alpha *= decay

    return sorted(solution)


# =========================
# Busca local first-improvement com uma troca
# =========================
def first_improvement_swap(
    solution: Sequence[int],
    current_value: float,
    a: List[List[float]],
    b: List[List[float]],
    nj: int,
) -> Tuple[List[int], float, bool]:
    """
    Procura a primeira troca 1-out/1-in que melhora a solução.

    Movimento: remove um local aberto e adiciona um local fechado.
    Critério: first improvement.
    """
    open_set = set(solution)
    closed = [j for j in range(nj) if j not in open_set]

    # Ordem fixa para garantir reprodutibilidade no first-improvement.
    for j_out in sorted(open_set):
        for j_in in closed:
            new_solution = list(open_set)
            new_solution.remove(j_out)
            new_solution.append(j_in)
            new_solution.sort()

            new_value = objective(new_solution, a, b)
            if new_value > current_value + EPS:
                return new_solution, new_value, True

    return list(solution), current_value, False


def local_search_first_improvement(
    solution: Sequence[int],
    a: List[List[float]],
    b: List[List[float]],
    nj: int,
) -> Tuple[List[int], float]:
    """
    Executa busca local até não existir troca 1-out/1-in com melhora.
    """
    current_solution = list(solution)
    current_value = objective(current_solution, a, b)

    while True:
        new_solution, new_value, improved = first_improvement_swap(
            current_solution, current_value, a, b, nj
        )
        if not improved:
            break
        current_solution = new_solution
        current_value = new_value

    return current_solution, current_value


# =========================
# Perturbação e ILS
# =========================
def perturb(solution: Sequence[int], nj: int, n_swaps: int = PERTURB_SWAPS) -> List[int]:
    """
    Aplica n_swaps trocas aleatórias forçadas.
    Como definido no projeto, o padrão é uma única troca.
    """
    sol = set(solution)

    for _ in range(n_swaps):
        if not sol or len(sol) == nj:
            break

        j_out = random.choice(list(sol))
        closed = [j for j in range(nj) if j not in sol]
        j_in = random.choice(closed)

        sol.remove(j_out)
        sol.add(j_in)

    return sorted(sol)


def ils(
    initial_solution: Sequence[int],
    a: List[List[float]],
    b: List[List[float]],
    nj: int,
    max_iter: int = MAX_ITER,
    no_improve_max: int = NO_IMPROVE_MAX,
) -> Tuple[List[int], float]:
    """
    Iterated Local Search com:
    - busca local first-improvement;
    - movimento de uma troca;
    - perturbação com uma troca;
    - aceitação somente quando melhora a melhor solução global.
    """
    best_solution, best_value = local_search_first_improvement(initial_solution, a, b, nj)

    no_improve = 0
    for _ in range(max_iter):
        candidate = perturb(best_solution, nj, PERTURB_SWAPS)
        candidate, candidate_value = local_search_first_improvement(candidate, a, b, nj)

        if candidate_value > best_value + EPS:
            best_solution = candidate
            best_value = candidate_value
            no_improve = 0
        else:
            no_improve += 1

        if no_improve >= no_improve_max:
            break

    return best_solution, best_value


# =========================
# Execução principal
# =========================
def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python ils.py <arquivo_instancia.json> [semente]")
        sys.exit(1)

    instance_path = sys.argv[1]
    seed = int(sys.argv[2]) if len(sys.argv) >= 3 else DEFAULT_SEED
    random.seed(seed)

    total_start = time.perf_counter()
    a, b, ni, nj, p = load_instance(instance_path)

    # ==========================================================
    # ESCOLHA DA CONSTRUÇÃO INICIAL
    # Deixe ativa apenas uma das duas linhas abaixo.
    # ==========================================================

    init_start = time.perf_counter()

    # Construção 1: método guloso determinístico
    #sol_init = greedy_initial_solution(a, b, p)

    # Construção 2: GRASP com aleatoriedade controlada
    sol_init = grasp_initial_solution(a, b, p, alpha=GRASP_ALPHA, decay=GRASP_DECAY)

    init_value = objective(sol_init, a, b)
    init_time = time.perf_counter() - init_start

    sol_final, final_value = ils(sol_init, a, b, nj)
    total_time = time.perf_counter() - total_start

    print(f"Solucao inicial: {init_value:.2f}")
    print(f"Tempo solucao inicial (s): {init_time:.4f}")
    print(f"Solucao final: {final_value:.2f}")
    print(f"Tempo total (s): {total_time:.4f}")

    # Caso queira conferir os locais escolhidos, descomente as linhas abaixo.
    # print(f"Locais iniciais: {sol_init}")
    # print(f"Locais finais: {sol_final}")


if __name__ == "__main__":
    main()
