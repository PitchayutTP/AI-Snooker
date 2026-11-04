"""Run from backend: python -m tools.export_schema > schema-postgresql.sql"""

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

from app.database import Base

if __name__ == "__main__":
    dialect = postgresql.dialect()
    for table in Base.metadata.sorted_tables:
        print(str(CreateTable(table).compile(dialect=dialect)) + ";")
        for index in table.indexes:
            print(str(CreateIndex(index).compile(dialect=dialect)) + ";")
