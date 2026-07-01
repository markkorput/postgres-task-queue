from datetime import timedelta
from json import dumps, loads
from typing import Any, Callable, AsyncGenerator, Literal
import logging
import time

from asyncpg import Connection
from dependency_injector.wiring import Closing, Provide

from pgmq import AsyncPGMQueue
from pgmq.async_queue import _parse_jsonb
from pgmq.messages import Message
from pgmq.decorators import async_transaction
from pgmq.logger import log_with_context

from postgres_task_queue.core.broker import Task
from postgres_task_queue.pgmq.container import Container
from postgres_task_queue.pgmq.metadata import Header, MessageStatus
from postgres_task_queue.pgmq.models import DlqBody


logger = logging.getLogger(__name__)


class _Message:
    """Represents a single message record in a queue, providing message-level operations."""

    def __init__(self, queue_name: str, msg_id: int) -> None:
        self.queue_name = queue_name
        self.msg_id = msg_id

    @property
    def table_name(self) -> str:
        return f"q_{self.queue_name}"

    async def archive(
        self,
        conn: Connection = Closing[Provide[Container.conn]],
        pgmq: AsyncPGMQueue = Provide[Container.pgmq],
    ) -> bool:
        """Archive this message using pgmq."""
        return await pgmq.archive(self.queue_name, self.msg_id, conn=conn)

    async def delete(
        self,
        conn: Connection = Closing[Provide[Container.conn]],
        pgmq: AsyncPGMQueue = Provide[Container.pgmq],
    ) -> bool:
        """Delete this message using pgmq."""
        return await pgmq.delete(self.queue_name, self.msg_id, conn=conn)

    async def set_vt(
        self,
        vt: float,
        conn: Connection = Closing[Provide[Container.conn]],
        pgmq: AsyncPGMQueue = Provide[Container.pgmq],
    ) -> Message:
        """Set visibility timeout for this message using pgmq."""
        return await pgmq.set_vt(
            queue=self.queue_name,
            msg_id=self.msg_id,
            vt=int(vt),
            conn=conn,
        )

    async def retry(self, delay_seconds: float) -> None:
        """
        Reset this message for retry by updating its vt and headers.

        This makes the message visible again in the queue after an optional delay,
        without needing to archive it or create a new message. The vt is computed
        based on the processor's retry_delay strategy.
        """
        await self.add_header(
            Header.STATUS.full_name(),
            MessageStatus.QUEUED,
        )

        await self.set_vt(time.time() + delay_seconds)

    async def get_headers(
        self,
        conn: Connection = Closing[Provide[Container.conn]],
    ) -> dict[str, Any] | None:
        """Retrieve all headers for this message."""
        result = await conn.fetchval(
            f"""SELECT headers FROM pgmq.{self.table_name} WHERE msg_id = $1""",
            self.msg_id,
        )
        return loads(result) if result else None

    async def add_header(
        self,
        header_name: str,
        header_value: object,
        conn: Connection = Closing[Provide[Container.conn]],
    ) -> None:
        """Add or update a header on a message. Preserves existing headers."""
        header_json = dumps({header_name: header_value})

        await conn.execute(
            f"""UPDATE pgmq.{self.table_name}
                SET headers = COALESCE(headers, '{{}}'::jsonb) || ($1::jsonb)
                WHERE msg_id = $2""",
            header_json,
            self.msg_id,
        )

    async def add_error(self, error: str) -> list[str]:
        """
        Add the given (string representation of) error to the
        errors header and returns all errors in the header.
        """
        # add exception to errors header
        headers = await self.get_headers()
        errors: list[str] = (headers or {}).get(Header.ERRORS.full_name()) or []
        errors = [*errors, error]

        await self.add_header(
            Header.ERRORS.full_name(),
            errors,
        )

        return errors

    async def get_payload(
        self,
        conn: Connection = Closing[Provide[Container.conn]],
    ) -> dict[str, Any]:
        message = await conn.fetchval(
            f"SELECT message FROM pgmq.{self.table_name} WHERE msg_id = $1",
            self.msg_id,
        )

        if not message:
            raise ValueError(f"Message with id {self.msg_id} not found")

        return loads(message)


class _Table:
    """Represents a pgmq DB table table"""

    def __init__(self, name: str) -> None:
        self.name = name

    async def count(self, conn: Connection = Closing[Provide[Container.conn]]) -> int:
        """Counts the total number of tasks (pgmq message) in the queue (table)"""
        result = await conn.fetchval(f"SELECT COUNT(*) FROM pgmq.{self.name}")
        return result or 0

    pending_condition = "vt = NULL OR vt < NOW()"

    async def pending_count(
        self, conn: Connection = Closing[Provide[Container.conn]]
    ) -> int:
        """
        Counts the number of "in progress" tasks in the queue_name

        A tasks is considered "in progress" when its pgmqmessage's visibility
        timeout (vt) is active (larger than the current time)
        """
        result = await conn.fetchval(
            f"SELECT COUNT(*) FROM pgmq.{self.name} WHERE {self.pending_condition}"
        )
        return result or 0

    vt_condition = "vt > NOW()"
    processing_condition = (
        f"headers->>'{Header.STATUS.full_name()}' = '{MessageStatus.PROCESSING}'"
    )

    async def processing_count(
        self, conn: Connection = Closing[Provide[Container.conn]]
    ) -> int:
        """
        Counts the number of "in progress" tasks in the queue_name

        A tasks is considered "in progress" when its pgmqmessage's visibility
        timeout (vt) is active (larger than the current time) and
        the STATUS header is set to PROCESSING.
        """
        result = await conn.fetchval(
            f"SELECT COUNT(*) FROM pgmq.{self.name} WHERE {self.vt_condition} AND {self.processing_condition}"
        )
        return result or 0

    async def items(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        conn: Connection = Closing[Provide[Container.conn]],
    ) -> AsyncGenerator[Task, None]:
        """List items from the queue without consuming them."""
        async with conn.transaction():
            async for row in conn.cursor(
                f"""SELECT msg_id, message FROM pgmq.{self.name} 
                ORDER BY msg_id OFFSET $1 LIMIT $2""",
                offset,
                limit,
            ):
                yield Task(row["msg_id"], loads(row["message"]))


class _QueueTable(_Table):
    """Represents a queue table"""

    def __init__(self, queue_name: str):
        super().__init__(f"q_{queue_name}")
        self.queue_name = queue_name

    async def enqueue(
        self,
        payload: dict[str, Any],
        *,
        group: str | None = None,
        conn: Connection = Closing[Provide[Container.conn]],
        pgmq: AsyncPGMQueue = Provide[Container.pgmq],
    ) -> int:
        """Enqueue a message to the queue using pgmq."""
        headers = {"x-pgmq-group": group} if group else None
        return await pgmq.send(self.queue_name, payload, headers=headers, conn=conn)

    def message(self, msg_id: int) -> _Message:
        """Get a MessageRecord for a specific message in this queue."""
        return _Message(self.queue_name, msg_id)


class Archive(_Table):
    """Represents a pgmq archive (a_*) table"""

    async def prune(
        self,
        *,
        ttl: timedelta | None = None,
        limit: int | None = None,
        batch_size: int = 1000,
        conn: Connection = Closing[Provide[Container.conn]],
    ) -> int:
        """Delete archived messages. When ttl is specified, deletes records older than ttl.
        When limit is specified, keeps only the most recent limit records (deletes oldest).
        batch_size limits the number of records deleted in a single operation.
        Returns the number of deleted records, or 0 if both ttl and limit are None."""
        conditions = []

        if ttl is not None:
            total_seconds = ttl.total_seconds()
            conditions.append(
                f"archived_at < NOW() - INTERVAL '{total_seconds} seconds'"
            )

        if limit is not None:
            conditions.append(
                f"msg_id NOT IN (SELECT msg_id FROM pgmq.{self.name} ORDER BY archived_at DESC LIMIT {limit})"
            )

        if not conditions:
            return 0

        where_clause = " OR ".join(conditions)
        result = await conn.execute(
            f"WITH to_delete AS (SELECT msg_id FROM pgmq.{self.name} WHERE {where_clause} LIMIT {batch_size}) DELETE FROM pgmq.{self.name} WHERE msg_id IN (SELECT msg_id FROM to_delete)"
        )
        return int(result.split()[1])


class Dlq(_QueueTable):
    def __init__(self, name: str, archive_table_name: str | None = None):
        super().__init__(name)
        self._archive_table_name = archive_table_name

    @property
    def archive(self) -> Archive | None:
        return Archive(self._archive_table_name) if self._archive_table_name else None


def _table_name(input: str | bool, default: str) -> str | None:
    if input is True:
        return default
    if input is False:
        return None
    return input


class PgmqBroker(_QueueTable):
    def __init__(
        self,
        queue_name: str,
        archive_table: str | bool = True,
        dlq_queue_name: str | bool = True,
        dlq_archive_name: str | bool = True,
    ):
        super().__init__(queue_name)

        self.queue_name = queue_name

        self.archive_table_name = _table_name(
            archive_table,
            f"a_{queue_name}",
        )
        self.dlq_queue_name = _table_name(
            dlq_queue_name,
            f"{queue_name}_dlq",
        )
        self.dlq_archive_name = (
            _table_name(
                dlq_archive_name,
                f"a_{self.dlq_queue_name}",
            )
            if self.dlq_queue_name
            else None
        )

    @property
    def archive(self) -> Archive | None:
        return Archive(self.archive_table_name) if self.archive_table_name else None

    @property
    def dlq(self) -> Dlq | None:
        return (
            Dlq(self.dlq_queue_name, self.dlq_archive_name)
            if self.dlq_queue_name
            else None
        )

    async def poll(
        self,
        vt: int = 30,
        qty: int = 1,
        max_poll_seconds: int = 5,
        poll_interval_ms: int = 100,
        lifo: bool = False,
        conn: Connection = Closing[Provide[Container.conn]],
    ) -> tuple[Task, ...]:
        """Poll for messages from the queue."""
        messages = await self._read_with_poll(
            self.queue_name,
            vt=vt,
            qty=qty,
            max_poll_seconds=max_poll_seconds,
            poll_interval_ms=poll_interval_ms,
            direction="DESC" if lifo else "ASC",
            conn=conn,
        )
        return tuple(Task(msg.msg_id, msg.message) for msg in messages or [])

    @async_transaction
    async def _read_with_poll(
        self,
        queue: str,
        *,
        vt: int,
        conn: Connection,
        qty: int = 1,
        max_poll_seconds: int = 5,
        poll_interval_ms: int = 100,
        conditional: dict[str, Any] | None = None,
        direction: Literal["ASC"] | Literal["DESC"] = "ASC",
    ) -> list[Message]:
        """Read with long-polling -- This is a patched version of AsyncPGMQueue's `read_with_poll` method"""
        log_with_context(
            logger, logging.DEBUG, "Reading with poll", queue=queue, qty=qty
        )

        actual_vt = vt

        if conditional:
            raise NotImplementedError("conditional support not implemented yet")
        else:
            sql = """SELECT msg_id, read_ct, enqueued_at, last_read_at, vt, message, headers 
                    FROM pgmq.read_with_poll(queue_name=>$1::text, vt=>$2::integer, qty=>$3::integer, 
                    max_poll_seconds=>$4::integer, poll_interval_ms=>$5::integer, direction=>$6::text);"""

            params = (
                queue,
                actual_vt,
                qty,
                max_poll_seconds,
                poll_interval_ms,
                direction,
            )

        rows = await conn.fetch(sql, *params)
        return [Message.from_row(row, _parse_jsonb) for row in rows]

    async def poll_grouped(
        self,
        vt: int = 30,
        qty: int = 1,
        max_poll_seconds: int = 5,
        poll_interval_ms: int = 100,
        lifo: bool = False,
        conn: Connection = Closing[Provide[Container.conn]],
    ) -> tuple[Task, ...]:
        """Poll for messages from the queue with strict group ordering."""
        messages = await self._read_grouped_rr_with_poll(
            queue=self.queue_name,
            vt=vt,
            qty=qty,
            max_poll_seconds=max_poll_seconds,
            poll_interval_ms=poll_interval_ms,
            conn=conn,
            direction="DESC" if lifo else "ASC",
        )

        return tuple(Task(msg.msg_id, msg.message) for msg in messages or [])

    @async_transaction
    async def _read_grouped_rr_with_poll(
        self,
        queue: str,
        *,
        conn: Connection,
        vt: int,
        qty: int = 1,
        max_poll_seconds: int = 5,
        poll_interval_ms: int = 100,
        direction: Literal["ASC"] | Literal["DESC"] = "ASC",
    ) -> list[Message]:
        """FIFO round-robin read with poll -- this is a patched version oof AsyncPGMQueue.read_grouped_rr_with_poll"""
        log_with_context(
            logger,
            logging.DEBUG,
            "Reading grouped RR with poll",
            queue=queue,
            qty=qty,
            max_poll_seconds=max_poll_seconds,
            poll_interval_ms=poll_interval_ms,
        )

        sql = """SELECT msg_id, read_ct, enqueued_at, last_read_at, vt, message, headers 
            FROM pgmq.read_grouped_rr_with_poll(queue_name=>$1::text, vt=>$2::integer, qty=>$3::integer,
            max_poll_seconds=>$4::integer, poll_interval_ms=>$5::integer, direction=>$6::text);"""

        rows = await conn.fetch(
            sql,
            queue,
            vt,
            qty,
            max_poll_seconds,
            poll_interval_ms,
            direction,
        )
        return [Message.from_row(row, _parse_jsonb) for row in rows]

    async def start(self, msg_id: int) -> None:
        await self.message(msg_id).add_header(
            Header.STATUS.full_name(), MessageStatus.PROCESSING
        )

    async def complete(self, msg_id: int) -> None:
        await self._remove(msg_id, MessageStatus.COMPLETED)

    async def fail(
        self,
        msg_id: int,
        exc: Exception,
        *,
        max_retries: int = 0,
        delay_seconds: Callable[[int], float] | float = 0.0,
    ) -> None:
        message = self.message(msg_id)

        errors = await message.add_error(str(exc))

        # Retry?
        if max_retries and len(errors) < max_retries:
            logger.info(
                f"Scheduling message {msg_id} for retry (attempt {len(errors)}/{max_retries})"
            )

            await message.retry(
                delay_seconds
                if isinstance(delay_seconds, (float, int))
                else delay_seconds(len(errors))
            )
            return

        # Dlq?
        if self.dlq:
            # Post DLQ message with reference to the failed message
            dlq_msg_id = await self.dlq.enqueue(
                DlqBody(
                    msg_id=msg_id,
                    queue_name=self.queue_name,
                    message=await message.get_payload(),
                    errors=errors,
                ).model_dump(),
            )

            # Set DLQ header on original message
            await message.add_header(
                Header.DLQ.full_name(),
                str(dlq_msg_id),
            )

        await self._remove(msg_id, MessageStatus.FAILED)

    async def _remove(self, msg_id: int, status: MessageStatus) -> None:
        message = self.message(msg_id)

        if self.archive:
            await message.add_header(Header.STATUS.full_name(), status)
            await message.archive()
        else:
            await message.delete()

    async def count(
        self,
        conn: Connection = Closing[Provide[Container.conn]],
    ) -> int:
        """Count the total number of items in the queue."""
        result = await conn.fetchval(f"SELECT COUNT(*) FROM pgmq.q_{self.queue_name}")
        return result or 0

    async def reschedule(
        self,
        dlq_msg_id: int,
        conn: Connection = Closing[Provide[Container.conn]],
    ) -> int:
        """
        Reschedule a DLQ message by creating a new message in the original queue.

        This method:
        1. Gets the DLQ message payload
        2. Creates a new message in the task queue with the same payload as the DLQ-ed item
        3. Adds x-pgtq-original header to the new message (if queue archive is enabled)
        4. Adds x-pgtq-retry header to the DLQ message (if DLQ archive is enabled)
        5. Archives or deletes the DLQ message based on availability of DLQ archive

        All operations happen in a single transaction.

        Args:
            dlq_msg_id: The message ID of the DLQ message to reschedule

        Returns:
            The msg_id of the newly scheduled message in the original queue
        """

        if not self.dlq:
            raise ValueError(f"Queue {self.queue_name} has no DLQ configured")

        dlq_message = self.dlq.message(dlq_msg_id)

        async with conn.transaction():
            # Get the DLQ message payload
            payload = await dlq_message.get_payload(conn=conn)
            dlq_body = DlqBody.model_validate(payload)

            # Send new message to original queue
            new_msg_id = await self.enqueue(dlq_body.message, conn=conn)

            # Add x-pgtq-original header to new message (if queue archive is enabled)
            if self.archive:
                await self.message(new_msg_id).add_header(
                    Header.ORIGINAL.full_name(),
                    str(dlq_body.msg_id),
                    conn=conn,
                )

            # Add x-pgtq-retry header to DLQ message (if DLQ archive is enabled)
            if self.dlq.archive:
                await dlq_message.add_header(
                    Header.RETRY.full_name(),
                    str(new_msg_id),
                    conn=conn,
                )

                # Archive the DLQ message
                await dlq_message.archive(conn=conn)
            else:
                await dlq_message.delete(conn=conn)

        return new_msg_id
