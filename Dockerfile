FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OKF_BUNDLE=okf

WORKDIR /app

COPY pyproject.toml README.md SPEC.md ./
COPY okf_mcp ./okf_mcp
COPY okf ./okf

RUN pip install --no-cache-dir . \
    && mkdir -p artifacts/rag \
    && cp okf_mcp/rag/.env.example okf_mcp/rag/.env

EXPOSE 8000

CMD ["python", "-m", "okf_mcp", "server", "--bundle", "okf", "--transport", "http", "--host", "0.0.0.0", "--port", "8000"]
