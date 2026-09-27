# Experimentos — ILS Guloso vs GRASP (localização de lockers)

## Arquivos

| Arquivo | O que é |
|---|---|
| `gerador.txt` | Gerador **original** do orientador (uma instância por execução). Não alterado. |
| `guilherme.py` | Solver **original** do orientador (ILS Guloso/GRASP). Não alterado. |
| `milp.py` | Solver exato (MILP) do orientador, para referência do ótimo. |
| `gerar_instancias.py` | Gerador **parametrizado** — produz as 24 instâncias do experimento. |
| `runner_experimentos.py` | Executa Guloso + GRASP (30 repetições) e exporta o Excel. |
| `instancias/` | As 24 instâncias `.json` geradas. |
| `resultados_experimentos.xlsx` | Saída com os resultados. |
| `DIFERENCAS_TFC.md` | Diferenças entre o código/execução e o texto do TFC 1. |
| `Dockerfile`, `requirements.txt` | Ambiente reprodutível (Python 3.10). |

## Grade experimental (24 instâncias = 3 × 4 × 2)
- ni (clientes): **50, 90, 180**  → nj = ni/2
- p (lockers): **2, 4, 8, 11**
- alpha: **0,6 e 0,9**

## Como rodar (local)
```bash
python gerar_instancias.py        # cria as 24 instâncias em ./instancias
python runner_experimentos.py     # roda tudo (24 × 2 variantes × 30 sementes)
python runner_experimentos.py smoke   # teste rápido (2 instâncias × 3 sementes)
```

## Como rodar (Docker)
```bash
docker build -t tfc-ils .
# monta a pasta atual para receber o Excel de resultados de volta:
docker run --rm -v "${PWD}:/app" tfc-ils
```

## Observação sobre desempenho
O tempo por execução cresce com `p` e `ni` (o solver recalcula a função objetivo
por completo a cada avaliação, sem avaliação incremental — ver `DIFERENCAS_TFC.md`).
Referências medidas: ni=50 ~0,1 s; ni=90/p=11 ~9 s; ni=180/p=8 ~21 s; ni=180/p=11 dezenas de s.
O experimento completo é uma tarefa de **algumas horas** — recomendado rodar na
máquina final (via Docker).
