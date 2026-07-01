from pathlib import Path
from typing import Literal

LATEST_PGMQ_SQL_VERSION = "0.1.1"

SqlVersions = Literal["0.1.1"]

_sql_folder_path = Path(__file__).parent.parent.parent.parent


def get_pgmq_sql(version: SqlVersions | None = None) -> str:
    if not version:
        version = LATEST_PGMQ_SQL_VERSION

    sql_path = _sql_folder_path / f"pgmq-{version}.sql"
    return sql_path.read_text()
