FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim AS runner
RUN useradd --system --uid 10001 --create-home aegis
WORKDIR /app
COPY --from=builder /install /usr/local
COPY app ./app
RUN mkdir -p /app/data /tmp/aegispr-runs && chown -R aegis:aegis /app/data /tmp/aegispr-runs
USER aegis
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

