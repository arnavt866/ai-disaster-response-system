#!/bin/sh
set -e

echo "Waiting for PostgreSQL..."
python <<'PY'
import os
import sys
import time

from sqlalchemy import create_engine, text

url = os.environ.get("DATABASE_URL")
if not url:
    sys.exit("DATABASE_URL is not set")

for attempt in range(60):
    try:
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("Database is ready.")
        break
    except Exception as exc:
        print(f"  attempt {attempt + 1}/60: {exc}")
        time.sleep(2)
else:
    sys.exit("Database did not become ready in time")
PY

echo "Running Alembic migrations (alembic upgrade head)..."
alembic upgrade head

echo "Checking for demo snapshot restore..."
python <<'PY'
import gzip
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import unquote, urlparse

from sqlalchemy import create_engine, text

database_url = os.environ.get("DATABASE_URL")
if not database_url:
    sys.exit("DATABASE_URL is not set")

SNAPSHOT_DIR = Path(os.environ.get("DEMO_SNAPSHOT_DIR", "/app/snapshots"))

# Gzipped plain SQL is preferred: pg_dump's custom format embeds a header
# version that only an equal-or-newer pg_restore can read, so a dump taken with
# a newer pg_dump than this image's client is unreadable. Plain SQL replays on
# any psql. The .dump entry is kept so existing custom-format snapshots still
# work when the client versions happen to line up.
SNAPSHOT_CANDIDATES = (
    "demo_snapshot.sql.gz",
    "demo_snapshot.sql",
    "demo_snapshot.dump",
)

override = os.environ.get("DEMO_SNAPSHOT_PATH")
if override:
    snapshot_path = Path(override)
else:
    snapshot_path = next(
        (p for p in (SNAPSHOT_DIR / n for n in SNAPSHOT_CANDIDATES) if p.is_file()),
        SNAPSHOT_DIR / SNAPSHOT_CANDIDATES[0],
    )

if not snapshot_path.is_file():
    print(
        f"No demo snapshot found in {SNAPSHOT_DIR} "
        f"(looked for {', '.join(SNAPSHOT_CANDIDATES)}); "
        "continuing with migrated empty schema."
    )
    sys.exit(0)

engine = create_engine(database_url, pool_pre_ping=True)
with engine.connect() as conn:
    zones = conn.execute(text("SELECT COUNT(*) FROM disaster_zones")).scalar_one()
    buildings = conn.execute(text("SELECT COUNT(*) FROM buildings")).scalar_one()
    depots = conn.execute(text("SELECT COUNT(*) FROM relief_centers")).scalar_one()

if zones or buildings or depots:
    print(
        "Database already contains application data "
        f"(zones={zones}, buildings={buildings}, depots={depots}); skipping snapshot restore."
    )
    sys.exit(0)

print(f"Database is empty after migrations; restoring data from {snapshot_path} ...")

parsed = urlparse(database_url.replace("postgresql+psycopg2://", "postgresql://"))
host = parsed.hostname or "db"
port = str(parsed.port or 5432)
user = unquote(parsed.username or "postgres")
password = unquote(parsed.password or "")
dbname = (parsed.path or "/disaster_db").lstrip("/")

env = os.environ.copy()
env["PGPASSWORD"] = password

conn_args = ["-h", host, "-p", port, "-U", user, "-d", dbname]

# GUCs that newer pg_dump versions emit in the header but older servers reject.
# Restoring a pg_dump 17+ file into PostgreSQL 16 otherwise dies on
# `unrecognized configuration parameter "transaction_timeout"`. These are
# boilerplate session settings, so dropping them does not affect the data.
UNPORTABLE_HEADER_SETS = ("transaction_timeout",)


def stream_sql(path, stdin):
    """Feed a plain-SQL dump to psql, dropping unportable header SET lines.

    Every SET sits above the first COPY, so only the header is inspected line
    by line; the data body is handed over in bulk.
    """
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line.startswith(("COPY ", "INSERT ")):
                stdin.write(line)
                shutil.copyfileobj(handle, stdin)
                return
            if line.startswith("SET ") and any(
                guc in line for guc in UNPORTABLE_HEADER_SETS
            ):
                print(f"  dropping unportable header line: {line.strip()}")
                continue
            stdin.write(line)


def run_psql(cmd, path):
    """Stream `path` into psql, collecting its output via a temp file.

    psql's output goes to a file rather than a pipe so it can never fill and
    block the process while we are still feeding it hundreds of MB on stdin.
    """
    with tempfile.TemporaryFile("w+") as outfile:
        proc = subprocess.Popen(
            cmd,
            env=env,
            stdin=subprocess.PIPE,
            stdout=outfile,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            stream_sql(path, proc.stdin)
        except BrokenPipeError:
            # psql aborted (ON_ERROR_STOP) before consuming the whole stream;
            # its exit code and output below explain why.
            pass
        finally:
            try:
                proc.stdin.close()
            except BrokenPipeError:
                pass
        returncode = proc.wait()
        outfile.seek(0)
        return subprocess.CompletedProcess(cmd, returncode, outfile.read(), "")


if snapshot_path.suffix == ".dump":
    cmd = [
        "pg_restore",
        *conn_args,
        "--data-only",
        "--disable-triggers",
        "--no-owner",
        "--no-acl",
        "--exit-on-error",
        str(snapshot_path),
    ]
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
else:
    cmd = [
        "psql",
        *conn_args,
        "--quiet",
        "--no-psqlrc",
        "--single-transaction",
        "-v",
        "ON_ERROR_STOP=1",
    ]
    print("Running:", " ".join(cmd), f"< {snapshot_path}")
    result = run_psql(cmd, snapshot_path)

if result.stdout:
    print(result.stdout)
if result.returncode != 0:
    # The snapshot is optional demo data, not schema. Alembic has already
    # produced the correct schema above, so a restore failure must not stop the
    # API from starting -- otherwise the container crash-loops and a fresh
    # clone can never boot.
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    print(
        f"WARNING: snapshot restore failed with exit code {result.returncode}. "
        "Schema is correct and migrated to head, but demo data was NOT loaded. "
        "Starting API with an empty database.",
        file=sys.stderr,
    )
    sys.exit(0)

with engine.connect() as conn:
    zones = conn.execute(text("SELECT COUNT(*) FROM disaster_zones")).scalar_one()
    buildings = conn.execute(text("SELECT COUNT(*) FROM buildings")).scalar_one()
    depots = conn.execute(text("SELECT COUNT(*) FROM relief_centers")).scalar_one()

print(
    "Demo snapshot restore complete "
    f"(zones={zones}, buildings={buildings}, depots={depots})."
)
PY

echo "Starting API server..."
exec "$@"
