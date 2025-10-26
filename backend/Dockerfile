FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Copy project metadata and source
COPY pyproject.toml ./
COPY smart_advisor ./smart_advisor

# Install dependencies (including optional test extras for tooling)
RUN pip install --upgrade pip \
    && pip install .[test]

# Copy service source and assets
COPY app ./app
COPY scripts ./scripts
COPY sql ./sql

EXPOSE 8000

# Run the FastAPI application defined in backend/app/main.py
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
