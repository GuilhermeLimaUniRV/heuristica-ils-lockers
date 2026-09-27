# Ambiente reprodutível para os experimentos do TFC (Python 3.10).
# Conforme a metodologia (Seção 3.6), o isolamento de ambiente é feito via Docker,
# garantindo consistência de bibliotecas e versões entre execuções.

FROM python:3.10-slim

WORKDIR /app

# instala as dependências primeiro (aproveita cache de camada)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copia o código (gerador, solver e runner)
COPY . .

# por padrão: gera as instâncias e executa todo o experimento.
# O Excel de resultados é escrito em /app/resultados_experimentos.xlsx.
CMD ["sh", "-c", "python gerar_instancias.py && python runner_experimentos.py"]
