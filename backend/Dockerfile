FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    GDAL_CONFIG=/usr/bin/gdal-config

WORKDIR /app

# Geospatial runtime/build deps (GDAL, spatial index, PyOsmium/libosmium).
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    curl \
    postgresql-client \
    gdal-bin \
    libgdal-dev \
    libspatialindex-dev \
    libboost-dev \
    libboost-program-options-dev \
    libboost-filesystem-dev \
    libboost-system-dev \
    libboost-iostreams-dev \
    libboost-regex-dev \
    libexpat1-dev \
    zlib1g-dev \
    libbz2-dev \
    liblz4-dev \
    libprotobuf-dev \
    protobuf-compiler \
    libosmium2-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY alembic.ini .
COPY migrations ./migrations
COPY app ./app

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN sed -i 's/\r$//' /docker-entrypoint.sh && chmod +x /docker-entrypoint.sh

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --retries=5 --start-period=30s \
    CMD curl -f http://localhost:8000/ || exit 1

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
