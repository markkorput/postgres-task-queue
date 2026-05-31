import pytest
from json import loads

import asyncpg

from postgres_task_queue.pgmq.broker import PgmqBroker, Dlq, Archive
from postgres_task_queue.pgmq.container import Container


class _AsyncContextManager:
    """Mock async context manager for transaction."""

    async def __aenter__(self):
        return None

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None


@pytest.mark.asyncio
class TestEnqueue:
    async def test_adds_message_to_queue_and_returns_msg_id(
        self, broker: PgmqBroker, db_conn: asyncpg.Connection
    ):
        payload = {"foo": "bar2"}
        msg_id = await broker.enqueue(payload)

        results = await db_conn.fetch(
            f"SELECT msg_id, message FROM pgmq.q_{broker.queue_name}"
        )
        assert {row["msg_id"]: loads(row["message"]) for row in results} == {
            msg_id: payload
        }

    async def test_enqueue_with_empty_payload(
        self, broker: PgmqBroker, db_conn: asyncpg.Connection
    ):
        msg_id = await broker.enqueue({})

        results = await db_conn.fetch(
            f"SELECT msg_id, message FROM pgmq.q_{broker.queue_name}"
        )
        assert len(results) == 1
        assert results[0]["msg_id"] == msg_id
        assert loads(results[0]["message"]) == {}

    async def test_enqueue_multiple_messages(
        self, broker: PgmqBroker, db_conn: asyncpg.Connection
    ):
        payloads = [{"task": f"item_{i}"} for i in range(3)]
        msg_ids = [await broker.enqueue(p) for p in payloads]

        results = await db_conn.fetch(
            f"SELECT msg_id, message FROM pgmq.q_{broker.queue_name} ORDER BY msg_id"
        )
        assert len(results) == 3
        for result, expected_id in zip(results, sorted(msg_ids)):
            assert result["msg_id"] == expected_id

    async def test_enqueue_with_group_sets_header(
        self, broker: PgmqBroker, db_conn: asyncpg.Connection
    ):
        payload = {"foo": "bar"}
        group_name = "my-group"
        msg_id = await broker.enqueue(payload, group=group_name)

        headers = await db_conn.fetchval(
            f"SELECT headers FROM pgmq.q_{broker.queue_name} WHERE msg_id = $1",
            msg_id,
        )
        assert headers is not None
        assert loads(headers) == {"x-pgmq-group": group_name}

    async def test_enqueue_without_group_has_no_header(
        self, broker: PgmqBroker, db_conn: asyncpg.Connection
    ):
        payload = {"foo": "bar"}
        msg_id = await broker.enqueue(payload)

        headers = await db_conn.fetchval(
            f"SELECT headers FROM pgmq.q_{broker.queue_name} WHERE msg_id = $1",
            msg_id,
        )
        assert headers is None

    async def test_enqueue_with_none_group_has_no_header(
        self, broker: PgmqBroker, db_conn: asyncpg.Connection
    ):
        payload = {"foo": "bar"}
        msg_id = await broker.enqueue(payload, group=None)

        headers = await db_conn.fetchval(
            f"SELECT headers FROM pgmq.q_{broker.queue_name} WHERE msg_id = $1",
            msg_id,
        )
        assert headers is None

    async def test_enqueue_with_different_groups(
        self, broker: PgmqBroker, db_conn: asyncpg.Connection
    ):
        payload = {"task": "test"}
        group1 = "group-a"
        group2 = "group-b"

        msg_id1 = await broker.enqueue(payload, group=group1)
        msg_id2 = await broker.enqueue(payload, group=group2)

        headers1 = await db_conn.fetchval(
            f"SELECT headers FROM pgmq.q_{broker.queue_name} WHERE msg_id = $1",
            msg_id1,
        )
        headers2 = await db_conn.fetchval(
            f"SELECT headers FROM pgmq.q_{broker.queue_name} WHERE msg_id = $1",
            msg_id2,
        )

        assert loads(headers1) == {"x-pgmq-group": group1}
        assert loads(headers2) == {"x-pgmq-group": group2}


@pytest.mark.asyncio
class TestPoll:
    async def test_polls_and_returns_tasks(
        self, broker: PgmqBroker, db_conn: asyncpg.Connection
    ):
        payload1 = {"task": "one"}
        payload2 = {"task": "two"}
        msg_id1 = await broker.enqueue(payload1)
        msg_id2 = await broker.enqueue(payload2)

        tasks = await broker.poll(qty=2, conn=db_conn)

        assert len(tasks) == 2
        task_ids = {t.id for t in tasks}
        assert task_ids == {msg_id1, msg_id2}
        task_payloads = {t.id: t.payload for t in tasks}
        assert task_payloads == {msg_id1: payload1, msg_id2: payload2}

    async def test_polls_limited_quantity(
        self, broker: PgmqBroker, db_conn: asyncpg.Connection
    ):
        for i in range(5):
            await broker.enqueue({"task": f"item_{i}"})

        tasks = await broker.poll(qty=2, conn=db_conn)

        assert len(tasks) == 2

    async def test_polls_empty_queue(
        self, broker: PgmqBroker, db_conn: asyncpg.Connection
    ):
        tasks = await broker.poll(qty=1, max_poll_seconds=1, conn=db_conn)
        assert tasks == ()

    async def test_poll_with_vt_parameter(
        self,
        broker: PgmqBroker,
        db_conn: asyncpg.Connection,
    ):
        from datetime import datetime, timedelta

        payload = {"task": "test"}
        msg_id = await broker.enqueue(payload)

        # Poll with a visibility timeout
        tasks = await broker.poll(vt=10, qty=1)

        assert len(tasks) == 1
        assert tasks[0].id == msg_id
        assert tasks[0].payload == payload

        # Verify vt was set on the message
        result = await db_conn.fetchval(
            f"SELECT vt FROM pgmq.q_{broker.queue_name} WHERE msg_id = $1",
            msg_id,
        )
        assert result is not None
        # vt should be approximately now + 10 seconds
        # Use timezone-aware datetime for comparison
        current_time = datetime.now(datetime.now().astimezone().tzinfo)
        assert result > current_time + timedelta(seconds=9)
        assert result < current_time + timedelta(seconds=11)


@pytest.mark.asyncio
class TestPollGrouped:
    async def test_poll_grouped_returns_single_task(
        self,
        broker: PgmqBroker,
    ):
        payload = {"task": "test"}
        msg_ids = [
            await broker.enqueue(payload, group="test-group-1"),
            await broker.enqueue(payload, group="test-group-1"),
            await broker.enqueue(payload, group="test-group-2"),
        ]

        tasks = await broker.poll_grouped(qty=2)

        assert len(tasks) == 2
        assert [t.id for t in tasks] == [msg_ids[0], msg_ids[2]]

    async def test_poll_grouped_empty_queue(
        self,
        broker: PgmqBroker,
    ):
        tasks = await broker.poll_grouped(max_poll_seconds=1)
        assert tasks == ()


@pytest.mark.asyncio
class TestProcessingCount:
    async def test_returns_zero_for_empty_queue(
        self,
        broker: PgmqBroker,
    ):
        count = await broker.processing_count()

        assert count == 0

    async def test_returns_zero_for_queued_messages(
        self,
        broker: PgmqBroker,
    ):
        await broker.enqueue({"task": "test"})

        count = await broker.processing_count()

        assert count == 0

    async def test_returns_count_of_processing_messages(
        self,
        broker: PgmqBroker,
    ):
        msg_id = await broker.enqueue({"task": "test"})
        await broker.start(msg_id)

        count = await broker.processing_count()

        assert count == 1

    async def test_returns_count_of_multiple_processing_messages(
        self,
        broker: PgmqBroker,
    ):
        msg_id1 = await broker.enqueue({"task": "test1"})
        msg_id2 = await broker.enqueue({"task": "test2"})
        await broker.enqueue({"task": "test3"})

        await broker.start(msg_id1)
        await broker.start(msg_id2)

        count = await broker.processing_count()

        assert count == 2


@pytest.mark.asyncio
class TestStart:
    async def test_adds_processing_status_header(
        self, broker: PgmqBroker, db_conn: asyncpg.Connection
    ):
        msg_id = await broker.enqueue({"task": "test"})

        await broker.start(msg_id)

        headers = await db_conn.fetchval(
            f"SELECT headers FROM pgmq.q_{broker.queue_name} WHERE msg_id = $1",
            msg_id,
        )
        assert headers is not None
        headers_dict = loads(headers)
        assert headers_dict.get("x-pgtq-status") == "processing"

    async def test_start_on_nonexistent_message_raises_no_error(
        self, broker: PgmqBroker
    ):
        # Starting a non-existent message should not raise an error
        # (the SQL UPDATE will just affect 0 rows)
        await broker.start(999999)

        # No assertion needed - just verify it doesn't raise


@pytest.mark.asyncio
class TestComplete:
    async def test_removes_message_from_queue_with_archive(
        self, broker: PgmqBroker, db_conn: asyncpg.Connection
    ):
        msg_id = await broker.enqueue({"task": "test"})

        await broker.complete(msg_id)

        # Check message is archived
        archived = await db_conn.fetch(
            f"SELECT msg_id, message, headers FROM pgmq.a_{broker.queue_name}"
        )
        assert len(archived) == 1
        assert archived[0]["msg_id"] == msg_id
        headers = loads(archived[0]["headers"])
        assert headers.get("x-pgtq-status") == "completed"

        # Check message is removed from queue
        remaining = await db_conn.fetch(
            f"SELECT msg_id FROM pgmq.q_{broker.queue_name}"
        )
        assert len(remaining) == 0

    async def test_complete_removes_from_queue_without_archive(
        self,
        container: Container,
        db_conn: asyncpg.Connection,
        test_queue_name: str,
    ):
        from postgres_task_queue.pgmq.broker import PgmqBroker

        # Create broker without archive
        broker = PgmqBroker(test_queue_name, archive_table=False)
        queue = await container.pgmq()
        await queue.create_queue(test_queue_name, conn=db_conn)

        msg_id = await broker.enqueue({"task": "test"})

        await broker.complete(msg_id)

        # Check message is deleted from queue
        remaining = await db_conn.fetch(f"SELECT msg_id FROM pgmq.q_{test_queue_name}")
        assert len(remaining) == 0


@pytest.mark.asyncio
class TestFail:
    async def test_moves_to_dlq_without_retry(
        self, broker: PgmqBroker, db_conn: asyncpg.Connection
    ):
        msg_id = await broker.enqueue({"task": "test"})
        exc = ValueError("test error")

        await broker.fail(msg_id, exc, max_retries=0)

        # Check DLQ has the message
        dlq_messages = await db_conn.fetch(
            f"SELECT msg_id, message FROM pgmq.q_{broker.queue_name}_dlq"
        )
        assert len(dlq_messages) == 1
        dlq_payload = loads(dlq_messages[0]["message"])
        assert dlq_payload["msg_id"] == msg_id
        assert dlq_payload["queue_name"] == broker.queue_name
        assert dlq_payload["message"] == {"task": "test"}
        assert "test error" in dlq_payload["errors"]

        # Check original message is archived with FAILED status
        archived = await db_conn.fetch(
            f"SELECT msg_id, headers FROM pgmq.a_{broker.queue_name}"
        )
        assert len(archived) == 1
        assert archived[0]["msg_id"] == msg_id
        headers = loads(archived[0]["headers"])
        assert headers.get("x-pgtq-status") == "failed"

    async def test_retries_on_failure_within_max_retries(
        self, broker: PgmqBroker, db_conn: asyncpg.Connection
    ):
        msg_id = await broker.enqueue({"task": "test"})
        exc = ValueError("test error")

        await broker.fail(msg_id, exc, max_retries=3, delay_seconds=0.0)

        # Message should still be in queue (retried)
        remaining = await db_conn.fetch(
            f"SELECT msg_id, headers FROM pgmq.q_{broker.queue_name}"
        )
        assert len(remaining) == 1
        assert remaining[0]["msg_id"] == msg_id
        headers = loads(remaining[0]["headers"])
        assert headers.get("x-pgtq-status") == "queued"
        assert "test error" in headers.get("x-pgtq-errors", [])

    async def test_retries_with_delay(
        self, broker: PgmqBroker, db_conn: asyncpg.Connection
    ):

        msg_id = await broker.enqueue({"task": "test"})
        exc = ValueError("test error")

        await broker.fail(msg_id, exc, max_retries=3, delay_seconds=10.0)

        # Check vt is set in the future
        result = await db_conn.fetch(
            f"SELECT vt FROM pgmq.q_{broker.queue_name} WHERE msg_id = $1",
            msg_id,
        )
        assert len(result) == 1
        vt = result[0]["vt"]
        assert vt is not None
        # vt should be in the future (greater than NOW())
        current_time = await db_conn.fetchval("SELECT NOW()")
        assert vt > current_time

    async def test_moves_to_dlq_after_max_retries_exceeded(
        self, broker: PgmqBroker, db_conn: asyncpg.Connection
    ):
        msg_id = await broker.enqueue({"task": "test"})

        # First failure - will retry (1 error < max_retries=2)
        await broker.fail(
            msg_id, ValueError("error 1"), max_retries=2, delay_seconds=0.0
        )

        # Second failure - will retry (2 errors < max_retries=2 is False, but errors was 1 before this call)
        # Actually, after first fail, errors=["error 1"], len=1 < 2, so it retries
        # After second fail, errors=["error 1", "error 2"], len=2, 2 < 2 is False, so it goes to DLQ
        await broker.fail(
            msg_id, ValueError("error 2"), max_retries=2, delay_seconds=0.0
        )

        # Third failure - message is already in DLQ, so this should just update the original message
        # But the message is no longer in the queue, so this will fail
        # Let's just check that the message is in DLQ after 2 failures with max_retries=2

        # Check DLQ has the message
        dlq_messages = await db_conn.fetch(
            f"SELECT msg_id, message FROM pgmq.q_{broker.queue_name}_dlq"
        )
        assert len(dlq_messages) == 1
        dlq_payload = loads(dlq_messages[0]["message"])
        assert dlq_payload["msg_id"] == msg_id
        assert (
            len(dlq_payload["errors"]) == 2
        )  # Only 2 errors since it went to DLQ after second failure

    async def test_fail_without_dlq_deletes_message(
        self,
        container: Container,
        db_conn: asyncpg.Connection,
        test_queue_name: str,
    ):
        from postgres_task_queue.pgmq.broker import PgmqBroker

        # Create broker without DLQ
        broker = PgmqBroker(test_queue_name, dlq_queue_name=False)
        queue = await container.pgmq()
        await queue.create_queue(test_queue_name, conn=db_conn)

        msg_id = await broker.enqueue({"task": "test"})
        exc = ValueError("test error")

        await broker.fail(msg_id, exc, max_retries=0)

        # Check message is archived (since archive is enabled by default)
        archived = await db_conn.fetch(
            f"SELECT msg_id, headers FROM pgmq.a_{test_queue_name}"
        )
        assert len(archived) == 1
        assert archived[0]["msg_id"] == msg_id
        headers = loads(archived[0]["headers"])
        assert headers.get("x-pgtq-status") == "failed"
        assert "test error" in headers.get("x-pgtq-errors", [])

    async def test_fail_without_archive_and_dlq_deletes_message(
        self, container: Container, db_conn: asyncpg.Connection, test_queue_name: str
    ):
        from postgres_task_queue.pgmq.broker import PgmqBroker

        # Create broker without archive and without DLQ
        broker = PgmqBroker(test_queue_name, archive_table=False, dlq_queue_name=False)
        queue = await container.pgmq()
        await queue.create_queue(test_queue_name, conn=db_conn)

        msg_id = await broker.enqueue({"task": "test"})
        exc = ValueError("test error")

        await broker.fail(msg_id, exc, max_retries=0)

        # Check message is deleted from queue
        remaining = await db_conn.fetch(f"SELECT msg_id FROM pgmq.q_{test_queue_name}")
        assert len(remaining) == 0


@pytest.mark.asyncio
class TestReschedule:
    async def test_reschedules_dlq_message_to_main_queue(
        self, broker: PgmqBroker, db_conn: asyncpg.Connection
    ):
        # First, create a message and fail it to DLQ
        original_payload = {"task": "original"}
        msg_id = await broker.enqueue(original_payload)
        await broker.fail(msg_id, ValueError("error"), max_retries=0)

        # Get the DLQ message ID
        dlq_messages = await db_conn.fetch(
            f"SELECT msg_id, message FROM pgmq.q_{broker.queue_name}_dlq"
        )
        assert len(dlq_messages) == 1
        dlq_msg_id = dlq_messages[0]["msg_id"]

        # Reschedule the DLQ message
        new_msg_id = await broker.reschedule(dlq_msg_id, conn=db_conn)

        # Check new message is in main queue
        main_queue_messages = await db_conn.fetch(
            f"SELECT msg_id, message FROM pgmq.q_{broker.queue_name}"
        )
        assert len(main_queue_messages) == 1
        assert main_queue_messages[0]["msg_id"] == new_msg_id
        assert loads(main_queue_messages[0]["message"]) == original_payload

        # Check DLQ message is archived
        dlq_archived = await db_conn.fetch(
            f"SELECT msg_id FROM pgmq.a_{broker.queue_name}_dlq"
        )
        assert len(dlq_archived) == 1
        assert dlq_archived[0]["msg_id"] == dlq_msg_id

        # Check new message has original header
        headers = await db_conn.fetchval(
            f"SELECT headers FROM pgmq.q_{broker.queue_name} WHERE msg_id = $1",
            new_msg_id,
        )
        headers_dict = loads(headers)
        assert headers_dict.get("x-pgtq-original") == str(msg_id)

    async def test_adds_retry_header_to_dlq_message(
        self, broker: PgmqBroker, db_conn: asyncpg.Connection
    ):
        # First, create a message and fail it to DLQ
        original_payload = {"task": "original"}
        msg_id = await broker.enqueue(original_payload)
        await broker.fail(msg_id, ValueError("error"), max_retries=0)

        # Get the DLQ message ID
        dlq_messages = await db_conn.fetch(
            f"SELECT msg_id FROM pgmq.q_{broker.queue_name}_dlq"
        )
        dlq_msg_id = dlq_messages[0]["msg_id"]

        # Reschedule the DLQ message
        new_msg_id = await broker.reschedule(dlq_msg_id, conn=db_conn)

        # Check DLQ message has retry header
        dlq_archived = await db_conn.fetch(
            f"SELECT headers FROM pgmq.a_{broker.queue_name}_dlq WHERE msg_id = $1",
            dlq_msg_id,
        )
        assert len(dlq_archived) == 1
        headers = loads(dlq_archived[0]["headers"])
        assert headers.get("x-pgtq-retry") == str(new_msg_id)


@pytest.mark.asyncio
class TestBrokerProperties:
    async def test_queue_name(self, broker: PgmqBroker, test_queue_name: str):
        assert broker.queue_name == test_queue_name

    async def test_archive_property(self, broker: PgmqBroker, test_queue_name: str):
        assert broker.archive is not None
        assert PgmqBroker(test_queue_name, archive_table=False).archive is None

    async def test_dlq_property(self, broker: PgmqBroker, test_queue_name: str):
        assert broker.dlq is not None
        assert PgmqBroker(test_queue_name, dlq_queue_name=False).dlq is None


@pytest.mark.asyncio
class TestArchivePrune:
    async def test_prune_by_ttl_deletes_old_messages(
        self, broker: PgmqBroker, archive: Archive, db_conn: asyncpg.Connection
    ):
        from datetime import timedelta

        # First, add and archive some messages
        msg_id1 = await broker.enqueue({"task": "old"})
        await broker.complete(msg_id1)

        # Archive an old message by directly manipulating the timestamp
        await db_conn.execute(
            f"""UPDATE pgmq.a_{broker.queue_name}
                SET archived_at = NOW() - INTERVAL '2 days'
                WHERE msg_id = $1""",
            msg_id1,
        )

        # Prune messages older than 1 day
        deleted_count = await archive.prune(ttl=timedelta(days=1), conn=db_conn)

        assert deleted_count == 1

        # Verify message is deleted from archive
        archived = await db_conn.fetch(f"SELECT msg_id FROM pgmq.a_{broker.queue_name}")
        assert len(archived) == 0

    async def test_prune_by_limit_keeps_most_recent(
        self, broker: PgmqBroker, archive: Archive, db_conn: asyncpg.Connection
    ):
        # Archive multiple messages
        for i in range(5):
            msg_id = await broker.enqueue({"task": f"item_{i}"})
            await broker.complete(msg_id)

        # Prune to keep only 2 most recent
        deleted_count = await archive.prune(limit=2, conn=db_conn)

        assert deleted_count == 3

        # Verify only 2 most recent remain
        archived = await db_conn.fetch(
            f"SELECT msg_id FROM pgmq.a_{broker.queue_name} ORDER BY archived_at DESC"
        )
        assert len(archived) == 2

    async def test_prune_with_no_parameters_returns_zero(
        self, broker: PgmqBroker, archive: Archive, db_conn: asyncpg.Connection
    ):
        # Archive a message
        msg_id = await broker.enqueue({"task": "test"})
        await broker.complete(msg_id)

        # Prune with no parameters should delete nothing
        deleted_count = await archive.prune(conn=db_conn)

        assert deleted_count == 0

        # Verify message still in archive
        archived = await db_conn.fetch(f"SELECT msg_id FROM pgmq.a_{broker.queue_name}")
        assert len(archived) == 1


@pytest.mark.asyncio
class TestDlqEnqueue:
    async def test_enqueue_adds_message_to_dlq(
        self, broker: PgmqBroker, dlq: Dlq, db_conn: asyncpg.Connection
    ):
        payload = {"foo": "bar", "original_msg_id": 123}
        dlq_msg_id = await dlq.enqueue(payload)

        results = await db_conn.fetch(
            f"SELECT msg_id, message FROM pgmq.q_{broker.queue_name}_dlq"
        )
        assert len(results) == 1
        assert results[0]["msg_id"] == dlq_msg_id
        assert loads(results[0]["message"]) == payload

    async def test_enqueue_multiple_messages_to_dlq(
        self, broker: PgmqBroker, dlq: Dlq, db_conn: asyncpg.Connection
    ):
        payload1 = {"error": "first"}
        payload2 = {"error": "second"}
        msg_id1 = await dlq.enqueue(payload1)
        msg_id2 = await dlq.enqueue(payload2)

        results = await db_conn.fetch(
            f"SELECT msg_id, message FROM pgmq.q_{broker.queue_name}_dlq ORDER BY msg_id"
        )
        assert len(results) == 2
        msg_ids = {row["msg_id"] for row in results}
        assert msg_ids == {msg_id1, msg_id2}
