# Diferenças entre o CÓDIGO/EXECUÇÃO e o texto do TFC 1

Este arquivo registra os pontos em que a implementação real (código do orientador +
execução) diverge do que está escrito na monografia do TFC 1. Serve de checklist para
alinhar o texto no TFC 2 (ou confirmar cada ponto com o orientador).

Decisão adotada: **seguir o código do orientador**. Portanto, onde há divergência,
é o **texto** que deve ser ajustado no TFC 2 para refletir o que o código faz.

---

## 1. Geração de instâncias (Seção 3.5)

| Texto do TFC 1 diz | O código realmente faz | Ação sugerida |
|---|---|---|
| Bibliotecas **NumPy e Pandas** | Usa **NumPy e SciPy** (Pandas só no runner de resultados) | Ajustar texto |
| Atributos de utilidade por **distribuição normal truncada** | Utilidade determinística: `u = -alpha * dist` (Logit/Huff) | Ajustar texto (remover normal truncada) |
| Coordenadas em **grid urbano ou retângulo** | Apenas sorteio aleatório em retângulo 1000×1000 | Ajustar texto |
| Distâncias **euclidiana ou Manhattan** | Apenas **euclidiana** | Ajustar texto |
| Instâncias salvas em **CSV** | Salvas em **JSON** | Ajustar texto |
| `b_ij` = "distância ou custo de acesso" | `b_ij = d * theta` (demanda × disposição). Interpretável como "termo de acesso" | Aceito como está (leitura ampla) |
| Função de nível de serviço `s` (degraus) | Presente no código, não mencionada no texto | Opcional: mencionar no texto |

## 2. Desenho experimental (Seção 3.6)

| Texto do TFC 1 diz | O código/plano real faz | Ação sugerida |
|---|---|---|
| Dois **padrões de disposição (uniforme e agrupado)** | Não há padrão agrupado; varia-se **p** e **alpha** | Ajustar texto (trocar "padrões" por "variação de p e alpha") |
| — | Grade: 3 ni × 4 p × 2 alpha = **24 instâncias** | Descrever no texto |

## 3. Busca local (Seções 2.6 e 3.4)

| Texto do TFC 1 diz | O código realmente faz | Ação sugerida |
|---|---|---|
| Seleciona o par (j, j') que **maximiza ΔZ** (best-improvement) | **first-improvement**: aceita a primeira troca que melhora | Ajustar texto para "first-improvement" |
| Avaliação **incremental** de ΔZ | Recalcula a função objetivo **por completo** a cada avaliação | Ajustar texto (não há avaliação incremental) |

## 4. Ambiente de execução (Seção 3.6)

| Texto do TFC 1 diz | Situação real | Ação sugerida |
|---|---|---|
| **Python 3.10** | Adotado no Docker (imagem python:3.10-slim) | OK — garantido pelo Docker |
| **Docker** para isolamento | Dockerfile criado; será usado | OK |
| **Intel Xeon Gold 6230, 32 GB RAM** | Máquina final a definir | Declarar a máquina real usada |
| **Linux Ubuntu 20.04** | Garantido pela imagem Docker (base Debian/Linux) | Confirmar/ajustar versão no texto |
| **Limite de 1 hora de CPU** por execução | Implementado no runner (SIGALRM, só em Linux/Docker) | OK — ativo no Docker |

## 5. Métrica de tempo

| Texto do TFC 1 diz | O código realmente faz | Ação sugerida |
|---|---|---|
| "tempo de **CPU** (s)" | Mede **tempo de parede** (`time.perf_counter`), como no código do orientador | Verificar com orientador; se necessário, trocar por `time.process_time` |

---

## Resumo do que precisa de AÇÃO NO CÓDIGO (não só no texto)
- Nada obrigatório: o código do orientador está sendo seguido como está.
- O limite de 1 h já está implementado no runner.

## Resumo do que precisa de AJUSTE NO TEXTO do TFC 2
- Seção 3.5: normal truncada, Pandas→SciPy, CSV→JSON, euclidiana/Manhattan→euclidiana, grid.
- Seção 3.6: uniforme/agrupado → variação de p e alpha; descrever as 24 instâncias; máquina real.
- Seções 2.6/3.4: best-improvement → first-improvement; remover "avaliação incremental".
