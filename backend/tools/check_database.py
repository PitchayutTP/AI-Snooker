"""Read-only check of the configured PostgreSQL connection and application tables."""
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def main():
    try:
        from sqlalchemy import text,inspect
        from app.database import engine,Base
        import app.auth
        with engine.connect() as connection:
            connection.execute(text('SELECT 1'))
            database=connection.scalar(text('SELECT current_database()'))
            existing=set(inspect(connection).get_table_names())
        missing=sorted(set(Base.metadata.tables)-existing)
        print(json.dumps({'connected':True,'driver':engine.dialect.driver,'database':database,
                          'missing_tables':missing,'ready':not missing},indent=2))
        if missing:print('Start the backend to create missing tables.');return 1
        return 0
    except Exception as exc:
        # Do not echo a connection URL/password into diagnostics.
        print('PostgreSQL check failed:',type(exc).__name__)
        print('Check DATABASE_URL, PostgreSQL service, database name, port and credentials.')
        return 1


if __name__=='__main__':raise SystemExit(main())
