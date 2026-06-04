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
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]