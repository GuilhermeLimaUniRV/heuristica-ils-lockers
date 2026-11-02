#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Figuras do Capítulo 4 (salvas em figuras/cap4_*.png, 300 dpi).

Paleta categórica validada (seguro para daltonismo, todos os pares):
  ILS-Guloso = azul #2a78d6 | ILS-GRASP = laranja #eb6834 | MILP = aqua #1baf7a
Porte (ordinal): rampa de cinza #a8a6a0 -> #6f6d68 -> #2e2d2a + formato de marcador.
"""

import os
import shutil

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import numpy as np
import pandas as pd
from scipy import stats

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # raiz do repositório
RES = os.path.join(RAIZ, "resultados")
FIG = os.path.join(RAIZ, "figuras")
os.makedirs(FIG, exist_ok=True)

GUL, GRA, MIL = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, MUTED, GRID, AXIS = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
PORTE = {50: "Pequeno", 90: "Médio", 180: "Grande"}
P_COR = {"Pequeno": "#a8a6a0", "Médio": "#6f6d68", "Grande": "#2e2d2a"}
P_MARC = {"Pequeno": "o", "Médio": "s", "Grande": "^"}
W = 6.3  # largura útil da página (pol)

plt.rcParams.update({
    # Arial no ambiente de redação (Windows); Liberation Sans (métrica-compatível)
    # no contêiner Docker/Linux; DejaVu Sans como último recurso.
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Liberation Sans", "DejaVu Sans"],
    "font.size": 8.5, "axes.titlesize": 9, "axes.labelsize": 8.5,
    "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "legend.fontsize": 7.5,
    "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.titlecolor": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "grid.linestyle": "-", "axes.axisbelow": True, "axes.spines.top": False,
    "axes.spines.right": False, "savefig.dpi": 300, "savefig.bbox": "tight",
    "savefig.facecolor": "white", "legend.frameon": False,
})


def _salva(fig, nome):
    caminho = os.path.join(FIG, nome)
    fig.savefig(caminho)
    plt.close(fig)
    print("figura:", caminho)


def _ic(x):
    x = np.asarray(x, float)
    m = x.mean()
    h = stats.t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / np.sqrt(len(x)) if len(x) > 1 else 0
    return m, h


def _virgula(ax, eixos="xy"):
    """Rótulos numéricos com vírgula decimal (padrão pt-BR), inclusive em escala log."""
    from matplotlib.ticker import FuncFormatter
    fmt = FuncFormatter(lambda v, _: f"{v:g}".replace(".", ","))
    if "x" in eixos:
        ax.xaxis.set_major_formatter(fmt)
    if "y" in eixos:
        ax.yaxis.set_major_formatter(fmt)


def carrega():
    br = pd.read_excel(os.path.join(RES, "resultados_experimentos.xlsx"), sheet_name="Bruto")
    br["Porte"] = br["ni"].map(PORTE)
    return br


# ---------------- dispersão pareada (inicial, final, tempo) ----------------
def fig_dispersao(br):
    fig, axs = plt.subplots(1, 3, figsize=(W, 2.45))
    cfg = [("Zini_Guloso", "Zini_GRASP", "(a) Função objetivo inicial", False),
           ("Zfin_Guloso", "Zfin_GRASP", "(b) Função objetivo final", False),
           ("Tempo_Guloso", "Tempo_GRASP", "(c) Tempo de execução (s)", True)]
    for ax, (cx, cy, tit, log) in zip(axs, cfg):
        for porte in ["Pequeno", "Médio", "Grande"]:
            s = br[br.Porte == porte]
            ax.scatter(s[cx], s[cy], s=11, marker=P_MARC[porte], color=P_COR[porte],
                       edgecolors="white", linewidths=0.35, alpha=0.9, zorder=3)
        lo = min(br[cx].min(), br[cy].min()); hi = max(br[cx].max(), br[cy].max())
        if log:
            ax.set_xscale("log"); ax.set_yscale("log")
            lo, hi = lo * 0.8, hi * 1.25
        else:
            lo, hi = 0, hi * 1.06
        ax.plot([lo, hi], [lo, hi], color=MUTED, lw=0.8, zorder=2)
        ax.set_xlim(lo, hi); ax.set_ylim(lo, hi); ax.set_aspect("equal", adjustable="box")
        _virgula(ax)
        ax.set_title(tit, loc="left"); ax.set_xlabel("ILS-Guloso"); ax.set_ylabel("ILS-GRASP")
    axs[0].text(0.04, 0.95, "acima da diagonal:\nGRASP melhor", transform=axs[0].transAxes,
                va="top", fontsize=6.8, color=INK2)
    axs[1].text(0.04, 0.95, "717 de 720 pares\nsobre a diagonal", transform=axs[1].transAxes,
                va="top", fontsize=6.8, color=INK2)
    leg = [Line2D([], [], marker=P_MARC[p], color="none", markerfacecolor=P_COR[p],
                  markeredgecolor="white", markersize=6, label=f"{p} ({n}×{n//2})")
           for p, n in (("Pequeno", 50), ("Médio", 90), ("Grande", 180))]
    fig.legend(handles=leg, loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.06))
    fig.tight_layout(w_pad=1.2)
    _salva(fig, "cap4_dispersao.png")


# ---------------- qualidade inicial relativa à final, por porte ----------------
def fig_inicial_relativa(br):
    fig, ax = plt.subplots(figsize=(W * 0.72, 2.4))
    portes = ["Pequeno", "Médio", "Grande"]
    x = np.arange(3); w = 0.27
    for k, (var, cor) in enumerate((("Guloso", GUL), ("GRASP", GRA))):
        med, err = [], []
        for p in portes:
            s = br[br.Porte == p]
            m, h = _ic(100 * s[f"Zini_{var}"] / s[f"Zfin_{var}"])
            med.append(m); err.append(h)
        ax.bar(x + (k - 0.5) * w, med, w, color=cor, edgecolor="white", linewidth=1.5,
               label=f"ILS-{var}", zorder=3)
        ax.errorbar(x + (k - 0.5) * w, med, yerr=err, fmt="none", ecolor=INK, elinewidth=0.8,
                    capsize=2.5, zorder=4)
    ax.axhline(100, color=MUTED, lw=0.8, zorder=2)
    ax.text(2.45, 102, "solução final = 100%", va="bottom", ha="right", fontsize=6.8, color=INK2)
    ax.set_xticks(x); ax.set_xticklabels(["Pequeno (50×25)", "Médio (90×45)", "Grande (180×90)"])
    ax.set_ylim(0, 112); ax.set_xlim(-0.55, 2.55); ax.grid(axis="x", visible=False)
    ax.set_ylabel("Solução inicial (% da final)")
    ax.legend(loc="upper center", ncol=2, bbox_to_anchor=(0.45, 1.16))
    fig.tight_layout()
    _salva(fig, "cap4_inicial_relativa.png")


# ---------------- validação com o MILP ----------------
def fig_milp(br):
    mv = pd.read_excel(os.path.join(RES, "milp_vs_ils.xlsx"))
    t = br.groupby("Instancia").agg(TG=("Tempo_Guloso", "mean"), TR=("Tempo_GRASP", "mean"),
                                    ZG=("Zfin_Guloso", "max"), ZR=("Zfin_GRASP", "max")).reset_index()
    d = mv.merge(t, on="Instancia").sort_values(["ni", "p", "alpha"]).reset_index(drop=True)
    d["BKS"] = d[["MILP_Z", "ZG", "ZR"]].max(axis=1)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(W, 2.9), gridspec_kw={"width_ratios": [1.65, 1]})
    x = np.arange(1, len(d) + 1)
    prov = d.Provou_otimo.values.astype(bool)
    a1.scatter(x[prov], d.MILP_tempo_s[prov], s=22, color=MIL, edgecolors="white", lw=0.4,
               zorder=4, label="MILP (ótimo provado)")
    a1.scatter(x[~prov], d.MILP_tempo_s[~prov], s=22, facecolors="white", edgecolors=MIL, lw=1.2,
               zorder=4, label="MILP (limite de tempo)")
    a1.scatter(x - 0.18, d.TG, s=14, marker="o", color=GUL, edgecolors="white", lw=0.3, zorder=3,
               label="ILS-Guloso")
    a1.scatter(x + 0.18, d.TR, s=14, marker="D", color=GRA, edgecolors="white", lw=0.3, zorder=3,
               label="ILS-GRASP")
    a1.axhline(3600, color=MUTED, lw=0.8, zorder=2)
    a1.text(0.6, 3600 * 1.35, "limite do MILP (1 h)", fontsize=6.6, color=INK2)
    a1.set_yscale("log"); a1.set_ylim(0.05, 3e4); a1.set_xlim(0.3, 24.7)
    a1.grid(axis="x", visible=False)
    for xv in (8.5, 16.5):
        a1.axvline(xv, color=AXIS, lw=0.7, zorder=1)
    for xc, lab in ((4.5, "Pequeno"), (12.5, "Médio"), (20.5, "Grande")):
        a1.text(xc, -0.11, lab, ha="center", va="top", fontsize=7.2, color=INK2,
                transform=a1.get_xaxis_transform())
    a1.set_xticks(x); a1.set_xticklabels([str(int(p)) for p in d.p], fontsize=6.5)
    a1.set_xlabel("Instâncias ordenadas por porte e p (rótulo = p)", labelpad=14)
    a1.set_ylabel("Tempo (s, escala log)")
    a1.set_title("(a) Tempo por instância", loc="left")
    _virgula(a1, "y")
    h1, l1 = a1.get_legend_handles_labels()
    fig.legend(h1, l1, loc="lower center", ncol=4, fontsize=6.8, bbox_to_anchor=(0.5, -0.07))
    # (b) desvantagem do MILP nas 8 instâncias sem certificado
    nc = d[~prov].copy()
    nc["gap"] = 100 * (nc.BKS - nc.MILP_Z) / nc.BKS
    nc["rot"] = [f"{int(a)}×{int(a) // 2}, p={int(c)}, α={str(e).replace('.', ',')}"
                 for a, c, e in zip(nc.ni, nc.p, nc.alpha)]
    y = np.arange(len(nc))[::-1]
    a2.barh(y, nc.gap, color=MIL, edgecolor="white", linewidth=1.5, height=0.62, zorder=3)
    for yy, g in zip(y, nc.gap):
        a2.text(g + 0.08, yy, f"{g:.2f}%".replace(".", ","), va="center", fontsize=6.6, color=INK2)
    a2.set_yticks(y); a2.set_yticklabels(nc.rot, fontsize=6.6)
    a2.set_xlim(0, 5.2); a2.grid(axis="y", visible=False)
    a2.set_xlabel("Distância do MILP à melhor solução (%)")
    a2.set_title("(b) Instâncias sem prova de otimalidade", loc="left")
    fig.tight_layout(w_pad=1.0)
    _salva(fig, "cap4_milp.png")


# ---------------- tempo por p, em cada porte (pequenos múltiplos) ----------------
def fig_tempo(br):
    fig, axs = plt.subplots(1, 3, figsize=(W, 2.35))
    for ax, (porte, n) in zip(axs, (("Pequeno", 50), ("Médio", 90), ("Grande", 180))):
        s = br[br.Porte == porte]
        ps = sorted(s.p.unique())
        # mesmo x para as duas variantes: a sobreposição é a própria mensagem
        for var, cor, mk, lw, ms, z in (("Guloso", GUL, "o", 2.6, 5.5, 3),
                                        ("GRASP", GRA, "D", 1.3, 3.6, 4)):
            med, err = zip(*[_ic(s[s.p == p][f"Tempo_{var}"]) for p in ps])
            xs = np.arange(len(ps))
            ax.errorbar(xs, med, yerr=err, color=cor, marker=mk, markersize=ms, lw=lw,
                        elinewidth=0.8, capsize=2.2, markeredgecolor="white", markeredgewidth=0.4,
                        label=f"ILS-{var}", zorder=z)
        ax.set_xticks(range(len(ps))); ax.set_xticklabels([str(p) for p in ps])
        ax.set_xlabel("p (armários)"); ax.set_title(f"{porte} ({n}×{n//2})", loc="left")
        ax.set_ylim(bottom=0); ax.grid(axis="x", visible=False); _virgula(ax, "y")
    axs[0].set_ylabel("Tempo médio (s)")
    h, l = axs[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.07))
    fig.tight_layout(w_pad=1.4)
    _salva(fig, "cap4_tempo.png")


# ---------------- resultado dos testes por instância (mapa) ----------------
def fig_testes_instancia():
    pi = pd.read_excel(os.path.join(RES, "analise_capitulo4.xlsx"), sheet_name="T_testes_instancia")
    pi = pi.sort_values(["ni", "p", "alpha"])
    inst = pi.drop_duplicates("Instancia")[["Instancia", "ni", "p", "alpha"]].reset_index(drop=True)
    inst["nj"] = inst["ni"] // 2
    mets = ["Zini", "Zfin", "Tempo"]
    cor = {"GRASP": GRA, "Guloso": GUL, "—": "#f0efec"}
    txt = {"GRASP": "GRASP", "Guloso": "Guloso", "—": "n.s."}
    fig, ax = plt.subplots(figsize=(3.9, 6.0))
    for i, r in inst.iterrows():
        for j, m in enumerate(mets):
            fav = pi[(pi.Instancia == r.Instancia) & (pi.Metrica == m)].Favorece.iloc[0]
            ax.add_patch(plt.Rectangle((j, i), 1, 1, facecolor=cor[fav], edgecolor="white", lw=1.5))
            ax.text(j + 0.5, i + 0.5, txt[fav], ha="center", va="center", fontsize=6.4,
                    color="white" if fav != "—" else INK2)
    ax.set_xlim(0, 3); ax.set_ylim(len(inst), 0)
    ax.set_xticks([0.5, 1.5, 2.5]); ax.set_xticklabels(["Z inicial", "Z final", "Tempo"])
    ax.xaxis.tick_top()
    ax.set_yticks(np.arange(len(inst)) + 0.5)
    ax.set_yticklabels([f"{int(a)}×{int(b)}, p={int(c)}, α={str(e).replace('.', ',')}"
                        for a, b, c, e in zip(inst.ni, inst.nj, inst.p, inst.alpha)], fontsize=6.6)
    ax.grid(False); ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    for yv in (8, 16):
        ax.axhline(yv, color=INK2, lw=0.9)
    leg = [Patch(facecolor=GRA, label="GRASP significativamente melhor"),
           Patch(facecolor=GUL, label="Guloso significativamente melhor"),
           Patch(facecolor="#f0efec", label="sem diferença significativa (n.s.)")]
    ax.legend(handles=leg, loc="upper center", bbox_to_anchor=(0.42, -0.01), ncol=1, fontsize=6.6)
    fig.tight_layout()
    _salva(fig, "cap4_testes_instancia.png")


# ---------------- calibração (2 x 3 pequenos múltiplos) ----------------
def fig_calibracao():
    arq = os.path.join(RES, "calibracao_parametros.xlsx")
    if not os.path.exists(arq):
        print("calibração ainda não disponível"); return
    c = pd.read_excel(arq, sheet_name="Bruto")
    bks = c.groupby("Instancia").Z_final.max()
    c["no_bks"] = (np.abs(c.Z_final - c.Instancia.map(bks)) / c.Instancia.map(bks)) < 1e-4
    fatores = [("NI", "Iterações sem melhora (NI)", [25, 50, 100, 200],
                lambda d, v: d[(d.k == 1) & (d.GRASP_alpha == 0.8) & (d.NI == v)]),
               ("k", "Intensidade da perturbação (k)", [1, 2, 3],
                lambda d, v: d[(d.NI == 100) & (d.GRASP_alpha == 0.8) & (d.k == v)]),
               ("a", "α da LRC do GRASP", [0.5, 0.65, 0.8, 0.95],
                lambda d, v: d[(d.NI == 100) & (d.k == 1) & (d.GRASP_alpha == v)])]
    fig, axs = plt.subplots(2, 3, figsize=(W, 3.9), sharey="row")
    for col, (nome, rot, vals, filt) in enumerate(fatores):
        for var, cor, mk in (("ILS-Guloso", GUL, "o"), ("ILS-GRASP", GRA, "D")):
            if nome == "a" and var == "ILS-Guloso":
                continue
            q, e = [], []
            for v in vals:
                s = filt(c, v); s = s[s.Variante == var]
                q.append(100 * s.no_bks.mean()); e.append(s.Aval_total.mean() / 1e3)
            xs = np.arange(len(vals))
            axs[0, col].plot(xs, q, color=cor, marker=mk, lw=1.6, markersize=4.5,
                             markeredgecolor="white", markeredgewidth=0.4, label=var)
            axs[1, col].plot(xs, e, color=cor, marker=mk, lw=1.6, markersize=4.5,
                             markeredgecolor="white", markeredgewidth=0.4, label=var)
        for r in (0, 1):
            axs[r, col].set_xticks(np.arange(len(vals)))
            axs[r, col].set_xticklabels([str(v).replace(".", ",") for v in vals])
            ref = {"NI": 2, "k": 0, "a": 2}[nome]
            axs[r, col].axvspan(ref - 0.18, ref + 0.18, color=GRID, zorder=0)
        axs[1, col].set_xlabel(rot)
    axs[0, 0].set_ylabel("Execuções na melhor\nsolução conhecida (%)")
    axs[1, 0].set_ylabel("Avaliações da função\nobjetivo (×10³)")
    axs[0, 0].set_ylim(0, 105)
    axs[0, 0].set_title("(a) Critério de parada", loc="left")
    axs[0, 1].set_title("(b) Perturbação", loc="left")
    axs[0, 2].set_title("(c) Construção GRASP", loc="left")
    h, l = axs[0, 0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.04))
    fig.text(0.99, -0.03, "faixa cinza = configuração de referência", ha="right", fontsize=6.6,
             color=INK2)
    fig.tight_layout(h_pad=1.0, w_pad=1.0)
    _salva(fig, "cap4_calibracao.png")


# ---------------- iterações: onde o esforço é gasto ----------------
def fig_iteracoes():
    arq = os.path.join(RES, "iteracoes_convergencia.xlsx")
    if not os.path.exists(arq):
        print("iterações ainda não disponíveis"); return
    it = pd.read_excel(arq, sheet_name="Bruto")
    it["Porte"] = it.ni.map(PORTE)
    fig, ax = plt.subplots(figsize=(W * 0.78, 2.5))
    grupos, ate, conf = [], [], []
    for porte in ["Pequeno", "Médio", "Grande"]:
        for var in ("ILS-Guloso", "ILS-GRASP"):
            s = it[(it.Porte == porte) & (it.Variante == var)]
            a = 100 * (s.Aval_ate_melhor / s.Aval_total).mean()
            grupos.append((porte, var)); ate.append(a); conf.append(100 - a)
    y = np.arange(len(grupos))[::-1]
    cores = [GUL if v == "ILS-Guloso" else GRA for _, v in grupos]
    ax.barh(y, ate, color=cores, edgecolor="white", linewidth=1.5, height=0.66, zorder=3)
    ax.barh(y, conf, left=ate, color="#d9d8d2", edgecolor="white", linewidth=1.5, height=0.66,
            zorder=3)
    for yy, a in zip(y, ate):
        ax.text(a + 1, yy, f"{a:.0f}%", va="center", fontsize=6.8, color=INK)
    ax.set_yticks(y); ax.set_yticklabels([f"{p} — {v}" for p, v in grupos], fontsize=7)
    ax.set_xlim(0, 100); ax.grid(False)
    ax.set_xlabel("Esforço computacional (% das avaliações da função objetivo)")
    leg = [Patch(facecolor=GUL, label="até encontrar a melhor solução (ILS-Guloso)"),
           Patch(facecolor=GRA, label="até encontrar a melhor solução (ILS-GRASP)"),
           Patch(facecolor="#d9d8d2", label="confirmação (iterações sem melhora até a parada)")]
    ax.legend(handles=leg, loc="upper center", bbox_to_anchor=(0.45, -0.27), ncol=1, fontsize=6.8)
    fig.tight_layout()
    _salva(fig, "cap4_iteracoes.png")


def fig_mapa(br):
    """Instância grande (180 × 90, p = 11, α = 0,6) e melhor solução encontrada."""
    import json
    nome = "ni-180-nj-90-p-11-alpha-0.6.json"
    with open(os.path.join(RAIZ, "dados", "instancias", nome), encoding="utf-8") as fh:
        inst = json.load(fh)
    cli, cand = np.array(inst["cxyi"]), np.array(inst["cxyj"])
    s = br[br.Instancia == nome]
    melhor = s.loc[s.Zfin_Guloso.idxmax()]
    abertos = [int(x) for x in str(melhor.Locais_Guloso).split()]
    fig, ax = plt.subplots(figsize=(4.3, 4.6))
    ax.scatter(cli[:, 0], cli[:, 1], s=7, color=P_COR["Pequeno"], linewidths=0, zorder=2,
               label="Clientes (n = 180)")
    ax.scatter(cand[:, 0], cand[:, 1], s=26, facecolors="white", edgecolors=P_COR["Médio"], lw=0.9,
               zorder=3, label="Locais candidatos (m = 90)")
    ax.scatter(cand[abertos, 0], cand[abertos, 1], s=130, marker="*", color=INK, edgecolors="white",
               lw=0.6, zorder=4,
               label=f"Armários instalados (p = 11; Z = {melhor.Zfin_Guloso:.2f})".replace(".", ","))
    ax.set_xlim(0, 1000); ax.set_ylim(0, 1000); ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
    for sp in ax.spines.values():
        sp.set_visible(True); sp.set_color(AXIS); sp.set_linewidth(0.8)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.02), ncol=1, fontsize=7.2)
    fig.tight_layout()
    _salva(fig, "cap4_mapa_solucao.png")


def main():
    br = carrega()
    fig_mapa(br)
    fig_dispersao(br)
    fig_inicial_relativa(br)
    fig_milp(br)
    fig_tempo(br)
    fig_testes_instancia()
    fig_calibracao()
    fig_iteracoes()


if __name__ == "__main__":
    main()
