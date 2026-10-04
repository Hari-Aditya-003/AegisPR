FROM nvidia/cuda:12.8.1-runtime-ubuntu24.04
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-pip ca-certificates && rm -rf /var/lib/apt/lists/*
RUN useradd --system --uid 10001 --create-home aegis
WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt
COPY app ./app
USER aegis
EXPOSE 8091
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8091/health')"
CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8091"]
