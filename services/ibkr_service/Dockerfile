FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY services/ibkr_service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/ibkr_service ./ibkr_service

CMD ["uvicorn", "ibkr_service.main:app", "--host", "0.0.0.0", "--port", "8110", "--loop", "asyncio"]
