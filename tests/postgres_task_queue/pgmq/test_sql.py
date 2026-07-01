from pathlib import Path
from postgres_task_queue.pgmq import sql

_sql_folder_path = Path(__file__).parent.parent.parent.parent


def _version_path(version: str) -> Path:
    return _sql_folder_path / f"pgmq-{version}.sql"


class TestGetPgmqSql:
    def test_latest_version(self):
        assert sql.LATEST_PGMQ_SQL_VERSION == "0.1.1"

    def test_get_latest(self):
        assert (
            sql.get_pgmq_sql() == _version_path(sql.LATEST_PGMQ_SQL_VERSION).read_text()
        )

    def test_get_v_0_1_1(self):
        assert sql.get_pgmq_sql("0.1.1") == _version_path("0.1.1").read_text()
