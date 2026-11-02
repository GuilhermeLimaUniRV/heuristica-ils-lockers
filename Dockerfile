# Ambiente reprodutível para os experimentos do TFC (Python 3.10).
# Conforme a metodologia (Seção 3.6), o isolamento de ambiente é feito via Docker,
# garantindo consistência de bibliotecas, versões e condições de sistema.

FROM python:3.10-slim

WORKDIR /app

# Liberation Sans: fonte métrica-compatível com Arial, para as figuras saírem
# visualmente idênticas às geradas no ambiente de redação.
RUN apt-get update && apt-get install -y --no-install-recommends fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# dependências primeiro (aproveita o cache de camada do Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# código, instâncias, scripts e a referência de reprodutibilidade
COPY . .

# Por padrão, verifica a reprodutibilidade (instâncias e valores de Z). Para rodar
# uma etapa: docker run --rm -v "$PWD:/app" tfc-ils python src/<script>.py
CMD ["python", "src/verificar_reproducao.py"]
