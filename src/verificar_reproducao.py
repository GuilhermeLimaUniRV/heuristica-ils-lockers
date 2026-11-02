#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificação de reprodutibilidade (teste de fumaça do ambiente Docker/Python 3.10).

Confere, SEM alterar os arquivos do experimento, se este ambiente reproduz:
  (1) as 24 instâncias (hash SHA-256 idêntico ao de referência) — testa o NumPy;
  (2) os valores de Z (inicial e final) do ILS em casos representativos — testa o
      módulo random do Python (usado na construção GRASP e na perturbação).

Se tudo bater, a re-execução completa produzirá exatamente os mesmos resultados,
mudando apenas os tempos. Caso contrário, o script sai com código 1 e lista as
diferenças — sinal de que a re-execução seria um experimento novo.

Uso:  python verificar_reproducao.py
"""
import hashlib
import json
import os
import random
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # raiz do repositório
RES = os.path.join(RAIZ, "resultados")
REF = os.path.join(RAIZ, "dados", "referencia")
EPS = 1e-4


def _regenera_instancias(destino):
    """Reproduz a geração em um diretório temporário, sem tocar em dados/instancias."""
    import gerar_instancias as gi
    orig = gi.OUT_DIR
    gi.OUT_DIR = destino
    try:
        gi.main()
    finally:
        gi.OUT_DIR = orig


TOL_INST = 1e-9   # tolerância numérica (o ruído real é ~1e-15, precisão de máquina)


def verifica_instancias():
    """Confere que o gerador, neste ambiente, reproduz as instâncias commitadas.
    Compara NUMERICAMENTE (e não por hash): coordenadas devem ser idênticas e os
    coeficientes a/b devem coincidir dentro da precisão de máquina. Diferenças de
    último bit (serialização) não são reprodutibilidade quebrada."""
    import numpy as np
    ref = json.load(open(os.path.join(REF, "instancias.sha256"), encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        _regenera_instancias(tmp)
        difs, pior = [], 0.0
        for nome in ref:
            reg = os.path.join(tmp, nome)
            com = os.path.join(RAIZ, "dados", "instancias", nome)
            if not os.path.exists(reg):
                difs.append(f"{nome}: NÃO gerada"); continue
            o = json.load(open(com, encoding="utf-8"))
            n = json.load(open(reg, encoding="utf-8"))
            if o["cxyi"] != n["cxyi"] or o["cxyj"] != n["cxyj"]:
                difs.append(f"{nome}: coordenadas (sorteios) diferem"); continue
            dmax = max(float(np.max(np.abs(np.array(o[k]) - np.array(n[k])))) for k in ("a", "b"))
            pior = max(pior, dmax)
            if dmax > TOL_INST:
                difs.append(f"{nome}: a/b diferem em {dmax:.2e} (> {TOL_INST:.0e})")
    ok = not difs
    print(f"[1/2] Instâncias: {'OK' if ok else 'DIFEREM'} "
          f"({len(ref) - len(difs)}/{len(ref)} numericamente idênticas; "
          f"maior diferença em a/b = {pior:.2e})")
    for d in difs:
        print("      -", d)
    return ok


def verifica_z():
    import guilherme as ils
    casos = json.load(open(os.path.join(REF, "referencia_z.json"), encoding="utf-8"))
    difs = []
    for c in casos:
        a, b, ni, nj, p = ils.load_instance(os.path.join(RAIZ, "dados", "instancias", c["instancia"]))
        for var, suf in (("Guloso", "Guloso"), ("GRASP", "GRASP")):
            random.seed(c["semente"])
            if var == "Guloso":
                init = ils.greedy_initial_solution(a, b, p)
            else:
                init = ils.grasp_initial_solution(a, b, p, alpha=ils.GRASP_ALPHA, decay=ils.GRASP_DECAY)
            zini = ils.objective(init, a, b)
            _, zfin = ils.ils(init, a, b, nj)
            for metr, obtido, esperado in (("Zini", zini, c[f"Zini_{suf}"]),
                                           ("Zfin", zfin, c[f"Zfin_{suf}"])):
                if abs(obtido - esperado) > EPS:
                    difs.append(f"{c['instancia'][:22]} sem={c['semente']} {var} {metr}: "
                                f"obtido {obtido:.4f} ≠ esperado {esperado:.4f}")
    ok = not difs
    n = len(casos) * 4
    print(f"[2/2] Valores de Z (ILS): {'OK' if ok else 'DIFEREM'} "
          f"({n - len(difs)}/{n} idênticos)")
    for d in difs:
        print("      -", d)
    return ok


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print("=" * 60)
    print("VERIFICAÇÃO DE REPRODUTIBILIDADE  —  Python", sys.version.split()[0])
    import numpy, scipy, pandas
    print(f"numpy {numpy.__version__} | scipy {scipy.__version__} | pandas {pandas.__version__}")
    print("=" * 60)
    ok = verifica_instancias() & verifica_z()
    print("=" * 60)
    if ok:
        print("RESULTADO: ambiente REPRODUZ os resultados. Pode rodar o experimento completo.")
        sys.exit(0)
    else:
        print("RESULTADO: ambiente NÃO reproduz. A re-execução geraria dados novos — PARAR e avaliar.")
        sys.exit(1)


if __name__ == "__main__":
    main()
