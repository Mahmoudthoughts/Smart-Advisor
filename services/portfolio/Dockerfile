FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

COPY services/portfolio/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/portfolio/app ./app

ENV PORTFOLIO_API_PREFIX=/portfolio \
    PORT=8200

EXPOSE 8200

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8200"]
