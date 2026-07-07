"""
Backup the PostgreSQL database to a timestamped .sql.gz file.

Usage:
    python scripts/backup_db.py                          # saves to backups/ dir
    python scripts/backup_db.py /path/to/output/dir      # saves to custom dir

Requires pg_dump to be on PATH and DATABASE_URL to be set in .env.

The output filename is:  tnt_backup_YYYYMMDD_HHMMSS.sql.gz
"""
import gzip
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

# Ensure we can load .env
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def parse_pg_url(url: str) -> dict:
    """Parse DATABASE_URL into pg_dump-compatible connection params."""
    parsed = urlparse(url)
    return {
        "host": parsed.hostname or "localhost",
        "port": str(parsed.port or 5432),
        "dbname": parsed.path.lstrip("/"),
        "user": parsed.username or "postgres",
        "password": parsed.password or "",
    }


def run_backup(output_dir: str | Path) -> str:
    """Run pg_dump, gzip the output, return the filename."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL not found in .env")
        sys.exit(1)

    params = parse_pg_url(db_url)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"tnt_backup_{timestamp}.sql"
    gz_filename = filename + ".gz"
    gz_path = output_dir / gz_filename

    # Set PGPASSWORD for pg_dump
    env = os.environ.copy()
    env["PGPASSWORD"] = params["password"]

    print(f"📦 Backing up database '{params['dbname']}' on {params['host']}:{params['port']} ...")

    dump_args = [
        "pg_dump",
        "--host", params["host"],
        "--port", params["port"],
        "--username", params["user"],
        "--dbname", params["dbname"],
        "--no-password",
        "--format", "custom",   # custom format — compressed, restore with pg_restore
    ]

    # Build archive path
    archive_path = output_dir / f"tnt_backup_{timestamp}.dump"

    try:
        subprocess.run(
            dump_args + ["--file", str(archive_path)],
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"❌ pg_dump failed:\n  {e.stderr}")
        sys.exit(1)

    # Also produce a gzipped SQL version for readability
    flat_args = [
        "pg_dump",
        "--host", params["host"],
        "--port", params["port"],
        "--username", params["user"],
        "--dbname", params["dbname"],
        "--no-password",
    ]

    try:
        result = subprocess.run(
            flat_args,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        with gzip.open(gz_path, "wt", encoding="utf-8") as f:
            f.write(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"❌ pg_dump (flat) failed:\n  {e.stderr}")
        sys.exit(1)

    archive_size = archive_path.stat().st_size
    gz_size = gz_path.stat().st_size

    print(f"✅ Backup created:")
    print(f"   Custom:  {archive_path.name} ({archive_size / 1024 / 1024:.1f} MB)")
    print(f"   SQL.gz:  {gz_path.name} ({gz_size / 1024:.1f} KB)")

    return str(archive_path)


if __name__ == "__main__":
    out_dir = sys.argv[1] if len(sys.argv) > 1 else (Path(__file__).resolve().parent.parent / "backups")
    run_backup(out_dir)
