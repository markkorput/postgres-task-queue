from contextlib import asynccontextmanager
from typing import Callable, AsyncContextManager

from asyncpg import Connection
from dependency_injector import containers, providers

from pgmq import AsyncPGMQueue


async def _create_pgmq() -> AsyncPGMQueue:
    queue = AsyncPGMQueue()
    queue.config.init_extension = False
    await queue.init()
    return queue


@asynccontextmanager
async def _conn(pgmq: AsyncPGMQueue):
    assert pgmq.pool
    async with pgmq.pool.acquire() as conn:
        yield conn


class Container(containers.DeclarativeContainer):
    pgmq = providers.Singleton(_create_pgmq)
    conn = providers.Resource(_conn, pgmq=pgmq)


def wire(container: Container) -> None:
    """Wires the given container on the entire postgres_task_queue package and its sub-modules"""
    container.wire(modules=["postgres_task_queue.pgmq.broker"])


def setup(
    connection: Callable[[], AsyncContextManager[Connection]] | None = None,
    pgmq: AsyncPGMQueue | None = None,
) -> None:
    """
    Set up and configure the PGMQ container for postgres_task_queue.

    This function creates and configures a dependency injection container
    with the necessary components for the PGMQ backend. Users can provide
    either a connection factory or a pre-configured PGMQ instance.

    Args:
        connection: An async context manager that yields an asyncpg Connection.
            If provided, this will be used to create connections instead of using
            the PGMQ pool. This is the recommended way to provide your database
            connection configuration.
            Example:
                async def get_connection():
                    conn = await asyncpg.connect(DATABASE_URL)
                    try:
                        yield conn
                    finally:
                        await conn.close()
                setup(connection=get_connection)

        pgmq: A pre-configured AsyncPGMQueue instance. If provided,
            this will be used instead of creating a new one. Use this if you
            need custom PGMQ configuration.


        # Note that its only necessary to configure EITHER the connection or the
        # pgmq instance.
    """
    container = Container()

    if pgmq is not None:
        # Use the provided PGMQ instance
        async def coro():
            return pgmq

        container.pgmq = providers.Singleton(coro)

    if connection is not None:
        # Override the conn provider with the user's factory
        container.conn = providers.Resource(connection)

    wire(container)
