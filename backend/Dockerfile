FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY pyproject.toml ./
COPY smart_advisor ./smart_advisor

RUN pip install --upgrade pip \
    && pip install .[test]

EXPOSE 8000

CMD ["uvicorn", "smart_advisor.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
