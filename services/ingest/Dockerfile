FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY services/ingest/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services ./services
COPY backend/app ./app

ENV PYTHONPATH=/app

CMD ["uvicorn", "services.ingest.main:app", "--host", "0.0.0.0", "--port", "8100"]
