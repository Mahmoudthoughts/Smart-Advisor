FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY services/ibkr_service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/ibkr_service ./ibkr_service

CMD ["uvicorn", "ibkr_service.main:app", "--host", "0.0.0.0", "--port", "8110", "--loop", "asyncio"]
