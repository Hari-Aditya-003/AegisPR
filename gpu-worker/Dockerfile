FROM nvidia/cuda:12.8.1-devel-ubuntu24.04
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 CUPY_CACHE_DIR=/tmp/cupy-cache
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv ca-certificates && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
RUN useradd --system --uid 10001 --create-home aegis
WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir --upgrade pip==26.2.1 \
    && pip3 install --no-cache-dir -r requirements.txt
COPY app ./app
USER aegis
EXPOSE 8091
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8091/health')"
CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8091"]
