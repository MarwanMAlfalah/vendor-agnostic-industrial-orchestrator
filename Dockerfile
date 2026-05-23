FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY app ./app

RUN python -m pip install --upgrade pip \
    && python -m pip install -e .

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
