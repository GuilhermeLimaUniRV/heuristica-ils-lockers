# Heurística ILS para localização de *lockers*: Guloso × GRASP

Código, instâncias e resultados do Trabalho Final de Curso (Engenharia de Software, UniRV):
*Heurística ILS para localização de lockers com função objetivo de soma de frações: impacto da
construção da solução inicial na qualidade e no tempo computacional.*

Autor: Guilherme Marques Lima · Orientador: Prof. Me. Darlan Marques da Silva

## Estrutura

```
src/          código-fonte (Python)
dados/        instâncias de entrada
  instancias/            as 24 instâncias do experimento (JSON)
  instancias_calibracao/ instâncias usadas na calibração do parâmetro α
  referencia/            valores de referência para verificar a reprodução
resultados/   planilhas geradas pelos scripts (Excel)
figuras/      figuras do Capítulo 4
logs/         registros das execuções
```

### Código (`src/`)

| Arquivo | Função |
|---|---|
| `guilherme.py` | ILS do orientador (construção Guloso/GRASP), sem alterações. |
| `milp.py` | Modelo exato (MILP) do orientador, sem alterações. |
| `gerar_instancias.py` | Gerador parametrizado das 24 instâncias. |
| `runner_experimentos.py` | Experimento principal: 24 instâncias × 2 variantes × 30 sementes. |
| `milp_batch.py` | Resolve o MILP nas 24 instâncias e compara com o ILS. |
| `estudos_complementares.py` | Calibração de α e contagem de iterações. |
| `analise_capitulo4.py` | Testes estatísticos e tabelas do Capítulo 4. |
| `analise_estatistica.py`, `comparar_iniciais.py` | Análises preliminares. |
| `figuras_capitulo4.py` | Gera as figuras do Capítulo 4. |
| `verificar_reproducao.py` | Confere se o ambiente reproduz as instâncias e os valores de Z. |

### Resultados (`resultados/`)

`resultados_experimentos.xlsx` (1.440 execuções) · `milp_vs_ils.xlsx` (método exato) ·
`calibracao_parametros.xlsx` · `iteracoes_convergencia.xlsx` · `analise_capitulo4.xlsx` ·
`solucoes_iniciais.xlsx`

## Grade experimental (24 instâncias = 3 × 4 × 2)
- ni (clientes): **50, 90, 180**, com nj = ni/2
- p (lockers): **2, 4, 8, 11**
- α: **0,6 e 0,9**

## Como executar

Os comandos partem da raiz do repositório (Python 3.10; dependências com versões fixas em `requirements.txt`).

```bash
pip install -r requirements.txt
python src/verificar_reproducao.py     # confere o ambiente (rápido)
python src/gerar_instancias.py         # recria as instâncias em dados/instancias
python src/runner_experimentos.py      # experimento principal (várias horas)
python src/runner_experimentos.py smoke  # teste rápido (2 instâncias × 3 sementes)
python src/milp_batch.py               # método exato (limite de 1 h por instância)
python src/estudos_complementares.py
python src/analise_capitulo4.py
python src/figuras_capitulo4.py
```

Os scripts gravam em `resultados/`, `figuras/` e `dados/`: rodar o experimento principal **sobrescreve**
`resultados/resultados_experimentos.xlsx`.

### Docker

```bash
docker build -t tfc-ils .
docker run --rm tfc-ils python src/verificar_reproducao.py   # verificação da reprodução (padrão)
```

## Observação sobre desempenho
O solver recalcula a função objetivo por completo a cada avaliação (sem avaliação incremental). O tempo por execução cresce com `p` e `ni`: o experimento completo leva
algumas horas.
