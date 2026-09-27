#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analise estatistica: compara ILS-Guloso vs ILS-GRASP para tres metricas:
  - qualidade da solucao INICIAL (Z inicial)
  - qualidade da solucao FINAL   (Z final)
  - tempo de execucao (s)

Protocolo (conforme orientador e Secao 3.6):
  1) Shapiro-Wilk nas diferencas (Guloso - GRASP) para verificar normalidade;
  2) se normal (p > 0.05): teste t pareado (compara medias);
     se nao-normal: teste de Wilcoxon (compara medianas).

Le os dados da aba 'Bruto' de resultados_experimentos.xlsx e grava duas abas:
  - 'Testes_Global'       : um teste por metrica (todas as 720 execucoes)
  - 'Testes_PorInstancia' : um teste por metrica em cada instancia (30 repeticoes)
"""

import os
import numpy as np
import pandas as pd
from scipy import stats

PASTA = os.path.dirname(os.path.abspath(__file__))
XLSX = os.path.join(PASTA, "resultados_experimentos.xlsx")
ALPHA = 0.05

METRICAS = [
    ("Qualidade inicial (Z)", "Zini_Guloso", "Zini_GRASP"),
    ("Qualidade final (Z)", "Zfin_Guloso", "Zfin_GRASP"),
    ("Tempo (s)", "Tempo_Guloso", "Tempo_GRASP"),
]


def comparar(gul, gra):
    """Aplica o protocolo Shapiro -> (t pareado | Wilcoxon) a um par de amostras."""
    gul = np.asarray(gul, dtype=float)
    gra = np.asarray(gra, dtype=float)
    dif = gra - gul
    n = len(dif)
    zeros = int(np.sum(np.abs(dif) < 1e-9))

    # todas as diferencas nulas -> amostras identicas
    if np.allclose(dif, 0.0, atol=1e-9):
        return {"n": n, "Shapiro_p": np.nan, "Normal": "-", "Teste": "-",
                "Estatistica": np.nan, "p_valor": 1.0, "Significativo": "Nao",
                "Media_Guloso": round(gul.mean(), 4), "Media_GRASP": round(gra.mean(), 4),
                "Obs": "Amostras identicas (diferencas nulas)"}

    try:
        sh_stat, sh_p = stats.shapiro(dif)
    except Exception:
        sh_p = 0.0
    normal = sh_p > ALPHA

    if normal:
        stat, p = stats.ttest_rel(gul, gra)
        teste = "t pareado"
    else:
        try:
            stat, p = stats.wilcoxon(gul, gra)
        except Exception:
            stat, p = np.nan, 1.0
        teste = "Wilcoxon"

    obs = ""
    if zeros > 0.5 * n:
        obs = f"{zeros}/{n} diferencas nulas (amostras quase identicas)"

    return {"n": n, "Shapiro_p": round(sh_p, 5), "Normal": "Sim" if normal else "Nao",
            "Teste": teste, "Estatistica": round(float(stat), 4) if stat == stat else np.nan,
            "p_valor": round(float(p), 5), "Significativo": "Sim" if p < ALPHA else "Nao",
            "Media_Guloso": round(gul.mean(), 4), "Media_GRASP": round(gra.mean(), 4),
            "Obs": obs}


def main():
    df = pd.read_excel(XLSX, sheet_name="Bruto")

    # ---- Global (todas as execucoes) ----
    linhas = []
    for nome, cg, cr in METRICAS:
        r = comparar(df[cg], df[cr]); r = {"Metrica": nome, **r}
        linhas.append(r)
    glob = pd.DataFrame(linhas)

    # ---- Por instancia ----
    linhas_i = []
    for inst, g in df.groupby("Instancia"):
        for nome, cg, cr in METRICAS:
            r = comparar(g[cg], g[cr])
            r = {"Instancia": inst, "Metrica": nome, **r}
            linhas_i.append(r)
    porinst = pd.DataFrame(linhas_i)

    with pd.ExcelWriter(XLSX, engine="openpyxl", mode="a", if_sheet_exists="replace") as w:
        glob.to_excel(w, sheet_name="Testes_Global", index=False)
        porinst.to_excel(w, sheet_name="Testes_PorInstancia", index=False)

    # ---- resumo no console ----
    print("=" * 70)
    print("ANALISE GLOBAL (720 execucoes, alpha = 0,05)")
    print("=" * 70)
    for _, r in glob.iterrows():
        print(f"\n{r['Metrica']}:")
        print(f"   media Guloso={r['Media_Guloso']} | media GRASP={r['Media_GRASP']}")
        print(f"   Shapiro p={r['Shapiro_p']} -> {'normal' if r['Normal']=='Sim' else 'nao-normal'} "
              f"| Teste: {r['Teste']} | p-valor={r['p_valor']}")
        print(f"   Diferenca significativa? {r['Significativo']}"
              + (f"  ({r['Obs']})" if r['Obs'] else ""))

    print("\n" + "=" * 70)
    print("POR INSTANCIA - resumo (quantas das 24 deram diferenca significativa)")
    print("=" * 70)
    for nome, _, _ in METRICAS:
        sub = porinst[porinst["Metrica"] == nome]
        sig = (sub["Significativo"] == "Sim").sum()
        print(f"   {nome}: {sig}/24 instancias com diferenca significativa")


if __name__ == "__main__":
    main()
