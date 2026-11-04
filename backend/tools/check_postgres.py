"""Check local PostgreSQL and application CRUD, rolling back all test writes.
Set DATABASE_URL, or supply --env-file. No credentials are printed or persisted.
"""

import argparse
import json
import os
import sys
import uuid
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.database_config import database_url

TABLES = (
    "profiles",
    "modules",
    "exercises",
    "criteria_versions",
    "training_sessions",
    "attempts",
    "metric_definitions",
    "measurements",
    "accounts",
    "auth_sessions",
)


def env_url(path):
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and key.strip() == "DATABASE_URL":
            value = value.strip()
            if len(value) > 1 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            return value
    return None


def check(value):
    url = database_url(value)
    hosts = [url.host, url.query.get("host", url.host)]
    if any(host not in ("127.0.0.1", "localhost", "::1") for host in hosts):
        raise ValueError("This check accepts local PostgreSQL hosts only.")
    engine = create_engine(url, connect_args={"connect_timeout": 5})
    report = {
        "endpoint": {
            "host": url.host,
            "port": url.port or 5432,
            "database": url.database,
            "user": url.username,
        },
        "connected": False,
        "application_schema_ready": False,
        "crud": {},
        "rollback_verified": False,
    }
    ids = [-(uuid.uuid4().int % 1_000_000_000 + 1) for _ in range(2)]
    while ids[0] == ids[1]:
        ids[1] = -(uuid.uuid4().int % 1_000_000_000 + 1)
    try:
        with engine.connect() as conn:
            transaction = conn.begin()
            try:
                conn.execute(text("SET LOCAL statement_timeout='5s'"))
                conn.execute(text("SET LOCAL lock_timeout='2s'"))
                info = conn.execute(
                    text(
                        "SELECT current_database(),current_user,inet_server_addr()::text,inet_server_port(),version()"
                    )
                ).one()
                report.update(
                    connected=True,
                    database=info[0],
                    user=info[1],
                    server_address=info[2],
                    server_port=info[3],
                    version=info[4],
                )
                present = set(
                    conn.execute(
                        text("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname='public'")
                    ).scalars()
                )
                report["missing_tables"] = [name for name in TABLES if name not in present]
                report["table_checks"] = {}
                for name in TABLES:
                    if name not in present:
                        continue
                    permissions = {
                        action: bool(
                            conn.execute(
                                text("SELECT has_table_privilege(current_user,:table,:action)"),
                                {"table": "public." + name, "action": action},
                            ).scalar()
                        )
                        for action in ("SELECT", "INSERT", "UPDATE", "DELETE")
                    }
                    count = (
                        conn.execute(text('SELECT COUNT(*) FROM public."' + name + '"')).scalar()
                        if permissions["SELECT"]
                        else None
                    )
                    report["table_checks"][name] = {"rows": count, "permissions": permissions}
                report["application_schema_ready"] = not report["missing_tables"] and all(
                    all(item["permissions"].values()) for item in report["table_checks"].values()
                )
                if "profiles" not in present:
                    return report
                custom = conn.execute(
                    text(
                        "SELECT COUNT(*) FROM pg_trigger WHERE tgrelid='public.profiles'::regclass AND NOT tgisinternal AND tgenabled!='D'"
                    )
                ).scalar()
                if custom:
                    raise ValueError(
                        "Profiles has custom triggers; application CRUD check was not run."
                    )
                if conn.execute(
                    text("SELECT COUNT(*) FROM public.profiles WHERE id IN (:a,:b)"),
                    {"a": ids[0], "b": ids[1]},
                ).scalar():
                    raise ValueError("Temporary test ID collision; rerun the check.")
                label = "Codex rollback check " + uuid.uuid4().hex
                params = {"id": ids[0], "label": label}
                inserted = conn.execute(
                    text(
                        "INSERT INTO public.profiles (id,display_name,dominant_hand) VALUES (:id,:label,'RIGHT') RETURNING id"
                    ),
                    params,
                ).scalar()
                report["crud"]["insert"] = inserted == ids[0]
                fetched = conn.execute(
                    text("SELECT display_name FROM public.profiles WHERE id=:id"), params
                ).scalar()
                report["crud"]["read"] = fetched == label
                changed = conn.execute(
                    text(
                        "UPDATE public.profiles SET dominant_hand='LEFT' WHERE id=:id RETURNING dominant_hand"
                    ),
                    params,
                ).scalar()
                report["crud"]["update"] = changed == "LEFT"
                removed = conn.execute(
                    text("DELETE FROM public.profiles WHERE id=:id RETURNING id"), params
                ).scalar()
                report["crud"]["delete"] = removed == ids[0]
                conn.execute(
                    text(
                        "INSERT INTO public.profiles (id,display_name,dominant_hand) VALUES (:id,:label,'RIGHT')"
                    ),
                    {"id": ids[1], "label": label},
                )
            finally:
                transaction.rollback()
            remaining = conn.execute(
                text("SELECT COUNT(*) FROM public.profiles WHERE id IN (:a,:b)"),
                {"a": ids[0], "b": ids[1]},
            ).scalar()
            report["rollback_verified"] = remaining == 0
            conn.rollback()
        return report
    finally:
        engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path)
    args = parser.parse_args()
    value = env_url(args.env_file) if args.env_file else os.getenv("DATABASE_URL")
    try:
        report = check(value)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return (
            0
            if report["application_schema_ready"]
            and report["rollback_verified"]
            and all(report["crud"].values())
            else 1
        )
    except SQLAlchemyError as exc:
        origin = getattr(exc, "orig", None)
        state = getattr(origin, "sqlstate", None)
        hints = {
            "28P01": "PostgreSQL rejected the supplied password.",
            "3D000": "The specified database does not exist.",
            "42501": "The database account lacks required permissions.",
            "42P01": "An application table is missing.",
            "42703": "The application schema is missing a required column.",
        }
        print(
            json.dumps(
                {
                    "connected_or_crud_failed": True,
                    "sqlstate": state,
                    "error": hints.get(
                        state,
                        "Connection or transaction failed. Check service, credentials, schema and permissions.",
                    ),
                }
            )
        )
        return 1
    except (ValueError, RuntimeError, OSError) as exc:
        print(json.dumps({"error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
