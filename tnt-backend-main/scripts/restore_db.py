"""
Restore the PostgreSQL database from a backup file.

Usage:
    python scripts/restore_db.py backups/tnt_backup_20260624_235959.dump
    python scripts/restore_db.py backups/tnt_backup_20260624_235959.sql.gz

Supports both:
  - .dump  (pg_restore custom format)
  - .sql   / .sql.gz  (psql plain SQL)

⚠ DESTRUCTIVE: This drops and recreates the database.  Use with caution.

Requires pg_dump / pg_restore / psql on PATH and DATABASE_URL in .env.
"""
import gzip
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def parse_pg_url(url: str) -> dict:
    parsed = urlparse(url)
    return {
        "host": parsed.hostname or "localhost",
        "port": str(parsed.port or 5432),
        "dbname": parsed.path.lstrip("/"),
        "user": parsed.username or "postgres",
        "password": parsed.password or "",
    }


def confirm_destructive_action(prompt: str) -> bool:
    """Ask for confirmation before destructive operation."""
    print(f"\n⚠  {prompt}")
    reply = input('Type "yes" to confirm: ').strip().lower()
    return reply == "yes"


def restore_dump(file_path: Path, params: dict):
    """Restore a .dump file with pg_restore."""
    env = os.environ.copy()
    env["PGPASSWORD"] = params["password"]

    # Drop and recreate the target database
    drop_cmd = [
        "dropdb",
        "--host", params["host"],
        "--port", params["port"],
        "--username", params["user"],
        "--if-exists",
        params["dbname"],
    ]
    subprocess.run(drop_cmd, env=env, capture_output=True)

    create_cmd = [
        "createdb",
        "--host", params["host"],
        "--port", params["port"],
        "--username", params["user"],
        params["dbname"],
    ]
    subprocess.run(create_cmd, env=env, check=True, capture_output=True)

    # Restore
    restore_cmd = [
        "pg_restore",
        "--host", params["host"],
        "--port", params["port"],
        "--username", params["user"],
        "--dbname", params["dbname"],
        "--no-password",
        "--clean",
        "--if-exists",
        str(file_path),
    ]

    print(f"🔄 Restoring from {file_path.name} ...")
    try:
        subprocess.run(restore_cmd, env=env, check=True, capture_output=True, text=True)
        print(f"✅ Restore completed from {file_path.name}")
    except subprocess.CalledProcessError as e:
        print(f"❌ pg_restore failed:\n  {e.stderr}")
        sys.exit(1)


def restore_sql(file_path: Path, params: dict):
    """Restore a .sql or .sql.gz file with psql."""
    env = os.environ.copy()
    env["PGPASSWORD"] = params["password"]

    # Drop and recreate
    drop_cmd = [
        "dropdb",
        "--host", params["host"],
        "--port", params["port"],
        "--username", params["user"],
        "--if-exists",
        params["dbname"],
    ]
    subprocess.run(drop_cmd, env=env, capture_output=True)

    create_cmd = [
        "createdb",
        "--host", params["host"],
        "--port", params["port"],
        "--username", params["user"],
        params["dbname"],
    ]
    subprocess.run(create_cmd, env=env, check=True, capture_output=True)

    psql_cmd = [
        "psql",
        "--host", params["host"],
        "--port", params["port"],
        "--username", params["user"],
        "--dbname", params["dbname"],
    ]

    print(f"🔄 Restoring from {file_path.name} ...")
    try:
        if file_path.suffix == ".gz":
            with gzip.open(file_path, "rt", encoding="utf-8") as f:
                sql_content = f.read()
            proc = subprocess.Popen(psql_cmd, stdin=subprocess.PIPE, env=env, text=True)
            proc.communicate(input=sql_content)
            if proc.returncode != 0:
                raise subprocess.CalledProcessError(proc.returncode, psql_cmd)
        else:
            psql_cmd.append("-f")
            psql_cmd.append(str(file_path))
            subprocess.run(psql_cmd, env=env, check=True, capture_output=True, text=True)
        print(f"✅ Restore completed from {file_path.name}")
    except subprocess.CalledProcessError as e:
        print(f"❌ psql restore failed:\n  {e.stderr or 'unknown'}")
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/restore_db.py <backup-file>")
        print("Example: python scripts/restore_db.py backups/tnt_backup_20260624_235959.dump")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        sys.exit(1)

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL not found in .env")
        sys.exit(1)

    params = parse_pg_url(db_url)

    print(f"ℹ️  Target database: {params['dbname']} on {params['host']}:{params['port']}")
    print(f"ℹ️  Backup file: {file_path} ({file_path.stat().st_size / 1024 / 1024:.1f} MB)")

    if not confirm_destructive_action(
        f"This will DROP and recreate the database '{params['dbname']}'. "
        "All current data will be lost. Continue?"
    ):
        print("❌ Restore cancelled.")
        sys.exit(0)

    suffix = file_path.suffix
    if suffix == ".dump":
        restore_dump(file_path, params)
    elif suffix == ".gz":
        restore_sql(file_path, params)
    elif suffix == ".sql":
        restore_sql(file_path, params)
    else:
        print(f"❌ Unknown backup format: {suffix} (expected .dump, .sql, or .sql.gz)")
        sys.exit(1)


if __name__ == "__main__":
    main()
