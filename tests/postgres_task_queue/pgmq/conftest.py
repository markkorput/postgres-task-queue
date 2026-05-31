import os
from contextlib import asynccontextmanager

import asyncpg
from dependency_injector import providers
import pytest
import pytest_asyncio

from postgres_task_queue.pgmq.broker import PgmqBroker, Dlq, Archive
from postgres_task_queue.pgmq.container import Container, wire


TEST_QUEUE_NAME = "test_queue"

_db_conn_cache: asyncpg.Connection | None = None
"""_db_conn stores it connection in this cache var"""


@asynccontextmanager
async def _db_conn():
    """
    Lazy-load-and-cache test-db-connection with activated transaction that will
    be rolled back when the context manager exits.
    """
    global _db_conn_cache

    # repeated invocation of _db_conn while the "root" db_conn is still "active"
    # will result in the same, already created, connection being yielded
    if _db_conn_cache:
        yield _db_conn_cache
        return

    conn = await asyncpg.connect(os.environ["PGTQ_TEST_DB_URL"])

    try:
        async with conn.transaction():
            # Set connection cache
            _db_conn_cache = conn
            yield conn
            raise ValueError("rollback")
    except ValueError as err:
        if err.args[0] != "rollback":
            raise
    finally:
        # Clear connection cache
        _db_conn_cache = None


@pytest_asyncio.fixture(scope="function")
async def db_conn():
    """
    Create a real asyncpg connection wrapped in a transaction that is rolled
    back after the test case ends

    This ensures the database is unaffected by test operations.
    """
    async with _db_conn() as conn:
        yield conn


@pytest.fixture(autouse=True)
def container():
    c = Container()
    wire(c)

    # use the _db_conn method, NOT the db_conn fixture, so the connection is lazy-loaded
    with c.conn.override(providers.Resource(_db_conn)):
        yield c


@pytest.fixture
def test_queue_name() -> str:
    return TEST_QUEUE_NAME


@pytest_asyncio.fixture
async def broker(container: Container, db_conn: asyncpg.Connection) -> PgmqBroker:
    queue = await container.pgmq()
    await queue.create_queue(TEST_QUEUE_NAME, conn=db_conn)
    await queue.create_queue(f"{TEST_QUEUE_NAME}_dlq", conn=db_conn)
    return PgmqBroker(TEST_QUEUE_NAME)


@pytest_asyncio.fixture
def archive(broker: PgmqBroker) -> Archive:
    assert broker.archive is not None
    return broker.archive


@pytest_asyncio.fixture
def dlq(broker: PgmqBroker) -> Dlq:
    assert broker.dlq is not None
    return broker.dlq
