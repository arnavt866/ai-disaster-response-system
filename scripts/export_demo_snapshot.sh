#!/usr/bin/env bash
# Export a PostgreSQL data-only snapshot from the live dev database.
#
# Output: backend/snapshots/demo_snapshot.sql.gz (gzipped plain SQL).
#
# Plain SQL is used rather than pg_dump's custom format on purpose: pg_dump
# always writes the newest custom-format header version and has no flag to
# target an older one, so a dump taken with pg_dump 17/18 cannot be read by the
# older pg_restore shipped in the backend image. Plain SQL is portable text that
# any psql version can replay.
#
# Data only: the Docker entrypoint runs `alembic upgrade head` first, so the
# schema already exists. alembic_version and spatial_ref_sys are excluded --
# migrations stamp the former and the PostGIS extension populates the latter.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT/backend/.env}"
OUTPUT="${OUTPUT:-$ROOT/backend/snapshots/demo_snapshot.sql.gz}"
PG_DUMP_BIN="${PG_DUMP:-pg_dump}"
PSQL_BIN="${PSQL:-psql}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: $ENV_FILE" >&2
  exit 1
fi

DATABASE_URL="$(grep -E '^[[:space:]]*DATABASE_URL[[:space:]]*=' "$ENV_FILE" | tail -n1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
if [[ -z "$DATABASE_URL" ]]; then
  echo "DATABASE_URL not found in $ENV_FILE" >&2
  exit 1
fi

if ! command -v "$PG_DUMP_BIN" >/dev/null 2>&1; then
  echo "pg_dump not found. Install PostgreSQL client tools or set PG_DUMP." >&2
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT")"

export DATABASE_URL

read -r DB_HOST DB_PORT DB_USER DB_PASSWORD DB_NAME <<EOF
$(python - <<PY
import os
from urllib.parse import unquote, urlparse

url = os.environ["DATABASE_URL"].replace("postgresql+psycopg2://", "postgresql://")
parsed = urlparse(url)
print(parsed.hostname or "localhost")
print(parsed.port or 5432)
print(unquote(parsed.username or "postgres"))
print(unquote(parsed.password or ""))
print((parsed.path or "/disaster_db").lstrip("/"))
PY
)
EOF

echo "Exporting data-only snapshot from ${DB_USER}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
echo "Output: $OUTPUT"

export PGPASSWORD="$DB_PASSWORD"
"$PG_DUMP_BIN" \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  --data-only \
  --format=plain \
  --no-owner \
  --no-acl \
  --disable-triggers \
  --exclude-table=alembic_version \
  --exclude-table=spatial_ref_sys \
  --verbose \
  | gzip -9 >"$OUTPUT"

size_bytes=$(wc -c <"$OUTPUT" | tr -d ' ')
size_mb=$(python - <<PY
print(f"{int('$size_bytes') / (1024 * 1024):.2f}")
PY
)
echo "Snapshot complete: ${size_mb} MB (${size_bytes} bytes)"

echo "Row-count spot check (live source DB):"
"$PSQL_BIN" -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -At -F '|' -c "
SELECT 'disaster_zones' AS table_name, COUNT(*)::bigint AS row_count FROM disaster_zones
UNION ALL SELECT 'buildings', COUNT(*)::bigint FROM buildings
UNION ALL SELECT 'relief_centers', COUNT(*)::bigint FROM relief_centers
UNION ALL SELECT 'disaster_events', COUNT(*)::bigint FROM disaster_events
UNION ALL SELECT 'ndma_alerts', COUNT(*)::bigint FROM ndma_alerts
UNION ALL SELECT 'satellite_assessments', COUNT(*)::bigint FROM satellite_assessments
UNION ALL SELECT 'allocation_records', COUNT(*)::bigint FROM allocation_records
ORDER BY table_name;
"

echo "Restore path for Docker: mount $OUTPUT at /app/snapshots/demo_snapshot.sql.gz"
