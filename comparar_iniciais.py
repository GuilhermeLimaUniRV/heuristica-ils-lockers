#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compara APENAS as soluções INICIAIS (sem rodar o ILS) geradas por:
  - Guloso: determinístico (sempre o mesmo conjunto);
  - GRASP : aleatório via LRC (muda a cada semente).

Para cada instância mostra o Guloso e 3 amostras de GRASP, indicando se o
conjunto do GRASP difere do Guloso (validação do ponto de partida distinto).

Reutiliza as funções do orientador (guilherme.py).
Saída: 'solucoes_iniciais.xlsx' (aba única, formatada).
"""

import glob
import os
import random
import re

import pandas as pd

import guilherme as m


PASTA = os.path.dirname(os.path.abspath(__file__))
INST_DIR = os.path.join(PASTA, "instancias")
OUT_XLSX = os.path.join(PASTA, "solucoes_iniciais.xlsx")

# 3 sementes de GRASP por instância
SEMENTES_GRASP = [975, 2617, 4116]


def alpha_do_nome(nome):
    mm = re.search(r"alpha-([0-9.]+)\.json$", nome)
    return float(mm.group(1)) if mm else float("nan")


def chave(path):
    nome = os.path.basename(path)
    ni = int(re.search(r"ni-(\d+)", nome).group(1))
    p = int(re.search(r"-p-(\d+)", nome).group(1))
    return (ni, p, alpha_do_nome(nome))


def main():
    arquivos = sorted(glob.glob(os.path.join(INST_DIR, "*.json")), key=chave)
    linhas = []

    for path in arquivos:
        a, b, ni, nj, p = m.load_instance(path)
        nome = os.path.basename(path)

        # Guloso (determinístico) — referência de comparação
        gul = sorted(m.greedy_initial_solution(a, b, p))
        z_gul = m.objective(gul, a, b)
        linhas.append({
            "Instancia": nome, "ni": ni, "nj": nj, "p": p, "alpha": alpha_do_nome(nome),
            "Metodo": "Guloso", "Semente": "-",
            "Z_inicial": round(z_gul, 4), "Locais": " ".join(map(str, gul)),
            "Difere_do_Guloso": "-", "Locais_diferentes": 0,
        })

        # 3 amostras de GRASP
        for s in SEMENTES_GRASP:
            random.seed(s)
            gr = sorted(m.grasp_initial_solution(a, b, p))
            z_gr = m.objective(gr, a, b)
            ndif = len(set(gr) - set(gul))
            linhas.append({
                "Instancia": nome, "ni": ni, "nj": nj, "p": p, "alpha": alpha_do_nome(nome),
                "Metodo": "GRASP", "Semente": s,
                "Z_inicial": round(z_gr, 4), "Locais": " ".join(map(str, gr)),
                "Difere_do_Guloso": "Sim" if gr != gul else "Nao",
                "Locais_diferentes": ndif,
            })

    df = pd.DataFrame(linhas)

    with pd.ExcelWriter(OUT_XLSX, engine="openpyxl") as w:
        df.to_excel(w, sheet_name="Solucoes_Iniciais", index=False)
        _formatar(w.book["Solucoes_Iniciais"], df)

    # resumo no console
    grasp = df[df["Metodo"] == "GRASP"]
    dif = (grasp["Difere_do_Guloso"] == "Sim").sum()
    print(f"Amostras GRASP: {len(grasp)} | diferentes do Guloso: {dif} "
          f"| iguais: {len(grasp)-dif}")
    print(f"Salvo em: {OUT_XLSX}")


def _formatar(ws, df):
    """Formatação básica: cabeçalho em negrito, largura de coluna e cores por método."""
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter

    header_fill = PatternFill("solid", fgColor="1F4E78")
    header_font = Font(bold=True, color="FFFFFF")
    fill_gul = PatternFill("solid", fgColor="FCE4D6")   # laranja claro (Guloso)
    fill_gra = PatternFill("solid", fgColor="E2EFDA")   # verde claro (GRASP)

    # cabeçalho
    for j, col in enumerate(df.columns, start=1):
        c = ws.cell(row=1, column=j)
        c.fill = header_fill
        c.font = header_font
        c.alignment = Alignment(horizontal="center", vertical="center")

    # largura das colunas
    larguras = {"Instancia": 34, "Locais": 40, "Metodo": 9, "Difere_do_Guloso": 16,
                "Locais_diferentes": 16, "Z_inicial": 11}
    for j, col in enumerate(df.columns, start=1):
        ws.column_dimensions[get_column_letter(j)].width = larguras.get(col, 8)

    # cores por método + linha divisória entre instâncias
    col_metodo = list(df.columns).index("Metodo") + 1
    for i in range(len(df)):
        metodo = ws.cell(row=i + 2, column=col_metodo).value
        fill = fill_gul if metodo == "Guloso" else fill_gra
        for j in range(1, len(df.columns) + 1):
            ws.cell(row=i + 2, column=j).fill = fill

    ws.freeze_panes = "A2"  # congela o cabeçalho


if __name__ == "__main__":
    main()
