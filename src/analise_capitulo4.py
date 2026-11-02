#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Análises que sustentam o Capítulo 4 (Resultados e Discussões).

Entradas : resultados_experimentos.xlsx (aba Bruto) e milp_vs_ils.xlsx
Saída    : analise_capitulo4.xlsx (uma aba por tabela do capítulo)

Inclui, conforme a Seção 3.6:
  - média, desvio-padrão e IC de 95% por porte e por alpha (Zini, Zfin, tempo);
  - Shapiro-Wilk -> t pareado ou Wilcoxon (global, por porte e por instância),
    com tamanho de efeito (correlação rank-bisserial pareada);
  - comparações múltiplas entre portes: Kruskal-Wallis + post-hoc de Nemenyi;
  - Friedman + Nemenyi entre MILP, ILS-Guloso e ILS-GRASP (24 instâncias);
  - comparação com o MILP (otimalidade, gaps, aceleração).
"""

import math
import os
import sys
from itertools import combinations

import numpy as np
import pandas as pd
from scipy import stats

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # raiz do repositório
RES = os.path.join(RAIZ, "resultados")
ALFA = 0.05
PORTE = {50: "Pequeno", 90: "Médio", 180: "Grande"}


def ic95(x):
    x = np.asarray(x, float)
    n, m, s = len(x), x.mean(), x.std(ddof=1)
    h = stats.t.ppf(0.975, n - 1) * s / math.sqrt(n) if n > 1 else 0.0
    return m, s, m - h, m + h


def rank_bisserial(d):
    """Correlação rank-bisserial pareada (efeito do Wilcoxon), em [-1, 1].

    Calculada sobre TODOS os pares: as diferenças nulas recebem os menores postos e
    entram no denominador (não favorecem nenhuma variante). Assim, amostras quase
    idênticas resultam em efeito próximo de zero, e não em um efeito inflado
    pelos poucos pares não nulos."""
    d = np.asarray(d, float)
    d = np.where(np.abs(d) < 1e-9, 0.0, d)
    if np.all(d == 0):
        return 0.0
    r = stats.rankdata(np.abs(d))
    wp, wm = r[d > 0].sum(), r[d < 0].sum()
    return (wp - wm) / r.sum()


def protocolo(g, r):
    """Shapiro nas diferenças -> t pareado (normal) ou Wilcoxon. Diferença = GRASP - Guloso."""
    g, r = np.asarray(g, float), np.asarray(r, float)
    d = r - g
    nulas = int(np.sum(np.abs(d) < 1e-9))
    if np.allclose(d, 0, atol=1e-9):
        return dict(n=len(d), shapiro_p=np.nan, teste="—", p_valor=1.0, efeito=0.0, nulas=nulas,
                    dif_media=0.0)
    try:
        sp = stats.shapiro(d).pvalue
    except Exception:
        sp = 0.0
    if sp > ALFA:
        p = stats.ttest_rel(r, g).pvalue
        teste = "t pareado"
    else:
        try:
            p = stats.wilcoxon(r, g).pvalue
        except ValueError:
            p = 1.0
        teste = "Wilcoxon"
    return dict(n=len(d), shapiro_p=sp, teste=teste, p_valor=p, efeito=rank_bisserial(d),
                nulas=nulas, dif_media=d.mean())


def nemenyi_kw(grupos):
    """Post-hoc de Nemenyi após Kruskal-Wallis (amostras independentes)."""
    nomes = list(grupos)
    dados = np.concatenate([np.asarray(grupos[k], float) for k in nomes])
    ranks = stats.rankdata(dados)
    N = len(dados)
    _, cont = np.unique(dados, return_counts=True)
    C = 1 - (np.sum(cont ** 3 - cont) / (N ** 3 - N))      # correção de empates
    pos, medias, ns = 0, {}, {}
    for k in nomes:
        n = len(grupos[k]); medias[k] = ranks[pos:pos + n].mean(); ns[k] = n; pos += n
    out = []
    for a, b in combinations(nomes, 2):
        q = abs(medias[a] - medias[b]) / math.sqrt(N * (N + 1) / 12 * (1 / ns[a] + 1 / ns[b]))
        q = q / math.sqrt(C) if C > 0 else q
        p = 1 - stats.studentized_range.cdf(q * math.sqrt(2), len(nomes), np.inf)
        out.append((a, b, medias[a], medias[b], min(max(p, 0.0), 1.0)))
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    br = pd.read_excel(os.path.join(RES, "resultados_experimentos.xlsx"), sheet_name="Bruto")
    mv = pd.read_excel(os.path.join(RES, "milp_vs_ils.xlsx"))
    br["Porte"] = br["ni"].map(PORTE)
    abas = {}

    # ---------- T1: caracterização das instâncias ----------
    inst = (br.groupby("Instancia")[["ni", "nj", "p", "alpha"]].first().reset_index()
            .sort_values(["ni", "p", "alpha"]))
    inst["Porte"] = inst["ni"].map(PORTE)
    inst["Espaco_busca"] = [math.comb(int(nj), int(p)) for nj, p in zip(inst.nj, inst.p)]
    abas["T_instancias"] = inst

    # ---------- T2: descritiva (média, DP, IC95) por porte e por alpha ----------
    linhas = []
    for seg_col, seg_vals in (("Porte", ["Pequeno", "Médio", "Grande"]), ("alpha", [0.6, 0.9])):
        for sv in seg_vals:
            sub = br[br[seg_col] == sv]
            for met, cg, cr in (("Zini", "Zini_Guloso", "Zini_GRASP"),
                                ("Zfin", "Zfin_Guloso", "Zfin_GRASP"),
                                ("Tempo", "Tempo_Guloso", "Tempo_GRASP")):
                for var, col in (("Guloso", cg), ("GRASP", cr)):
                    m, s, lo, hi = ic95(sub[col])
                    linhas.append(dict(Segmento=seg_col, Valor=sv, Metrica=met, Variante=var,
                                       n=len(sub), Media=m, DP=s, IC_inf=lo, IC_sup=hi))
    abas["T_descritiva"] = pd.DataFrame(linhas)

    # ---------- T3: testes global, por porte e por instância ----------
    mets = (("Zini", "Zini_Guloso", "Zini_GRASP"), ("Zfin", "Zfin_Guloso", "Zfin_GRASP"),
            ("Tempo", "Tempo_Guloso", "Tempo_GRASP"))
    lin = []
    for escopo, grupos in (("Global", [("Todas", br)]),
                           ("Porte", [(p, br[br.Porte == p]) for p in ["Pequeno", "Médio", "Grande"]])):
        for nome, sub in grupos:
            for met, cg, cr in mets:
                lin.append(dict(Escopo=escopo, Grupo=nome, Metrica=met,
                                **protocolo(sub[cg], sub[cr])))
    abas["T_testes_agregados"] = pd.DataFrame(lin)

    lin = []
    for nome, sub in br.groupby("Instancia"):
        for met, cg, cr in mets:
            r = protocolo(sub[cg], sub[cr])
            lin.append(dict(Instancia=nome, ni=sub.ni.iloc[0], p=sub.p.iloc[0],
                            alpha=sub.alpha.iloc[0], Porte=PORTE[sub.ni.iloc[0]], Metrica=met,
                            Media_Guloso=sub[cg].mean(), Media_GRASP=sub[cr].mean(), **r))
    pi = pd.DataFrame(lin)
    pi["Signif"] = pi["p_valor"] < ALFA
    pi["Favorece"] = np.where(~pi["Signif"], "—",
                              np.where(pi["dif_media"] > 0,
                                       np.where(pi["Metrica"] == "Tempo", "Guloso", "GRASP"),
                                       np.where(pi["Metrica"] == "Tempo", "GRASP", "Guloso")))
    abas["T_testes_instancia"] = pi.sort_values(["ni", "p", "alpha", "Metrica"])

    # ---------- T4: Kruskal-Wallis + Nemenyi entre portes (diferença relativa %) ----------
    lin = []
    for met, cg, cr in (("Zini", "Zini_Guloso", "Zini_GRASP"), ("Tempo", "Tempo_Guloso", "Tempo_GRASP")):
        grupos = {p: (100 * (br[br.Porte == p][cr] - br[br.Porte == p][cg])
                      / br[br.Porte == p][cg]).values for p in ["Pequeno", "Médio", "Grande"]}
        H, pkw = stats.kruskal(*grupos.values())
        for a, b, ra, rb, p in nemenyi_kw(grupos):
            lin.append(dict(Metrica=met, KW_H=H, KW_p=pkw, Par=f"{a} × {b}",
                            Rank_medio_A=ra, Rank_medio_B=rb, Nemenyi_p=p,
                            Mediana_A=np.median(grupos[a]), Mediana_B=np.median(grupos[b])))
    abas["T_nemenyi_portes"] = pd.DataFrame(lin)

    # ---------- T5: comparação com o MILP ----------
    agg = br.groupby("Instancia").agg(ZiG=("Zini_Guloso", "mean"), ZiR=("Zini_GRASP", "mean"),
                                      ZfG=("Zfin_Guloso", "mean"), ZfR=("Zfin_GRASP", "mean"),
                                      ZfG_min=("Zfin_Guloso", "min"), ZfR_min=("Zfin_GRASP", "min"),
                                      ZfG_max=("Zfin_Guloso", "max"), ZfR_max=("Zfin_GRASP", "max"),
                                      TG=("Tempo_Guloso", "mean"), TR=("Tempo_GRASP", "mean")).reset_index()
    t5 = mv.merge(agg, on="Instancia").sort_values(["ni", "p", "alpha"])
    t5["BKS"] = t5[["MILP_Z", "ZfG_max", "ZfR_max"]].max(axis=1)
    execs = []
    for _, r in t5.iterrows():
        sub = br[br.Instancia == r.Instancia]
        z = np.concatenate([sub.Zfin_Guloso.values, sub.Zfin_GRASP.values])
        execs.append(int(np.sum(np.abs(z - r.BKS) / r.BKS < 1e-4)))
    t5["Execucoes_no_BKS"] = execs                         # de 60 (30 por variante)
    t5["Gap_MILP_vs_BKS_%"] = 100 * (t5.BKS - t5.MILP_Z) / t5.BKS
    t5["Aceleracao_G"] = t5.MILP_tempo_s / t5.TG
    t5["Aceleracao_R"] = t5.MILP_tempo_s / t5.TR
    abas["T_milp"] = t5

    # ---------- T6: Friedman + Nemenyi (MILP, ILS-Guloso, ILS-GRASP) ----------
    lin = []
    k, N = 3, len(t5)
    for met, cols, maior_melhor in (("Qualidade (Z)", ["MILP_Z", "ZfG", "ZfR"], True),
                                    ("Tempo (s)", ["MILP_tempo_s", "TG", "TR"], False)):
        M = t5[cols].values.astype(float)
        M = np.round(M, 4)
        ranks = np.array([stats.rankdata(-row if maior_melhor else row) for row in M])
        rm = ranks.mean(axis=0)
        try:
            chi, pf = stats.friedmanchisquare(*M.T)
        except ValueError:
            chi, pf = np.nan, 1.0
        cd = 2.343 * math.sqrt(k * (k + 1) / (6 * N))        # q_0,05 (k=3) = 2,343
        for (i, a), (j, b) in combinations(enumerate(["MILP", "ILS-Guloso", "ILS-GRASP"]), 2):
            q = abs(rm[i] - rm[j]) / math.sqrt(k * (k + 1) / (6 * N))
            p = 1 - stats.studentized_range.cdf(q * math.sqrt(2), k, np.inf)
            lin.append(dict(Metrica=met, Friedman_chi2=chi, Friedman_p=pf, CD=cd,
                            Par=f"{a} × {b}", Rank_A=rm[i], Rank_B=rm[j],
                            Dif_rank=abs(rm[i] - rm[j]), Nemenyi_p=min(max(p, 0), 1)))
    abas["T_friedman"] = pd.DataFrame(lin)

    # ---------- indicadores avulsos ----------
    mesmos = int((br.Locais_Guloso == br.Locais_GRASP).sum())
    gap_ini = br.assign(GapG=100 * (br.Zfin_Guloso - br.Zini_Guloso) / br.Zfin_Guloso,
                        GapR=100 * (br.Zfin_GRASP - br.Zini_GRASP) / br.Zfin_GRASP)
    ind = [dict(Indicador="Pares com o mesmo conjunto de locais", Valor=f"{mesmos}/{len(br)}"),
           dict(Indicador="Distância média inicial→final Guloso (%)", Valor=gap_ini.GapG.mean()),
           dict(Indicador="Distância média inicial→final GRASP (%)", Valor=gap_ini.GapR.mean())]
    for p in ["Pequeno", "Médio", "Grande"]:
        s = gap_ini[gap_ini.Porte == p]
        ind.append(dict(Indicador=f"Distância inicial→final {p} (G/R %)",
                        Valor=f"{s.GapG.mean():.2f} / {s.GapR.mean():.2f}"))
    abas["T_indicadores"] = pd.DataFrame(ind)

    with pd.ExcelWriter(os.path.join(RES, "analise_capitulo4.xlsx"), engine="openpyxl") as w:
        for nome, df in abas.items():
            df.to_excel(w, sheet_name=nome[:31], index=False)

    # ---------- resumo no console ----------
    pd.set_option("display.width", 220); pd.set_option("display.max_columns", 30)
    for nome, df in abas.items():
        print("\n" + "=" * 20, nome, "=" * 20)
        print(df.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
