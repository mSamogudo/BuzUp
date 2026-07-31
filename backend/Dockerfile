FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY entrypoint.sh /usr/local/bin/backend-entrypoint
RUN chmod +x /usr/local/bin/backend-entrypoint

COPY . .

ENTRYPOINT ["backend-entrypoint"]
# Recurso: o compose passa o seu proprio `command:` com os valores afinados
# por ambiente. Isto so corre se alguem subir a imagem sem esse override — e
# os defaults do gunicorn (1 worker, timeout 30s, sem reciclagem) davam um
# processo que bloqueia num pagamento lento e cresce em memoria sem limite.
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "2", \
     "--threads", "4", \
     "--max-requests", "800", \
     "--max-requests-jitter", "100", \
     "--timeout", "120"]